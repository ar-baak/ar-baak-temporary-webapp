from dataclasses import dataclass
from enum import Enum
import io
import json
from random import random
import time
from typing import Dict, List, Optional
import httpx
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone
import pytz
import re
from lxml import html
import logging

HKJC_BASE_URL = "https://bet.hkjc.com"
RSDATA_URL = "https://bet.hkjc.com/racing/script/rsdata.js?lang=en&date={date:%Y-%m-%d}"
URL_HKJC_WPO = "https://bet.hkjc.com/racing/getJSON.aspx?type=winplaodds&date={date:%Y-%m-%d}&venue={venue}&start={start_race}&end={end_race}"
RACECARD_URL = "https://bet.hkjc.com/racing/index.aspx?lang=ch&date={date:%Y-%m-%d}&venue={venue}&raceno={race_no}"
HKJC_ODDS_PATTERN = re.compile(r"(?P<horse>\d+)=(?P<odds>[\d\.\w]+)=(?P<fav>\d)")
VARIABLE_REGEX_PATTERN = r"var (?P<key>\w+) = (?P<value>.+);"
CAMELCASE_TO_SNAKE_PATTERN = r"(?<!^)(?=[A-Z])"
RUNNER_LIST_PATTERN = re.compile(r" = (\[.+?\]);")


class Mode(Enum):
    BET = "bet"
    EAT = "eat"


URL_MAPPING = {
    Mode.BET: "http://info.mdataone.com/bdata?race_type={location}&race_date={date:%d-%m-%Y}&m=HK&rc=0&c=0",
    Mode.EAT: "http://info.mdataone.com/edata?race_type={location}&race_date={date:%d-%m-%Y}&m=HK&rc=0&c=0",
}
CTB_ODDS_PATTERN: re.Pattern = re.compile(
    r"\n(?P<race>\d+)\t(?P<horse>\d+)\t(?P<win_amount>\d+)\t(?P<place_amount>\d+)\t(?P<discount>\d+)"
)
CTB_KEY_PATTERN: re.Pattern = re.compile(
    r"(?P<mode>[A-Z]{3})_(?P<race_date>\d{2}-\d{2}-\d{4})_(?P<location>\d{0,3}[A-Z]{0,2})_\d+"
)

# Get the GMT+8 timezone
GMT8 = pytz.timezone(
    "Asia/Hong_Kong"
)  # You can choose any city that's in the GMT+8 timezone
TODAY = datetime.now(GMT8)


# @dataclass
# class HKJCEntry:
#     num: int = None
#     id: str = None
#     name_en: str = None
#     name_ch: str = None
#     horse_id: str = None
#     name: str = None
#     jockey_code: str = None
#     jockey_name_en: str = None
#     jockey_name_ch: str = None
#     jockey_name: str = None
#     trainerCode: str = None
#     trainer_name_en: str = None
#     trainer_name_ch: str = None
#     trainer_name: str = None
#     horseWeight: int = None
#     handicapWeight: int = None
#     runnerRating: int = None
#     intRating = None
#     gear = None
#     lastSixRun = None
#     barDraw = None
#     saddleCloth = None
#     brandNum = None
#     brandColor = None
#     standbyStatus = None
#     apprenticeAllowance = None
#     scratched = None
#     scratchedGroup = None
#     Members = None
#     priority = None
#     trumpCard = None
#     preference = None

JOCKEY_MAPPING = {
    "布文": "布",
    "潘頓": "潘",
    "鍾易禮": "鍾",
    "霍宏聲": "霍",
    "田泰安": "田",
    "梁家俊": "俊",
    "周俊樂": "周",
    "艾道拿": "艾",
    "楊明綸": "綸",
    "班德禮": "班",
    "艾兆禮": "兆",
    "黃智弘": "智",
    "董明朗": "董",
    "希威森": "森",
    "潘明輝": "明",
    "蔡明紹": "紹",
    "何澤堯": "堯",
    "陳嘉熙": "熙",
    "巴度": "度",
    "巫顯東": "巫",
    "賀銘年": "賀",
    "嘉里": "里",
}

