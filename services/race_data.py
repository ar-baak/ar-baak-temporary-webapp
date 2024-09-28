from typing import Dict, List
from services.graphql import send_graphql_query, build_meeting_payload
from models.race_models import (
    Country,
    Meeting,
    Pool,
    Race,
    RaceCourse,
    RaceTrack,
    Runner,
)
from utils.logger import logger


def fetch_race_meetings() -> Dict:
    """Fetch race meeting details from GraphQL."""
    payload = build_meeting_payload()
    return send_graphql_query(payload)


def parse_runners(runner_data: Dict) -> Runner:
    """Parse a single runner's data and return a Runner object."""
    return Runner(
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
        winOdds=runner_data.get("winOdds"),
        placeOdds=runner_data.get("placeOdds"),
    )


def parse_races(race_meeting_data: Dict) -> List[Race]:
    """Parse the races from a meeting and return a list of Race objects."""
    races = []
    for race in race_meeting_data["races"]:
        runners = [parse_runners(runner_data) for runner_data in race["runners"]]

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
    return races


def parse_pools(race_meeting_data: Dict) -> List[Pool]:
    """Parse the pools from a meeting and return a list of Pool objects."""
    pools = []
    for pool in race_meeting_data.get("poolInvs", []):
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
    return pools


def process_meeting_response(response: Dict) -> List[Meeting]:
    """Process the GraphQL race meeting response and return a list of structured Meeting data."""
    if not response or "data" not in response:
        logger.error("Invalid response or no data")
        return []

    race_meetings = response["data"]["raceMeetings"]
    meetings = []

    for race_meeting_data in race_meetings:
        # Extract date from the response
        meeting_date = race_meeting_data.get("date", "Unknown Date")

        # Extract country information
        country_data = race_meeting_data.get("country")
        country = Country.model_validate(country_data[0]) if country_data else None

        # Parse races and pools
        races = parse_races(race_meeting_data)
        pools = parse_pools(race_meeting_data)

        # Create a Meeting object
        meeting = Meeting(
            id=race_meeting_data["id"],
            status=race_meeting_data["status"],
            venueCode=race_meeting_data["venueCode"],
            totalNumberOfRace=race_meeting_data["totalNumberOfRace"],
            currentNumberOfRace=race_meeting_data["currentNumberOfRace"],
            date=meeting_date,
            meetingType=race_meeting_data.get("meetingType"),
            country=country,
            races=races,
            pools=pools,
        )
        meetings.append(meeting)

    return meetings
