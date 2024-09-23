from typing import List, Literal, Optional
from pydantic import BaseModel, field_validator


class RaceTrack(BaseModel):
    description_en: Optional[str]
    description_ch: Optional[str]


class RaceCourse(BaseModel):
    description_en: Optional[str]
    description_ch: Optional[str]
    displayCode: Optional[str]


class Runner(BaseModel):
    id: str
    no: Optional[int]
    standbyNo: Optional[int]
    status: Literal["Standby", "Declared", "Withdrawn"]
    name_ch: str
    name_en: str
    horse_id: str
    barrierDrawNumber: Optional[int]
    handicapWeight: Optional[int]
    jockey_name_en: Optional[str]
    jockey_name_ch: Optional[str]
    trainer_name_en: Optional[str]
    trainer_name_ch: Optional[str]
    winOdds: Optional[float]
    placeOdds: Optional[float] = None

    @field_validator("winOdds", "placeOdds", mode="before")
    def validate_win_odds(cls, value):
        if value == "" or value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    @field_validator(
        "no", "barrierDrawNumber", "handicapWeight", "standbyNo", mode="before"
    )
    def validate_int_field(cls, value):
        if value == "" or value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None


class Race(BaseModel):
    id: str
    no: int
    status: str
    raceName_en: Optional[str]
    raceName_ch: Optional[str]
    postTime: Optional[str]
    distance: Optional[int]
    wageringFieldSize: Optional[int]
    raceTrack: Optional[RaceTrack]
    raceCourse: Optional[RaceCourse]
    runners: List[Runner]


class Pool(BaseModel):
    id: str
    oddsType: Optional[str]
    status: Optional[str]
    investment: Optional[float]
    totalInvestment: Optional[float]  # Total investment in the pool
    mergedPoolId: Optional[str]
    lastUpdateTime: Optional[str]


class Meeting(BaseModel):
    id: str
    status: str
    venueCode: str
    totalNumberOfRace: int
    currentNumberOfRace: int
    date: str
    races: List[Race]
    pools: List[Pool]
