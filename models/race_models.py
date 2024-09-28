from datetime import datetime
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
    status: Literal["Standby", "Declared", "Withdrawn", "Ran", "Scratched"]
    name_ch: str
    name_en: str
    horse_id: str
    barrierDrawNumber: Optional[int]
    handicapWeight: Optional[int]
    jockey_name_en: Optional[str]
    jockey_name_ch: Optional[str]
    trainer_name_en: Optional[str]
    trainer_name_ch: Optional[str]
    winOdds: Optional[float] = None
    placeOdds: Optional[float] = None

    @field_validator("winOdds", "placeOdds", mode="before")
    def validate_win_odds(cls, value) -> Optional[float]:
        if value in ("", "SCR", None):
            return None
        try:
            return float(value)
        except ValueError:
            return None

    @field_validator(
        "no", "barrierDrawNumber", "handicapWeight", "standbyNo", mode="before"
    )
    def validate_int_field(cls, value) -> Optional[float]:
        if value in ("", "SCR", None):
            return None
        try:
            return int(value)
        except ValueError:
            return None

    class Config:
        validate_assignment = True


class Race(BaseModel):
    id: str
    no: int
    status: str
    raceName_en: Optional[str]
    raceName_ch: Optional[str]
    postTime: Optional[datetime]
    distance: Optional[int]
    wageringFieldSize: Optional[int]
    raceTrack: Optional[RaceTrack]
    raceCourse: Optional[RaceCourse]
    runners: List[Runner]

    @field_validator("postTime", mode="before")
    def validate_date_field(cls, value):
        if value == "" or value is None:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


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
    date: datetime
    races: List[Race]
    pools: List[Pool]

    @field_validator("date", mode="before")
    def validate_date_field(cls, value):
        if value == "" or value is None:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None
