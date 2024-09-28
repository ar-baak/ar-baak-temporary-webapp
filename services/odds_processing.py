from datetime import datetime
from enum import Enum
import io
import json
import re
from typing import Callable, Dict, List
import httpx
import streamlit as st

import pandas as pd
from services.graphql import send_graphql_query, build_odds_payload
from models.race_models import Race
from utils.logger import logger


def fetch_odds_from_graphql(
    date: str, venue: str, race_no: int, odds_types: List[str]
) -> Dict:
    """Fetch odds using the new GraphQL API."""
    payload = build_odds_payload(date, venue, race_no, odds_types)
    return send_graphql_query(payload)


def process_odds_response(response: Dict) -> Dict[int, Dict[str, float]]:
    """Process the odds response and return a dictionary of runner odds for the specified race."""
    odds_map: Dict[int, Dict[str, float]] = {}

    if not response or "data" not in response:
        logger.error("Invalid odds response or no data")
        return odds_map

    race_meetings = response["data"].get("raceMeetings", [])
    for meeting in race_meetings:
        pools = meeting.get("pmPools", [])
        for pool in pools:
            odds_type = pool.get("oddsType", "")
            odds_nodes = pool.get("oddsNodes", [])

            for odds_node in odds_nodes:
                comb_string = odds_node["combString"]  # Runner number
                odds_value = odds_node["oddsValue"]

                # Convert comb_string to runner number
                runner_num = int(comb_string)

                if runner_num not in odds_map:
                    odds_map[runner_num] = {}

                # Map WIN and PLA odds accordingly
                if odds_type == "WIN":
                    odds_map[runner_num]["WIN"] = odds_value
                elif odds_type == "PLA":
                    odds_map[runner_num]["PLA"] = odds_value

    return odds_map


def merge_races_with_odds(
    races: List[Race], odds_data: Dict[int, Dict[str, float]], race_no: int
):
    """Merge both WIN and PLA odds into the specified race's runners."""
    for race in races:
        if race.no == race_no:  # Only merge odds for the current race
            for runner in race.runners:
                if runner.no in odds_data:
                    runner.winOdds = odds_data[runner.no].get("WIN", None)
                    runner.placeOdds = odds_data[runner.no].get("PLA", None)


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


def fetch_ctb_data(url: str, callback_function: Callable) -> List[Dict]:
    """Fetch CTB data from the specified URL."""
    with httpx.Client(timeout=httpx.Timeout(3.0)) as client:
        response = client.get(url=url)
        return callback_function(response.text)


def parse_ctb988_response(response_text: str) -> List[Dict]:
    """Parse the CTB988 response and return the relevant betting data."""
    if not check_valid_ctb988_response(response_text):
        return []

    response = json.loads(response_text[2:-2])
    df = pd.read_csv(
        io.StringIO(response["pendingData"]),
        delimiter=r"\t",
        names=["race", "horse", "win_amount", "place_amount", "discount", "_"],
    )

    messages = []

    for (race, horse), _ in df.groupby(["race", "horse"]):
        win_discount = _[_["win_amount"] > 0]["discount"].min()
        place_discount = _[_["place_amount"] > 0]["discount"].min()
        messages.append(
            {
                "race": int(race),
                "horse": int(horse),
                "win_discount": win_discount,
                "place_discount": place_discount,
            }
        )

    return messages


def check_valid_ctb988_response(response_text: str) -> bool:
    """Check if a CTB988 response is valid."""
    if len(response_text) < 140:
        return False

    match = CTB_KEY_PATTERN.search(response_text)
    return bool(match)


@st.cache_data(ttl="10s")
def get_ctb_data(meeting_date: datetime) -> pd.DataFrame:
    """Fetch and return CTB data for the given date."""
    ctb_url = URL_MAPPING[Mode.EAT].format(location="3H", date=meeting_date)
    ctb_data = fetch_ctb_data(ctb_url, parse_ctb988_response)
    return pd.DataFrame(ctb_data)


def merge_races_with_ctb(df_race: pd.DataFrame, df_ctb: pd.DataFrame) -> pd.DataFrame:
    """Merge CTB data (discounts) with race data."""
    df_merged = pd.merge(
        left=df_race,
        right=df_ctb,
        left_on=["race_num", "num"],
        right_on=["race", "horse"],
        how="left",
    )
    df_merged.rename(
        columns={"win_discount": "WIN折", "place_discount": "PLA折"}, inplace=True
    )
    return df_merged