TRAINER_MAPPING = {
    "呂健威": "呂",
    "文家良": "文",
    "沈集成": "沈",
    "方嘉柏": "方",
    "伍鵬志": "伍",
    "告東尼": "東",
    "大衛希斯": "希",
    "葉楚航": "葉",
    "韋達": "韋",
    "姚本輝": "姚",
    "蘇偉賢": "偉",
    "羅富全": "羅",
    "賀賢": "賀",
    "容天鵬": "容",
    "丁冠豪": "丁",
    "鄭俊偉": "鄭",
    "蔡約翰": "蔡",
    "黎昭昇": "黎",
    "徐雨石": "徐",
    "廖康銘": "廖康銘",
    "巫偉傑": "巫偉傑",
}


@dataclass
class HKJCOdds:
    entry: str = None
    race_date: datetime = None
    race_num: int = None
    num: int = None
    win: int = 0
    place: int = 0
    win_fav: bool = False
    place_fav: bool = False


def fetch_from_hkjc(url: str, data: Optional[Dict] = None):
    with httpx.Client() as sess:
        res = sess.get(HKJC_BASE_URL)
        cookies = dict(res.cookies)
        if data:
            return sess.post(url, data=data, cookies=cookies)
        else:
            return sess.get(url=url, cookies=cookies)


def check_for_races(text: str) -> bool:
    return "mtgDate" in text


def safe_cast_int_from_str(s: str, default: int = 0) -> int:
    return int(s) if s.replace("-", "") != "" else default


def replace_hkjc_text(text: str) -> str:
    """Convert javascript expressions to python expressions

    Args:
        text (str): raw text

    Returns:
        str: cleaned text
    """
    return (
        text.replace("null", "None")
        .replace("true", "True")
        .replace("false", "False")
        .strip()
    )


def clean_meeting_response(text: str) -> Dict:
    """Clean meeting javascript responses

    Args:
        text (str): raw text

    Returns:
        Dict: dictionary of meeting metadata
    """
    data_dict = dict()
    text = replace_hkjc_text(text)
    for line in text.split("\n"):
        _ = re.match(VARIABLE_REGEX_PATTERN, line, flags=re.IGNORECASE)
        if _:
            key, value = _.groups()
            data_dict[re.sub(CAMELCASE_TO_SNAKE_PATTERN, "_", key).lower()] = eval(
                value
            )

    data_dict["mtg_date"] = datetime.strptime(
        data_dict["mtg_date"], "%Y-%m-%d"
    ).replace(tzinfo=GMT8)

    data_dict["race_post_time"] = [
        datetime.strptime(d, "%Y-%m-%d %H:%M:%S").replace(tzinfo=GMT8)
        for d in data_dict["race_post_time"]
        if d != ""
    ]
    data_dict.pop("multi_race_pools_str")

    return data_dict


def get_meeting_today() -> Dict:
    _ = 0
    while True:
        _ += 1
        logging.info(RSDATA_URL.format(date=TODAY) + ("&venue=ST" * (_ % 2)))
        response = fetch_from_hkjc(
            RSDATA_URL.format(date=TODAY) + ("&venue=ST" * (_ % 2))
        ).text
        if check_for_races(response):
            break
        else:
            time.sleep(random())
            logging.info("Invalid response!")

    response = clean_meeting_response(response)

    if response["mtg_date"].date() != TODAY.date():
        logging.info("Races are not on today!")
        return None

    return response


def get_racecard_today(race_no: int, venue: str) -> List[Dict]:
    """Clean racecard javascript responses

    Args:
        text (str): raw text

    Returns:
        List[Dict]: list of dictionary, each represents metadata of an entry on the
        racecard
    """
    response = fetch_from_hkjc(
        url=RACECARD_URL.format(date=TODAY, venue=venue, race_no=race_no)
    )

    text = replace_hkjc_text(response.text)
    tree = html.fromstring(text)
    elem = tree.xpath('//*[@id="container"]/div/div/div[2]/script[1]')[0]
    responses = []
    for match in re.finditer(RUNNER_LIST_PATTERN, elem.text):
        response = eval(match.group(1))
        for card in response:
            if isinstance(card, list):
                for _ in card:
                    _["race_num"] = race_no
                responses.extend(card)
            elif isinstance(card, dict):
                card["race_num"] = race_no
                responses.append(card)
            else:
                logging.info(f"Unexpected type: {type(card)}")
    return responses


def get_all_racecard_today(
    venue: str, total_ran_race: int, total_race: int
) -> List[List[Dict]]:
    racecards = []

    for i in range(1, total_race + 1):
        if i <= total_ran_race:
            racecards.append(None)
            continue

        logging.info(f"Race {i}")
        response = None
        while True:
            _ = 0
            if _ < 3:
                _ += 1
                try:
                    racecards.append(get_racecard_today(race_no=i, venue=venue))
                    break
                except IndexError:
                    logging.info("Retrying")
                    time.sleep(0.2)
                    continue

    return racecards


