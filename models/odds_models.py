from typing import Optional, List
from pydantic import BaseModel


class OddsNode(BaseModel):
    """Represents a single odds node from the GraphQL response."""

    combString: str  # Combination string (typically the runner number)
    oddsValue: float  # Odds value for the runner
    hotFavourite: Optional[bool] = False  # Is this runner a hot favourite?
    oddsDropValue: Optional[float] = 0.0  # Change in odds value
    bankerOdds: Optional[List[dict]] = []  # Additional banker odds (if applicable)


class Pool(BaseModel):
    """Represents a pool of odds for a race."""

    id: str  # Unique identifier for the pool
    status: Optional[str]
    oddsType: Optional[str]
    lastUpdateTime: Optional[str]
    guarantee: Optional[float]
    minTicketCost: Optional[float]
    name_en: Optional[str]
    name_ch: Optional[str]
    oddsNodes: List[OddsNode]  # List of odds nodes for runners


class OddsResponse(BaseModel):
    """Represents the response of the GraphQL odds query."""

    raceNo: int  # The race number
    oddsType: Optional[str]
    oddsNodes: List[OddsNode]  # The odds data for the runners
