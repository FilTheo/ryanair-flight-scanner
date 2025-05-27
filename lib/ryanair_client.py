import logging
from typing import List
from .ryanair_internal import Ryanair
from datetime import timedelta
import pandas as pd

from .models import (
    FlightSearchRequest,
    RyanairFlightResponse,
    AirportInfo,
)
from .config import Config

logger = logging.getLogger(__name__)


class RyanairAPIClient:
    """Simple client for interacting with Ryanair's API using the ryanair package"""

    def __init__(
        self,
        currency: str = "EUR",
    ):
        self.currency = currency
        self.ryanair = Ryanair(currency)
        logger.info(f"RyanairAPIClient initialized with currency: {currency}")

    async def close_session(self):
        """Closes the underlying HTTP session."""
        logger.info("RyanairAPIClient session closed.")

    def _convert_ryanair_flight(
        self, flight, origin: str, destination: str
    ) -> RyanairFlightResponse:
        """Convert a flight from the ryanair package to our internal format"""
        try:
            # Get flight attributes with fallbacks
            flight_number = getattr(flight, "flightNumber", "FR")
            departure_time = getattr(flight, "departureTime", None)

            # Calculate arrival time if not available (estimate based on departure + duration)
            arrival_time = getattr(flight, "arrivalTime", None)

            # Try to get duration from flight object
            duration_minutes = None
            if hasattr(flight, "duration"):
                duration_minutes = getattr(flight, "duration", None)

            # If we have departure but no arrival, calculate it from duration
            if arrival_time is None and departure_time and duration_minutes:
                from datetime import timedelta

                arrival_time = departure_time + timedelta(minutes=duration_minutes)
            elif arrival_time is None and departure_time:
                # Fallback: estimate based on typical flight time for route
                from datetime import timedelta

                # For European routes, estimate 1-4 hours based on distance
                estimated_duration = self._estimate_flight_duration(origin, destination)
                arrival_time = departure_time + timedelta(minutes=estimated_duration)
                duration_minutes = estimated_duration

            # Calculate duration from times if not available
            if duration_minutes is None and departure_time and arrival_time:
                duration_delta = arrival_time - departure_time
                duration_minutes = int(duration_delta.total_seconds() / 60)

            # Extract pricing information
            regular_fare = None
            if hasattr(flight, "price"):
                price_value = getattr(flight, "price", 0)
                currency_value = getattr(flight, "currency", self.currency)
                regular_fare = {
                    "amount": float(price_value) if price_value else 0.0,
                    "currency": currency_value,
                }
            elif hasattr(flight, "regularFare"):
                fare_obj = getattr(flight, "regularFare", None)
                if fare_obj:
                    regular_fare = {
                        "amount": getattr(fare_obj, "amount", 0.0),
                        "currency": getattr(fare_obj, "currency", self.currency),
                    }

            logger.debug(f"Flight attributes: {dir(flight)}")
            logger.debug(f"Extracted price info: {regular_fare}")

            return RyanairFlightResponse(
                flight_number=flight_number,
                origin=origin,
                destination=destination,
                departure_time=departure_time,
                arrival_time=arrival_time,
                duration_minutes=duration_minutes,
                regular_fare=regular_fare,
                operator="Ryanair",
            )
        except Exception as e:
            logger.error(f"Error converting flight data: {e}")
            logger.error(f"Flight object attributes: {dir(flight)}")
            return None

    def _estimate_flight_duration(self, origin: str, destination: str) -> int:
        """Estimate flight duration based on common routes (in minutes)"""
        # Common European route durations (rough estimates)
        route_durations = {
            ("STN", "SKG"): 200,  # London to Thessaloniki ~3h 20min
            ("STN", "BGY"): 120,  # London to Milan ~2h
            ("STN", "WMI"): 140,  # London to Warsaw ~2h 20min
            ("BGY", "SKG"): 140,  # Milan to Thessaloniki ~2h 20min
            ("WMI", "SKG"): 160,  # Warsaw to Thessaloniki ~2h 40min
        }

        # Check both directions
        route_key = (origin, destination)
        reverse_key = (destination, origin)

        if route_key in route_durations:
            return route_durations[route_key]
        elif reverse_key in route_durations:
            return route_durations[reverse_key]
        else:
            # Default fallback based on typical European flight times
            return 150  # 2.5 hours average

    async def search_flights(
        self, request: FlightSearchRequest
    ) -> List[RyanairFlightResponse]:
        """Search for flights using the simple ryanair package"""
        try:
            # Ensure departure_date is a date object
            base_departure_date = (
                request.departure_date.date()
                if hasattr(request.departure_date, "date")
                else request.departure_date
            )

            # Apply date flexibility
            flexibility_days = 0
            if (
                request.date_flexibility
                and request.date_flexibility.departure is not None
            ):
                flexibility_days = request.date_flexibility.departure

            date_from = base_departure_date - timedelta(days=flexibility_days)
            date_to = base_departure_date + timedelta(days=flexibility_days)

            logger.info(
                f"Searching flights from {request.origin} to {request.destination} "
                f"between {date_from} and {date_to} (flexibility: +/- {flexibility_days} days)"
            )

            all_flights = []

            # Iterate through each date in the flexible range to get ALL flights from each date
            current_date = date_from
            while current_date <= date_to:
                try:
                    logger.debug(f"Searching flights for specific date: {current_date}")

                    # Search for flights on this specific date only
                    # Use the same date for both from and to to get flights for just this day
                    daily_flights = self.ryanair.get_cheapest_flights(
                        request.origin, current_date, current_date
                    )

                    # Filter flights to the desired destination
                    matching_daily_flights = [
                        flight
                        for flight in daily_flights
                        if flight.destination == request.destination
                    ]

                    logger.debug(
                        f"Found {len(matching_daily_flights)} flights on {current_date}"
                    )

                    # Add all flights from this date to our collection
                    for flight in matching_daily_flights:
                        # Add date information to help identify which date this flight is from
                        logger.debug(
                            f"Adding flight {flight.flightNumber} from {current_date} "
                            f"with price {getattr(flight, 'price', 'N/A')}"
                        )
                        all_flights.append(flight)

                except Exception as e:
                    logger.warning(
                        f"Error searching flights for date {current_date}: {e}"
                    )

                # Move to next date
                current_date += timedelta(days=1)

            logger.info(
                f"Found total of {len(all_flights)} flights from {request.origin} to {request.destination} "
                f"across all dates from {date_from} to {date_to}"
            )

            # Convert to our internal format
            converted_flights = []
            for flight in all_flights:
                converted_flight = self._convert_ryanair_flight(
                    flight, request.origin, request.destination
                )
                if converted_flight:
                    converted_flights.append(converted_flight)

            logger.info(
                f"Successfully converted {len(converted_flights)} flights to internal format"
            )

            # Sort by departure date and then by price to show flights chronologically
            converted_flights.sort(
                key=lambda x: (
                    x.departure_time,
                    x.regular_fare.get("amount", 0) if x.regular_fare else 0,
                )
            )

            return converted_flights

        except Exception as e:
            logger.error(f"Error searching flights: {e}")
            raise

    async def get_airports(self) -> List[AirportInfo]:
        """Get list of airports from the ryanair-py CSV data"""
        logger.info("Getting airports list")
        try:
            # Load airports data from the CSV URL in config
            df = pd.read_csv(Config.AIRPORTS_CSV_URL, index_col=0)

            # Filter for airports that have IATA codes (Ryanair typically uses IATA codes)
            airports_with_iata = df[df["iata_code"].notna()]

            # Convert to our AirportInfo model
            airports = []
            for _, row in airports_with_iata.iterrows():
                airport_info = AirportInfo(
                    iata_code=row["iata_code"],
                    name=row["name"],
                    city_name=(
                        row["municipality"] if pd.notna(row["municipality"]) else ""
                    ),
                    country_name=(
                        row["iso_country"] if pd.notna(row["iso_country"]) else ""
                    ),
                    latitude=(
                        float(row["latitude_deg"])
                        if pd.notna(row["latitude_deg"])
                        else 0.0
                    ),
                    longitude=(
                        float(row["longitude_deg"])
                        if pd.notna(row["longitude_deg"])
                        else 0.0
                    ),
                )
                airports.append(airport_info)

            logger.info(f"Loaded {len(airports)} airports with IATA codes")
            return airports

        except Exception as e:
            logger.error(f"Error loading airports from CSV: {e}")
            # Return empty list instead of raising exception to match the current API behavior
            return []

    async def get_destinations_from_origin(
        self, origin_airport_code: str
    ) -> List[AirportInfo]:
        """Get destinations available from an origin airport"""
        logger.info(f"Getting destinations from {origin_airport_code}")
        # This could be implemented by making a test flight search
        # and extracting available destinations
        return []
