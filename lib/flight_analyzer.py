import logging
from typing import List, Optional
from datetime import datetime, timedelta

from .config import Config
from .models import (
    FlightSearchRequest,
    FlightSearchResponse,
    FlightOption,
    FlightSegment,
    LayoverInfo,
    RyanairFlightResponse,
)
from .ryanair_client import RyanairAPIClient

logger = logging.getLogger(__name__)

MIN_LAYOVER_MINUTES = Config.MIN_LAYOVER_MINUTES
MAX_LAYOVER_MINUTES = Config.MAX_LAYOVER_MINUTES


class FlightAnalyzer:
    """Analyzes flight data and finds connections"""

    def __init__(self, ryanair_client: RyanairAPIClient):
        self.client = ryanair_client
        self.min_layover = timedelta(minutes=MIN_LAYOVER_MINUTES)
        self.max_layover = timedelta(minutes=MAX_LAYOVER_MINUTES)

    async def search_flights(
        self, request: FlightSearchRequest
    ) -> FlightSearchResponse:
        """Main flight search method that handles both direct and connecting flights"""
        try:
            # Handle "ANY" destination searches
            if request.destination.upper() == "ANY":
                return await self._search_any_destination(request)

            # Search for direct flights
            direct_flights = await self._search_direct_flights(request)

            # Search for connecting flights if enabled
            connecting_flights = []
            if request.max_connections > 0:
                connecting_flights = await self._search_connecting_flights(request)

            # Combine and sort results
            all_flights = direct_flights + connecting_flights
            all_flights.sort(key=lambda x: x.total_price)

            return FlightSearchResponse(
                flights=all_flights,
                search_request=request,
                total_results=len(all_flights),
                direct_flights_count=len(direct_flights),
                connecting_flights_count=len(connecting_flights),
            )

        except Exception as e:
            logger.error(f"Flight search failed: {e}")
            return FlightSearchResponse(
                flights=[],
                search_request=request,
                total_results=0,
                direct_flights_count=0,
                connecting_flights_count=0,
                error=str(e),
            )

    async def _search_direct_flights(
        self, request: FlightSearchRequest
    ) -> List[FlightOption]:
        """Search for direct flights"""
        logger.info(
            f"Searching direct flights from {request.origin} to {request.destination}"
        )

        ryanair_flights = await self.client.search_flights(request)
        flight_options = []

        for flight in ryanair_flights:
            try:
                option = self._convert_to_flight_option(flight, is_direct=True)
                if option:
                    flight_options.append(option)
            except Exception as e:
                logger.warning(f"Failed to convert flight to option: {e}")
                continue

        return flight_options

    async def _search_connecting_flights(
        self, request: FlightSearchRequest
    ) -> List[FlightOption]:
        """Search for flights with one connection"""
        logger.info(
            f"Searching connecting flights from {request.origin} to {request.destination}"
        )

        # Get potential hub airports
        hub_airports = self._get_potential_hubs(request.origin, request.destination)

        connecting_flights = []

        for hub in hub_airports:
            try:
                connections = await self._find_connections_via_hub(request, hub)
                connecting_flights.extend(connections)
            except Exception as e:
                logger.warning(f"Failed to find connections via {hub}: {e}")
                continue

        return connecting_flights

    async def _search_any_destination(
        self, request: FlightSearchRequest
    ) -> FlightSearchResponse:
        """Search for flights to any destination from origin"""
        logger.info(f"Searching flights from {request.origin} to ANY destination")

        # Get all possible destinations from origin
        destinations = await self.client.get_destinations_from_origin(request.origin)

        all_flights = []

        for destination in destinations[:50]:  # Limit to avoid too many requests
            try:
                # Create a new request for each destination
                dest_request = FlightSearchRequest(
                    origin=request.origin,
                    destination=destination,
                    departure_date=request.departure_date,
                    return_date=request.return_date,
                    passengers=request.passengers,
                    date_flexibility=request.date_flexibility,
                    max_connections=0,  # Only direct flights for ANY searches
                )

                direct_flights = await self._search_direct_flights(dest_request)
                all_flights.extend(direct_flights)

            except Exception as e:
                logger.warning(f"Failed to search flights to {destination}: {e}")
                continue

        # Sort by price
        all_flights.sort(key=lambda x: x.total_price)

        return FlightSearchResponse(
            flights=all_flights[:100],  # Limit results
            search_request=request,
            total_results=len(all_flights),
            direct_flights_count=len(all_flights),
            connecting_flights_count=0,
        )

    def _get_potential_hubs(self, origin: str, destination: str) -> List[str]:
        """Get potential hub airports for connections"""
        # Common Ryanair hubs
        major_hubs = [
            "STN",  # London Stansted
            "DUB",  # Dublin
            "BGY",  # Milan Bergamo
            "CRL",  # Brussels Charleroi
            "BVA",  # Paris Beauvais
            "CIA",  # Rome Ciampino
            "MAD",  # Madrid
            "BCN",  # Barcelona
            "OPO",  # Porto
            "EDI",  # Edinburgh
            "MAN",  # Manchester
            "BRE",  # Bremen
            "WMI",  # Warsaw Modlin
        ]

        # Filter out origin and destination
        potential_hubs = [hub for hub in major_hubs if hub not in [origin, destination]]

        return potential_hubs

    async def _find_connections_via_hub(
        self, request: FlightSearchRequest, hub: str
    ) -> List[FlightOption]:
        """Find connecting flights via a specific hub"""
        connections = []

        try:
            # Search first leg: origin to hub
            first_leg_request = FlightSearchRequest(
                origin=request.origin,
                destination=hub,
                departure_date=request.departure_date,
                return_date=None,  # One way for first leg
                passengers=request.passengers,
                date_flexibility=request.date_flexibility,  # Pass flexibility for first leg
                max_connections=0,
            )
            logger.debug(f"First leg request for hub {hub}: {first_leg_request}")
            first_leg_flights = await self.client.search_flights(first_leg_request)
            logger.info(
                f"Found {len(first_leg_flights)} flights for first leg to {hub}"
            )

            if not first_leg_flights:
                return []

            # Search second leg: hub to destination
            # The base departure date for the second leg should consider the arrival of the first leg,
            # but for simplicity with the current ryanair library, we search around the original request's departure date.
            # A more advanced implementation would iterate through first_leg_flights and search for second legs
            # based on their arrival times.

            departure_flexibility_days = 0
            if (
                request.date_flexibility
                and request.date_flexibility.departure is not None
            ):
                departure_flexibility_days = request.date_flexibility.departure

            all_second_leg_flights = []

            # Iterate from -flexibility to +flexibility days for the second leg
            for days_offset in range(
                -departure_flexibility_days, departure_flexibility_days + 1
            ):
                search_date_dt = request.departure_date + timedelta(days=days_offset)
                # Ensure search_date is a date object, not datetime
                search_date = (
                    search_date_dt.date()
                    if hasattr(search_date_dt, "date")
                    else search_date_dt
                )

                logger.info(
                    f"Searching second leg for hub {hub} on {search_date} (offset: {days_offset} days)"
                )

                # For the second leg, we create a new FlightSearchRequest.
                # The date_flexibility for this specific call to ryanair_client.search_flights
                # should be 0, as we are already iterating through the flexible dates.
                second_leg_search_request = FlightSearchRequest(
                    origin=hub,
                    destination=request.destination,
                    departure_date=search_date,
                    return_date=None,  # one way for this leg
                    passengers=request.passengers,
                    date_flexibility={
                        "departure": 0,
                        "return_date": 0,
                    },  # No further flexibility here
                    max_connections=0,
                )
                logger.debug(
                    f"Second leg request for hub {hub} on {search_date}: {second_leg_search_request}"
                )

                try:
                    current_second_leg_flights = await self.client.search_flights(
                        second_leg_search_request
                    )
                    all_second_leg_flights.extend(current_second_leg_flights)
                    logger.info(
                        f"Found {len(current_second_leg_flights)} flights for second leg from {hub} on {search_date}"
                    )
                except Exception as e_sl:
                    logger.warning(
                        f"Error searching second leg from {hub} on {search_date}: {e_sl}"
                    )
                    continue

            if not all_second_leg_flights:
                logger.info(
                    f"No second leg flights found from hub {hub} to {request.destination} within flexible dates."
                )
                return []

            # Try to match first and second legs
            logger.info(
                f"Matching {len(first_leg_flights)} first-leg flights with {len(all_second_leg_flights)} second-leg flights for hub {hub}"
            )
            leg_connections = self._match_flight_legs(
                first_leg_flights, all_second_leg_flights, hub
            )
            connections.extend(leg_connections)
            logger.info(f"Found {len(leg_connections)} connections via hub {hub}")

        except Exception as e:
            logger.error(f"Error finding connections via {hub}: {e}", exc_info=True)

        return connections

    async def _search_second_leg(
        self,
        origin: str,
        destination: str,
        date: datetime,
        passengers,
        date_flexibility_departure: int = 0,
    ) -> List[RyanairFlightResponse]:
        """Search for second leg of connection, incorporating flexibility"""

        # Ensure date is a date object, not datetime, for the request
        search_date_obj = date.date() if hasattr(date, "date") else date

        second_leg_request = FlightSearchRequest(
            origin=origin,
            destination=destination,
            departure_date=search_date_obj,
            return_date=None,
            passengers=passengers,
            date_flexibility={
                "departure": date_flexibility_departure,
                "return_date": 0,
            },  # Pass flexibility
            max_connections=0,
        )
        logger.debug(
            f"Second leg search request: {second_leg_request.model_dump_json(indent=2)}"
        )
        return await self.client.search_flights(second_leg_request)

    def _match_flight_legs(
        self,
        first_leg_flights: List[RyanairFlightResponse],
        second_leg_flights: List[RyanairFlightResponse],
        hub: str,
    ) -> List[FlightOption]:
        """Match first and second leg flights to create valid connections"""
        connections = []

        for first_flight in first_leg_flights:
            for second_flight in second_leg_flights:
                try:
                    connection = self._create_connection(
                        first_flight, second_flight, hub
                    )
                    if connection:
                        connections.append(connection)
                except Exception as e:
                    logger.warning(f"Failed to create connection: {e}")
                    continue

        return connections

    def _create_connection(
        self,
        first_flight: RyanairFlightResponse,
        second_flight: RyanairFlightResponse,
        hub: str,
    ) -> Optional[FlightOption]:
        """Create a connection flight option from two legs"""

        # Validate layover time
        layover_time = second_flight.departure_time - first_flight.arrival_time

        if layover_time < self.min_layover or layover_time > self.max_layover:
            return None

        # Create flight segments
        first_segment = FlightSegment(
            leg_type="outbound",
            segment_index=0,
            origin_airport=first_flight.origin,
            destination_airport=first_flight.destination,
            departure_datetime=first_flight.departure_time,
            arrival_datetime=first_flight.arrival_time,
            flight_number=first_flight.flight_number,
            operator=first_flight.operator,
            duration_minutes=(
                int(first_flight.duration_minutes)
                if first_flight.duration_minutes
                else 0
            ),
            price=(
                first_flight.regular_fare.get("amount", 0)
                if first_flight.regular_fare
                else 0
            ),
            currency=(
                first_flight.regular_fare.get("currency", "EUR")
                if first_flight.regular_fare
                else "EUR"
            ),
        )

        second_segment = FlightSegment(
            leg_type="outbound",
            segment_index=1,
            origin_airport=second_flight.origin,
            destination_airport=second_flight.destination,
            departure_datetime=second_flight.departure_time,
            arrival_datetime=second_flight.arrival_time,
            flight_number=second_flight.flight_number,
            operator=second_flight.operator,
            duration_minutes=(
                int(second_flight.duration_minutes)
                if second_flight.duration_minutes
                else 0
            ),
            price=(
                second_flight.regular_fare.get("amount", 0)
                if second_flight.regular_fare
                else 0
            ),
            currency=(
                second_flight.regular_fare.get("currency", "EUR")
                if second_flight.regular_fare
                else "EUR"
            ),
        )

        # Create layover info
        layover = LayoverInfo(
            airport=hub,
            duration_minutes=int(layover_time.total_seconds() / 60),
        )

        # Calculate totals
        total_price = first_segment.price + second_segment.price

        return FlightOption(
            type="one-stop",
            total_price=total_price,
            currency=first_segment.currency,
            legs=[first_segment, second_segment],
            layovers=[layover],
        )

    def _convert_to_flight_option(
        self, flight: RyanairFlightResponse, is_direct: bool = True
    ) -> Optional[FlightOption]:
        """Convert a Ryanair flight response to a FlightOption"""
        try:
            segment = FlightSegment(
                leg_type="outbound",
                segment_index=0,
                origin_airport=flight.origin,
                destination_airport=flight.destination,
                departure_datetime=flight.departure_time,
                arrival_datetime=flight.arrival_time,
                flight_number=flight.flight_number,
                operator=flight.operator,
                duration_minutes=(
                    int(flight.duration_minutes) if flight.duration_minutes else 0
                ),
                price=(
                    flight.regular_fare.get("amount", 0) if flight.regular_fare else 0
                ),
                currency=(
                    flight.regular_fare.get("currency", "EUR")
                    if flight.regular_fare
                    else "EUR"
                ),
            )

            return FlightOption(
                type="direct",
                total_price=segment.price,
                currency=segment.currency,
                legs=[segment],
                layovers=[],
            )

        except Exception as e:
            logger.error(f"Failed to convert flight to option: {e}")
            return None
