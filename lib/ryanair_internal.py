"""
Internal Ryanair API client to replace ryanair-py package.
This module provides a serverless-friendly implementation that avoids
the issubclass() issues with the original ryanair-py package.
"""

import logging
import requests
from datetime import datetime, date, time
from typing import Union, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Flight:
    """Flight data structure compatible with ryanair-py"""

    departureTime: datetime
    flightNumber: str
    price: float
    currency: str
    origin: str
    originFull: str
    destination: str
    destinationFull: str


@dataclass
class Trip:
    """Trip data structure compatible with ryanair-py"""

    totalPrice: float
    outbound: Flight
    inbound: Flight


class RyanairAPIError(Exception):
    """Custom exception for Ryanair API errors"""

    def __init__(self, message):
        super().__init__(f"Ryanair API: {message}")


class Ryanair:
    """
    Internal Ryanair API client that replicates ryanair-py functionality
    without problematic dependencies for serverless environments.
    """

    BASE_SERVICES_API_URL = "https://services-api.ryanair.com/farfnd/v4/"
    BASE_SITE_URL = "https://www.ryanair.com/ie/en"

    def __init__(self, currency: Optional[str] = None):
        self.currency = currency
        self._num_queries = 0
        self.session = requests.Session()
        self._initialize_session()

    def _initialize_session(self):
        """Initialize session with proper headers and cookies"""
        try:
            # Visit main website to get session cookies
            response = self.session.get(
                self.BASE_SITE_URL,
                timeout=10,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    )
                },
            )
            response.raise_for_status()
            logger.debug("Session initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize session cookies: {e}")

    def get_cheapest_flights(
        self,
        airport: str,
        date_from: Union[datetime, date, str],
        date_to: Union[datetime, date, str],
        destination_country: Optional[str] = None,
        custom_params: Optional[dict] = None,
        departure_time_from: Union[str, time] = "00:00",
        departure_time_to: Union[str, time] = "23:59",
        max_price: Optional[int] = None,
        destination_airport: Optional[str] = None,
    ) -> List[Flight]:
        """
        Get cheapest flights from Ryanair API
        """
        query_url = f"{self.BASE_SERVICES_API_URL}oneWayFares"

        params = {
            "departureAirportIataCode": airport,
            "outboundDepartureDateFrom": self._format_date_for_api(date_from),
            "outboundDepartureDateTo": self._format_date_for_api(date_to),
            "outboundDepartureTimeFrom": self._format_time_for_api(departure_time_from),
            "outboundDepartureTimeTo": self._format_time_for_api(departure_time_to),
        }

        if self.currency:
            params["currency"] = self.currency
        if destination_country:
            params["arrivalCountryCode"] = destination_country
        if max_price:
            params["priceValueTo"] = max_price
        if destination_airport:
            params["arrivalAirportIataCode"] = destination_airport
        if custom_params:
            params.update(custom_params)

        try:
            response_data = self._make_api_request(query_url, params)
            fares = response_data.get("fares", [])

            if fares:
                return [
                    self._parse_cheapest_flight(flight["outbound"]) for flight in fares
                ]
            return []

        except Exception as e:
            logger.error(f"Error fetching cheapest flights: {e}")
            return []

    def get_cheapest_return_flights(
        self,
        source_airport: str,
        date_from: Union[datetime, date, str],
        date_to: Union[datetime, date, str],
        return_date_from: Union[datetime, date, str],
        return_date_to: Union[datetime, date, str],
        destination_country: Optional[str] = None,
        custom_params: Optional[dict] = None,
        outbound_departure_time_from: Union[str, time] = "00:00",
        outbound_departure_time_to: Union[str, time] = "23:59",
        inbound_departure_time_from: Union[str, time] = "00:00",
        inbound_departure_time_to: Union[str, time] = "23:59",
        max_price: Optional[int] = None,
        destination_airport: Optional[str] = None,
    ) -> List[Trip]:
        """
        Get cheapest return flights from Ryanair API
        """
        query_url = f"{self.BASE_SERVICES_API_URL}roundTripFares"

        params = {
            "departureAirportIataCode": source_airport,
            "outboundDepartureDateFrom": self._format_date_for_api(date_from),
            "outboundDepartureDateTo": self._format_date_for_api(date_to),
            "inboundDepartureDateFrom": self._format_date_for_api(return_date_from),
            "inboundDepartureDateTo": self._format_date_for_api(return_date_to),
            "outboundDepartureTimeFrom": self._format_time_for_api(
                outbound_departure_time_from
            ),
            "outboundDepartureTimeTo": self._format_time_for_api(
                outbound_departure_time_to
            ),
            "inboundDepartureTimeFrom": self._format_time_for_api(
                inbound_departure_time_from
            ),
            "inboundDepartureTimeTo": self._format_time_for_api(
                inbound_departure_time_to
            ),
        }

        if self.currency:
            params["currency"] = self.currency
        if destination_country:
            params["arrivalCountryCode"] = destination_country
        if max_price:
            params["priceValueTo"] = max_price
        if destination_airport:
            params["arrivalAirportIataCode"] = destination_airport
        if custom_params:
            params.update(custom_params)

        try:
            response_data = self._make_api_request(query_url, params)
            fares = response_data.get("fares", [])

            if fares:
                return [
                    self._parse_cheapest_return_flights_as_trip(
                        trip["outbound"], trip["inbound"]
                    )
                    for trip in fares
                ]
            return []

        except Exception as e:
            logger.error(f"Error fetching return flights: {e}")
            return []

    def _make_api_request(self, url: str, params: dict) -> dict:
        """Make API request with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._num_queries += 1
                response = self.session.get(
                    url,
                    params=params,
                    timeout=30,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "application/json",
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                logger.warning(f"API request attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise RyanairAPIError(
                        f"Failed to fetch data after {max_retries} attempts: {e}"
                    )
            except Exception as e:
                logger.error(f"Unexpected error in API request: {e}")
                raise RyanairAPIError(f"Unexpected error: {e}")

    def _parse_cheapest_flight(self, flight_data: dict) -> Flight:
        """Parse flight data from API response"""
        try:
            price_info = flight_data.get("price", {})
            currency = price_info.get("currencyCode", self.currency or "EUR")

            if self.currency and self.currency != currency:
                logger.warning(
                    f"Requested flights in {self.currency} but API responded with {currency}"
                )

            departure_airport = flight_data.get("departureAirport", {})
            arrival_airport = flight_data.get("arrivalAirport", {})

            return Flight(
                origin=departure_airport.get("iataCode", ""),
                originFull=", ".join(
                    [
                        departure_airport.get("name", ""),
                        departure_airport.get("countryName", ""),
                    ]
                ).strip(", "),
                destination=arrival_airport.get("iataCode", ""),
                destinationFull=", ".join(
                    [
                        arrival_airport.get("name", ""),
                        arrival_airport.get("countryName", ""),
                    ]
                ).strip(", "),
                departureTime=datetime.fromisoformat(
                    flight_data.get("departureDate", "")
                ),
                flightNumber=self._format_flight_number(
                    flight_data.get("flightNumber", "")
                ),
                price=float(price_info.get("value", 0)),
                currency=currency,
            )
        except Exception as e:
            logger.error(f"Error parsing flight data: {e}")
            logger.error(f"Flight data: {flight_data}")
            raise RyanairAPIError(f"Failed to parse flight data: {e}")

    def _parse_cheapest_return_flights_as_trip(
        self, outbound_data: dict, inbound_data: dict
    ) -> Trip:
        """Parse return trip data from API response"""
        outbound = self._parse_cheapest_flight(outbound_data)
        inbound = self._parse_cheapest_flight(inbound_data)

        total_price = outbound.price + inbound.price

        return Trip(totalPrice=total_price, outbound=outbound, inbound=inbound)

    @staticmethod
    def _format_date_for_api(d: Union[datetime, date, str]) -> str:
        """Format date for API request"""
        if isinstance(d, str):
            return d
        elif isinstance(d, datetime):
            return d.strftime("%Y-%m-%d")
        elif isinstance(d, date):
            return d.strftime("%Y-%m-%d")
        else:
            raise ValueError(f"Invalid date format: {type(d)}")

    @staticmethod
    def _format_time_for_api(t: Union[time, str]) -> str:
        """Format time for API request"""
        if isinstance(t, str):
            return t
        elif isinstance(t, time):
            return t.strftime("%H:%M")
        else:
            raise ValueError(f"Invalid time format: {type(t)}")

    @staticmethod
    def _format_flight_number(flight_number: str) -> str:
        """Format flight number (add space after airline code)"""
        if len(flight_number) >= 2:
            return f"{flight_number[:2]} {flight_number[2:]}"
        return flight_number

    @property
    def num_queries(self) -> int:
        """Get number of queries made"""
        return self._num_queries
