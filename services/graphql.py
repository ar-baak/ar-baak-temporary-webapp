import httpx
from typing import Dict, List
from utils.logger import logger

GRAPHQL_ENDPOINT = "https://info.cld.hkjc.com/graphql/base/"


def send_graphql_query(payload: Dict) -> Dict:
    """Sends a GraphQL query and returns the response."""
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(GRAPHQL_ENDPOINT, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e}")
        return {}
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        return {}


def build_meeting_payload(date: str, venue: str) -> Dict:
    """Builds the payload for the GraphQL POST request to get race meeting info."""
    query = """
    fragment raceFragment on Race {
      id
      no
      status
      raceName_en
      raceName_ch
      postTime
      country_en
      country_ch
      distance
      wageringFieldSize
      go_en
      go_ch
      ratingType
      raceTrack {
        description_en
        description_ch
      }
      raceCourse {
        description_en
        description_ch
        displayCode
      }
      raceClass_en
      raceClass_ch
      judgeSigns {
        value_en
      }
    }

    fragment racingBlockFragment on RaceMeeting {
      jpEsts: pmPools(
        oddsTypes: [TCE, TRI, FF, QTT, DT, TT, SixUP]
        filters: ["jackpot", "estimatedDividend"]
      ) {
        leg {
          number
          races
        }
        oddsType
        jackpot
        estimatedDividend
        mergedPoolId
      }
      poolInvs: pmPools(
        oddsTypes: [WIN, PLA, QIN, QPL, CWA, CWB, CWC, IWN, FCT, TCE, TRI, FF, QTT, DBL, TBL, DT, TT, SixUP]
      ) {
        id
        leg {
          races
        }
      }
      penetrometerReadings(filters: ["first"]) {
        reading
        readingTime
      }
      hammerReadings(filters: ["first"]) {
        reading
        readingTime
      }
      changeHistories(filters: ["top3"]) {
        type
        time
        raceNo
        runnerNo
        horseName_ch
        horseName_en
        jockeyName_ch
        jockeyName_en
        scratchHorseName_ch
        scratchHorseName_en
        handicapWeight
        scrResvIndicator
      }
    }

    fragment racingFoPoolFragment on RacingFoPool {
      instNo
      poolId
      oddsType
      status
      sellStatus
      otherSelNo
      inplayUpTo
      expStartDateTime
      expStopDateTime
      raceStopSellNo
      raceStopSellStatus
      includeRaces
      excludeRaces
      lastUpdateTime
      selections {
        order
        number
        code
        name_en
        name_ch
        scheduleRides
        remainingRides
        points
        lineId
        combId
        combStatus
        openOdds
        prevOdds
        currentOdds
        results {
          raceNo
          points
          point1st
          point2nd
          point3rd
          dhRmk1st
          dhRmk2nd
          dhRmk3rd
          count1st
          count2nd
          count3rd
          count4th
          numerator4th
          denominator4th
        }
      }
      otherSelections {
        order
        code
        name_en
        name_ch
        scheduleRides
        remainingRides
        points
        results {
          raceNo
          points
          point1st
          point2nd
          point3rd
          dhRmk1st
          dhRmk2nd
          dhRmk3rd
          count1st
          count2nd
          count3rd
          count4th
          numerator4th
          denominator4th
        }
      }
    }

    query racing($date: String, $venueCode: String, $foOddsTypes: [OddsType], $foFilter: [String], $resultOddsType: [OddsType]) {
      timeOffset {
        rc
      }
      activeMeetings: raceMeetings {
        id
        venueCode
        date
        status
        races {
          no
          postTime
          status
          wageringFieldSize
        }
      }
      raceMeetings(date: $date, venueCode: $venueCode) {
        id
        status
        venueCode
        date
        totalNumberOfRace
        currentNumberOfRace
        dateOfWeek
        meetingType
        totalInvestment
        country {
          code
          namech
          nameen
          seq
        }
        races {
          ...raceFragment
          runners {
            id
            no
            standbyNo
            status
            name_ch
            name_en
            horse {
              id
              code
            }
            color
            barrierDrawNumber
            handicapWeight
            currentWeight
            currentRating
            internationalRating
            gearInfo
            racingColorFileName
            allowance
            trainerPreference
            last6run
            saddleClothNo
            trumpCard
            priority
            finalPosition
            deadHeat
            winOdds
            jockey {
              code
              name_en
              name_ch
            }
            trainer {
              code
              name_en
              name_ch
            }
          }
        }
        obSt: pmPools(oddsTypes: [WIN, PLA]) {
          leg {
            races
          }
          oddsType
          comingleStatus
        }
        poolInvs: pmPools(
          oddsTypes: [WIN, PLA, QIN, QPL, CWA, CWB, CWC, IWN, FCT, TCE, TRI, FF, QTT, DBL, TBL, DT, TT, SixUP]
        ) {
          id
          leg {
            number
            races
          }
          status
          sellStatus
          oddsType
          investment
          mergedPoolId
          lastUpdateTime
        }
        resPools: pmPools(oddsTypes: $resultOddsType) {
          leg {
            number
            races
          }
          status
          oddsType
          name_en
          name_ch
          lastUpdateTime
          dividends(officialOnly: true) {
            winComb
            type
            div
            seq
            status
            guarantee
            partial
            partialUnit
          }
          cWinSelections {
            composite
            name_ch
            name_en
            starters
          }
        }
        ...racingBlockFragment
        pmPools(oddsTypes: []) {
          id
        }
        foPools(oddsTypes: $foOddsTypes, filters: $foFilter) {
          ...racingFoPoolFragment
        }
        jkcInstNo: foPools(oddsTypes: [JKC], filters: ["top"]) {
          instNo
        }
        tncInstNo: foPools(oddsTypes: [TNC], filters: ["top"]) {
          instNo
        }
      }
    }
    """

    return {
        "operationName": "racing",
        "variables": {
            "date": date,
            "venueCode": venue,
            "foOddsTypes": [],
            "foFilter": ["top"],
            "resultOddsType": [],
        },
        "query": query,
    }


def build_odds_payload(
    date: str, venue: str, race_no: int, odds_types: List[str]
) -> Dict:
    """Builds the payload for the GraphQL POST request to fetch odds."""
    query = """
    query racing($date: String, $venueCode: String, $oddsTypes: [OddsType], $raceNo: Int) {
      raceMeetings(date: $date, venueCode: $venueCode) {
        pmPools(oddsTypes: $oddsTypes, raceNo: $raceNo) {
          id
          status
          sellStatus
          oddsType
          lastUpdateTime
          guarantee
          minTicketCost
          name_en
          name_ch
          leg {
            number
            races
          }
          cWinSelections {
            composite
            name_ch
            name_en
            starters
          }
          oddsNodes {
            combString
            oddsValue
            hotFavourite
            oddsDropValue
            bankerOdds {
              combString
              oddsValue
            }
          }
        }
      }
    }
    """
    return {
        "operationName": "racing",
        "variables": {
            "date": date,
            "venueCode": venue,
            "raceNo": race_no,
            "oddsTypes": odds_types,
        },
        "query": query,
    }
