from typing import List, Optional
import pandas as pd
import streamlit as st
from services.race_data import fetch_race_meetings, process_meeting_response
from services.odds_processing import (
    fetch_odds_from_graphql,
    get_ctb_data,
    process_odds_response,
    merge_races_with_odds,
)
from models.race_models import Meeting, Race

# Mappings for jockeys and trainers
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
    "巫顯東": "東",
    "賀銘年": "賀",
    "嘉里": "里",
    "黃寶妮": "妮",
    "湯普新": "湯",
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
    "廖康銘": "廖",
    "巫偉傑": "巫",
    "游達榮": "游",
}


# Helper functions
def map_jockey_name(jockey_name: str) -> str:
    return JOCKEY_MAPPING.get(jockey_name, jockey_name)


def map_trainer_name(trainer_name: str) -> str:
    return TRAINER_MAPPING.get(trainer_name, trainer_name)


def highlight_favorites(odds: Optional[float], is_favorite: bool) -> str:
    if is_favorite:
        return f"<span style='color: red; font-weight: bold;'>{odds}</span>"
    return str(odds if odds is not None else "N/A")


def display_race_columns(race: Race, df_ctb: pd.DataFrame):
    """Display each horse in a markdown table layout using Streamlit with mobile responsiveness."""

    st.markdown(f"### 第 {race.no} 場: {race.raceName_ch}")
    st.markdown(f"**開跑時間:** {race.postTime:%Y-%m-%d %H:%M}")

    # Build the markdown table header for mobile-friendly view
    table_header = "|  | 馬 | 騎 | 練 | W | W折 | P | P折 |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n"

    # Initialize table rows
    table_rows = ""

    for runner in race.runners:
        if runner.status == "Standby":
            continue

        # Safely handle CTB data
        win_discount, place_discount = "N/A", "N/A"

        if not df_ctb.empty and all(
            col in df_ctb.columns
            for col in ["race", "horse", "win_discount", "place_discount"]
        ):
            win_discount_values = df_ctb.loc[
                (df_ctb["race"] == race.no) & (df_ctb["horse"] == runner.no),
                "win_discount",
            ].values
            place_discount_values = df_ctb.loc[
                (df_ctb["race"] == race.no) & (df_ctb["horse"] == runner.no),
                "place_discount",
            ].values

            win_discount = (
                win_discount_values[0] if len(win_discount_values) > 0 else "N/A"
            )
            place_discount = (
                place_discount_values[0] if len(place_discount_values) > 0 else "N/A"
            )

        # Map jockey and trainer names
        jockey_name = map_jockey_name(runner.jockey_name_ch)
        trainer_name = map_trainer_name(runner.trainer_name_ch)

        # Safely handle NoneType values for odds
        win_odds = f"{runner.winOdds:.1f}" if runner.winOdds is not None else "N/A"
        place_odds = (
            f"{runner.placeOdds:.1f}" if runner.placeOdds is not None else "N/A"
        )

        # Create a table row for each horse
        row = (
            f"| {runner.no} | {runner.name_ch[:3]}{'...' if len(runner.name_ch) > 3 else ''}"
            f" | {jockey_name} | {trainer_name} | {win_odds} | {win_discount} | "
            f"{place_odds} | {place_discount} |\n"
        )
        table_rows += row

    # Combine header and rows into a full table
    full_table = table_header + table_rows
    # Render the table as markdown
    st.markdown(full_table)


def display_race_tabs(meeting_info: Meeting, df_ctb: pd.DataFrame):
    race_tabs = st.tabs([f"第 {race.no} 場" for race in meeting_info.races])

    for i, race in enumerate(meeting_info.races):
        with race_tabs[i]:
            display_race_columns(race, df_ctb)


def display_meeting_selection(meetings: List[Meeting]):
    """Display a dropdown for users to select a meeting."""
    if not meetings:
        st.write("No meetings available.")
        return None

    # Create a list of meeting names (using date, venue, etc.)
    meeting_names = [
        f"{meeting.date:%Y-%m-%d} - {meeting.country_name()}" for meeting in meetings
    ]

    # Let users select a meeting from a dropdown
    selected_meeting_name = st.selectbox("Select a Race Meeting:", meeting_names)

    # Find and return the selected meeting
    for meeting in meetings:
        if (
            f"{meeting.date:%Y-%m-%d} - {meeting.country_name()}"
            == selected_meeting_name
        ):
            return meeting

    return None


# Main function
def main():
    st.title("Ar Baak Bet Horse")

    # Fetch race meeting details

    race_data = fetch_race_meetings()
    meetings = process_meeting_response(race_data)
    selected_meeting = display_meeting_selection(meetings)

    # Fetch odds data for the selected race and merge into race data
    if selected_meeting:
        for race in selected_meeting.races:
            odds_data = fetch_odds_from_graphql(
                date=selected_meeting.date.strftime("%Y-%m-%d"),
                venue=selected_meeting.venueCode,
                race_no=race.no,
                odds_types=["WIN", "PLA"],
            )
            odds_map = process_odds_response(odds_data)
            merge_races_with_odds(selected_meeting.races, odds_map, race_no=race.no)

        # Fetch CTB data and merge
        df_ctb = get_ctb_data(selected_meeting.date)

        # Display selected race details in tabs
        display_race_tabs(selected_meeting, df_ctb)


if __name__ == "__main__":
    st.set_page_config(page_title="Ar Baak", layout="wide")
    main()