def process_hkjc_response(results: str) -> List[HKJCOdds]:
    all_odds = []

    for race_num, data in enumerate(results.strip().split("@@@")[1:]):
        logging.info(f"Processing race {race_num + 1}")
        win_odds, place_odds = data.split("#")

        for win_match, place_match in zip(
            re.finditer(HKJC_ODDS_PATTERN, win_odds),
            re.finditer(HKJC_ODDS_PATTERN, place_odds),
        ):
            win_match = win_match.groupdict()
            place_match = place_match.groupdict()

            assert win_match["horse"] == place_match["horse"]

            if win_match["odds"] == "SCR":
                logging.info(
                    f"Race {race_num + 1} Horse {win_match.get('horse', 0)} scratched."
                )
                continue

            odds = HKJCOdds(race_num=race_num + 1)
            odds.num = int(win_match.get("horse", 0))
            win_is_float = win_match["odds"].replace(".", "", 1).isdigit()
            odds.win = float(win_match["odds"]) if win_is_float else None
            odds.win_fav = win_match["fav"] == "1"
            place_is_float = place_match["odds"].replace(".", "", 1).isdigit()
            odds.place = float(place_match["odds"]) if place_is_float else None
            odds.place_fav = place_match["fav"] == "1"

            all_odds.append(odds)

    return all_odds


def get_race_odds_today(venue: str, start_race: int, end_race: int):
    hkjc_odds_url = URL_HKJC_WPO.format(
        date=TODAY, venue=venue, start_race=start_race, end_race=end_race
    )
    response = fetch_from_hkjc(hkjc_odds_url)
    hkjc_odds = process_hkjc_response(response.text)
    return hkjc_odds


def fetch_ctb_data(url: str, callback_function: callable) -> None:
    """
    Fetch data synchronously from the specified URL and invoke the callback function.

    Args:
        url (str): The URL to fetch data from.
        callback_function (callable): The callback function to process the fetched data.
    """
    with httpx.Client(timeout=httpx.Timeout(3.0)) as client:
        response = client.get(url=url)
        return callback_function(response.text)


def check_valid_ctb988_response(response_text: str) -> bool:
    """
    Check if a CTB988 response is valid.

    Args:
        response_text (str): The response text.

    Returns:
        bool: True if the response is valid, False otherwise.
    """
    if len(response_text) < 140:
        return False

    match = CTB_KEY_PATTERN.search(response_text)
    if not CTB_KEY_PATTERN.search(response_text):
        return False

    return True


def parse_ctb988_datetime(datestring: str) -> Optional[datetime]:
    """
    Parse a CTB988 date string to a datetime object.

    Args:
        datestring (str): The CTB988 date string.

    Returns:
        datetime: The parsed datetime object.
    """
    if not datestring:
        return

    return datetime.strptime(datestring, "%d-%m-%Y")


def message_template_factory(
    date: str,
    location: str,
    race: int,
    horse: int,
    timestamp: str,
    mode: Mode,
    win_discount: Optional[int] = None,
    place_discount: Optional[int] = None,
) -> Dict[str, Optional[str]]:
    """
    Create a message template dictionary.

    Args:
        date (str): The date of the race.
        location (str): The location of the race.
        race (int): The race number.
        horse (int): The horse number.
        timestamp (str): The timestamp of the message.
        mode (str): The mode of bet.
        win_discount (int, optional): The win discount.
        place_discount (int, optional): The place discount.

    Returns:
        dict: The message template dictionary.
    """
    return {
        "date": date,
        "location": location,
        "race": race,
        "horse": horse,
        "win_discount": win_discount,
        "place_discount": place_discount,
        "timestamp": timestamp,
        "mode": mode.value,
    }


