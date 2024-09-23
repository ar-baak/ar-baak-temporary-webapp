import streamlit as st
from typing import Dict
from services.graphql import send_graphql_query, build_meeting_payload
from models.race_models import Meeting, Pool, Race, RaceCourse, RaceTrack, Runner
from utils.logger import logger


def fetch_race_meetings(date: str, venue: str) -> Dict:
    """Fetch race meeting details from GraphQL."""
    payload = build_meeting_payload(date, venue)
    return send_graphql_query(payload)


def calculate_odds(
    total_investment: float, runner_investment: float, track_takeout: float = 0.15
) -> float:
    """
    Calculate the odds for a runner based on total pool investment and investment on the runner.

    Args:
        total_investment: The total pool investment for the race.
        runner_investment: The amount bet on the specific runner.
        track_takeout: The percentage taken by the track (default is 15%).

    Returns:
        The calculated odds for the runner.
    """
    # Ensure runner_investment is not 0 to avoid division by zero
    if runner_investment == 0:
        return 0.0

    # Adjust the total investment by removing the track takeout
    available_pool = total_investment * (1 - track_takeout)

    # Calculate the odds
    odds = (available_pool / runner_investment) - 1
    return round(odds, 2)


def process_meeting_response(response: Dict) -> Meeting:
    """Process the GraphQL race meeting response and return structured data."""
    if not response or "data" not in response:
        logger.error("Invalid response or no data")
        return {}

    race_meeting_data = response["data"]["raceMeetings"][0]

    # Extract date from the response (assuming it's available)
    meeting_date = race_meeting_data.get(
        "date", "Unknown Date"
    )  # Adjust according to your response structure

    # Extract race information
    races = []
    for race in race_meeting_data["races"]:
        runners = []
        total_investment = None
        for pool in race_meeting_data.get("poolInvs", []):
            if pool["oddsType"] == "WIN":
                total_investment = pool["investment"]
                break

        for runner_data in race["runners"]:
            winOdds = None
            if total_investment and runner_data.get("winOdds"):
                winOdds = calculate_odds(
                    total_investment=total_investment,
                    runner_investment=float(runner_data["winOdds"]),
                )

            runner = Runner(
                id=runner_data["id"],
                no=runner_data["no"],
                standbyNo=runner_data.get("standbyNo"),
                status=runner_data["status"],
                name_ch=runner_data["name_ch"],
                name_en=runner_data["name_en"],
                horse_id=runner_data["horse"]["id"],
                barrierDrawNumber=runner_data.get("barrierDrawNumber"),
                handicapWeight=runner_data.get("handicapWeight"),
                jockey_name_en=runner_data["jockey"]["name_en"],
                jockey_name_ch=runner_data["jockey"]["name_ch"],
                trainer_name_en=runner_data["trainer"]["name_en"],
                trainer_name_ch=runner_data["trainer"]["name_ch"],
                winOdds=winOdds,
            )
            runners.append(runner)

        race_obj = Race(
            id=race["id"],
            no=race["no"],
            status=race["status"],
            raceName_en=race.get("raceName_en"),
            raceName_ch=race.get("raceName_ch"),
            postTime=race.get("postTime"),
            distance=race.get("distance"),
            wageringFieldSize=race.get("wageringFieldSize"),
            raceTrack=RaceTrack(**race["raceTrack"]) if race.get("raceTrack") else None,
            raceCourse=(
                RaceCourse(**race["raceCourse"]) if race.get("raceCourse") else None
            ),
            runners=runners,
        )
        races.append(race_obj)

    # Extract pool information
    pools = []
    for pool in race_meeting_data["poolInvs"]:
        pool_obj = Pool(
            id=pool["id"],
            oddsType=pool.get("oddsType"),
            status=pool.get("status"),
            investment=pool.get("investment"),
            totalInvestment=pool.get("investment"),
            mergedPoolId=pool.get("mergedPoolId"),
            lastUpdateTime=pool.get("lastUpdateTime"),
        )
        pools.append(pool_obj)

    # Return the structured meeting object, including the date
    meeting = Meeting(
        id=race_meeting_data["id"],
        status=race_meeting_data["status"],
        venueCode=race_meeting_data["venueCode"],
        totalNumberOfRace=race_meeting_data["totalNumberOfRace"],
        currentNumberOfRace=race_meeting_data["currentNumberOfRace"],
        date=meeting_date,  # Add date here
        races=races,
        pools=pools,
    )

    return meeting