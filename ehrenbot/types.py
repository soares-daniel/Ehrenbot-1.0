from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

class PogoEventResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    eventID: str
    name: str
    eventType: str
    heading: str
    link: str
    image: str
    start: str
    end: str
    extraData: Optional[dict] = {}  # TODO: Add model for extraData


class PogoEventEmbedData(PogoEventResponse):
    model_config = ConfigDict(extra="ignore")
    notes: list[str]
    color: int = 0x708090
    footer: str = "From Leekduck via ScrapedDuck"
    thumbnail: Optional[str] = None


class PogoEventDates(BaseModel):
    eventId: str
    start: datetime
    end: datetime


class PokeBattlerArticle(BaseModel):
    title: str
    url: str
    image: str
    published: float