def parse_ctb988_response(response_text: str) -> None:
    """
    Parse the CTB988 response.

    Args:
        response_text (str): The response text.
    """
    if not check_valid_ctb988_response(response_text):
        # logger.warning("Invalid CTB988 response")
        return "Invalid CTB988 response"

    response = json.loads(response_text[2:-2])
    timestamp: str = (
        datetime.utcfromtimestamp(int(response["ts"]) / 1000).isoformat() + "+00:00"
    )
    match = CTB_KEY_PATTERN.search(response["cookieKey"])
    mode = Mode(match.group("mode").lower()) if match else None
    race_date: Optional[datetime] = (
        parse_ctb988_datetime(match.group("race_date")) if match else None
    )
    location: Optional[str] = match.group("location") if match else None
    message: Optional[Dict[str, Optional[str]]] = None

    df = pd.read_csv(
        io.StringIO(response["pendingData"]),
        delimiter=r"\t",
        names=["race", "horse", "win_amount", "place_amount", "discount", "_"],
    )

    messages: List = []

    for (race, horse), _ in df.groupby(["race", "horse"]):
        win_discount = _[_["win_amount"] > 0]["discount"].min()
        place_discount = _[_["place_amount"] > 0]["discount"].min()
        message = message_template_factory(
            date=datetime.strftime(race_date, "%Y-%m-%d"),
            location=location,
            race=int(race),
            horse=int(horse),
            timestamp=timestamp,
            mode=mode,
            win_discount=win_discount,
            place_discount=place_discount,
        )
        messages.append(message)

    return messages


def main():
    st.title("Ar Baak")
    meeting = get_meeting_today()

    if not meeting:
        st.subheader("No upcoming race today")
        return

    total_race = meeting["mtg_total_race"]
    total_ran_race = meeting["mtg_ran_race"]
    venue = meeting["venue_short"]

    racecards = get_all_racecard_today(
        venue=venue, total_ran_race=total_ran_race, total_race=total_race
    )

    race_odds = get_race_odds_today(
        venue=venue, start_race=total_ran_race + 1, end_race=total_race
    )

    df_racecard = pd.concat(pd.DataFrame(_) for _ in racecards)
    df_race_odds = pd.DataFrame(race_odds)

    df_hkjc = pd.merge(
        left=df_racecard,
        right=df_race_odds,
        on=["race_num", "num"],
        how="left",
    )
    # df_hkjc = df_hkjc[["race_num", "num", "name", "jockeyName", "trainerName"]]
    df_hkjc = df_hkjc.rename(
        {
            "race_num": "場",
            "num": "號",
            "name": "馬",
            "jockeyName": "騎",
            "trainerName": "練",
            "win": "WIN",
            "place": "PLA",
            "win_fav": "WIN熱",
            "place_fav": "PLA熱",
        },
        axis=1,
    )
    df_hkjc["騎"] = df_hkjc["騎"].map(JOCKEY_MAPPING)
    df_hkjc["練"] = df_hkjc["練"].map(TRAINER_MAPPING)

    bet_response = fetch_ctb_data(
        URL_MAPPING[Mode.BET].format(location="3H", date=TODAY),
        callback_function=parse_ctb988_response,
    )

    df_ctb_bet = pd.DataFrame(bet_response)

    lay_response = fetch_ctb_data(
        URL_MAPPING[Mode.EAT].format(location="3H", date=TODAY),
        callback_function=parse_ctb988_response,
    )

    df_ctb_lay = pd.DataFrame(lay_response)

    df_bet = pd.merge(
        left=df_hkjc,
        right=df_ctb_bet,
        left_on=["場", "號"],
        right_on=["race", "horse"],
        how="left",
    )[
        [
            "場",
            "號",
            "馬",
            "騎",
            "練",
            "WIN",
            "PLA",
            # "WIN熱",
            # "PLA熱",
            "win_discount",
            "place_discount",
        ]
    ]
    df_bet = df_bet.rename({"win_discount": "WIN賭折", "place_discount": "PLA賭折"}, axis=1)

    df_bet = pd.merge(
        left=df_bet,
        right=df_ctb_lay,
        left_on=["場", "號"],
        right_on=["race", "horse"],
        how="left",
    )[
        [
            "場",
            "號",
            "馬",
            "騎",
            "練",
            "WIN",
            "PLA",
            # "WIN熱",
            # "PLA熱",
            "WIN賭折",
            "PLA賭折",
            "win_discount",
            "place_discount",
        ]
    ]
    df_bet = df_bet.rename({"win_discount": "WIN吃折", "place_discount": "PLA吃折"}, axis=1)

    st.markdown(df_bet.to_html(index=False), unsafe_allow_html=True)

    # for _ in race_odds:
    return


if __name__ == "__main__":
    st.set_page_config(page_title="Ar Baak", page_icon="🐴", layout="wide")
    main()
