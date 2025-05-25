from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


class PassengerInfo(BaseModel):
    adults: int = Field(ge=1, description="Number of adults (must be at least 1)")
    teens: int = Field(default=0, ge=0, description="Number of teens (12-15 years)")
    children: int = Field(
        default=0, ge=0, description="Number of children (2-11 years)"
    )
    infants: int = Field(default=0, ge=0, description="Number of infants (<2 years)")


class DateFlexibility(BaseModel):
    departure: int = Field(
        default=0, ge=0, description="Days flexibility for departure (+/- days)"
    )
    return_date: Optional[int] = Field(
        default=0,
        ge=0,
        alias="return",
        description="Days flexibility for return (+/- days)",
    )


class FlightSearchRequest(BaseModel):
    origin: str = Field(description="Origin airport IATA code (e.g., 'DUB')")
    destination: str = Field(
        description="Destination airport IATA code (e.g., 'STN') or 'ANY'"
    )
    departure_date: date = Field(description="Departure date in YYYY-MM-DD format")
    return_date: Optional[date] = Field(
        default=None, description="Return date for round-trip (optional)"
    )
    passengers: PassengerInfo
    date_flexibility: Optional[DateFlexibility] = Field(
        default=None, description="Date flexibility options"
    )
    max_connections: int = Field(
        default=1, ge=0, le=1, description="Maximum connections (0=direct, 1=one-stop)"
    )
    currency: str = Field(default="EUR", description="Currency code")
    include_connections: bool = Field(
        default=True, description="Whether to include connecting flights"
    )
    market: str = Field(
        default="EN", description="Market for the flight search (e.g., 'EN', 'IE')"
    )
    max_price: Optional[float] = Field(
        default=None, description="Maximum price for the flight search"
    )
    promo_code: Optional[str] = Field(
        default=None, description="Promotional code for the flight search"
    )


class FlightSegment(BaseModel):
    leg_type: str = Field(description="'outbound' or 'return'")
    segment_index: int = Field(description="0 for first segment, 1 for connection")
    origin_airport: str = Field(description="Origin airport IATA code")
    destination_airport: str = Field(description="Destination airport IATA code")
    departure_datetime: datetime = Field(description="Departure date and time")
    arrival_datetime: datetime = Field(description="Arrival date and time")
    flight_number: str = Field(description="Flight number")
    operator: str = Field(description="Airline operator")
    duration_minutes: int = Field(description="Flight duration in minutes")
    price: Optional[float] = Field(default=None, description="Segment price")
    currency: Optional[str] = Field(default=None, description="Price currency")


class LayoverInfo(BaseModel):
    airport: str = Field(description="Layover airport IATA code")
    duration_minutes: int = Field(description="Layover duration in minutes")


class FlightOption(BaseModel):
    type: str = Field(description="'direct' or 'one-stop'")
    total_price: float = Field(description="Total price for all passengers")
    currency: str = Field(description="Price currency")
    legs: List[FlightSegment] = Field(description="Flight segments")
    layovers: List[LayoverInfo] = Field(
        default=[], description="Layover information for connections"
    )


class FlightSearchResponse(BaseModel):
    search_query: Optional[FlightSearchRequest] = Field(
        default=None, description="Original search parameters"
    )
    flight_options: List[FlightOption] = Field(
        default=[], description="Available flight options sorted by price"
    )
    flights: Optional[List[FlightOption]] = Field(
        default=None,
        description="Available flight options sorted by price (alias for flight_options)",
    )
    search_request: Optional[FlightSearchRequest] = Field(
        default=None, description="Original search parameters (alias)"
    )
    total_results: Optional[int] = Field(
        default=0, description="Total number of results"
    )
    direct_flights_count: Optional[int] = Field(
        default=0, description="Number of direct flights"
    )
    connecting_flights_count: Optional[int] = Field(
        default=0, description="Number of connecting flights"
    )
    error: Optional[str] = Field(default=None, description="Error message if any")

    def model_post_init(self, __context) -> None:
        """Ensure flight_options is populated from flights if needed"""
        if self.flights and not self.flight_options:
            self.flight_options = self.flights
        elif self.flight_options and not self.flights:
            self.flights = self.flight_options


class AirportInfo(BaseModel):
    iata_code: str = Field(description="3-letter IATA airport code")
    name: str = Field(description="Airport name")
    city_name: str = Field(description="City name")
    country_name: str = Field(description="Country name")
    latitude: Optional[float] = Field(default=None, description="Airport latitude")
    longitude: Optional[float] = Field(default=None, description="Airport longitude")


class RyanairApiRequestParams(BaseModel):
    """Internal model for Ryanair API requests"""

    origin: str
    destination: str
    date_from: str
    date_to: str
    adults: int
    teens: int = 0
    children: int = 0
    infants: int = 0
    currency: str = "EUR"
    trip_type: str = "one-way"  # 'one-way' or 'round-trip'


class RyanairFlightData(BaseModel):
    """Internal model for raw Ryanair flight data"""

    flight_number: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    price: float
    currency: str
    duration: str
    operator: str = "Ryanair"


class RyanairApiResponse(BaseModel):
    """Internal model for Ryanair API responses"""

    flights: List[RyanairFlightData]
    currency: str
    total_results: int


class RyanairFlightResponse(BaseModel):
    """Internal model for individual Ryanair flight responses"""

    flight_number: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: Optional[int] = None
    regular_fare: Optional[dict] = None
    operator: str = "Ryanair"
