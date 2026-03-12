from pydantic import BaseModel
from typing import Optional, List, Dict


class Departure(BaseModel):
    iata: Optional[str]
    city: Optional[str]

class Destination(BaseModel):
    iata: Optional[str]
    city: Optional[str]
    confidence: float = 0.0

class TerminalField(BaseModel):
    value: Optional[str]
    source: Optional[str]
    confidence: float = 0.0

class BoardingPass(BaseModel):
    airport: Departure
    destination: Destination
    terminal: TerminalField
    gate: Optional[str]
    flight_number: Optional[str]
    departure_time_local: Optional[str]
    boarding_time_local: Optional[str]
    raw_text: Optional[str]
    assumptions: List[str] = []

class Lounge(BaseModel):
    lounge_id: str
    name: str
    airport_code: str
    terminal: Optional[str] = None
    opening_hours: str          # JSON string (day schedule) or simple range
    amenities: str
    access_notes: Optional[str] = None
    conditions: List[str] = []
    image_url: Optional[str] = None
    detail_url: Optional[str] = None
    source_url: Optional[str] = None

class LoungeRecommendation(BaseModel):
    lounge_id: str
    name: str
    terminal: Optional[str]
    opening_hours: str
    amenities: str
    source_url: Optional[str]