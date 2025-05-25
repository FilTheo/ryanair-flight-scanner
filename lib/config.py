import os
from typing import Dict, Any


class Config:
    # API Configuration
    RYANAIR_API_URL = os.getenv(
        "RYANAIR_API_URL",
        "https://www.ryanair.com/api/booking/v4",  # Default from previous RYANAIR_API_BASE_URL
    )
    # Example specific API endpoint URLs (these should be verified with actual Ryanair API docs)
    RYANAIR_FLIGHT_SEARCH_URL = os.getenv(
        "RYANAIR_FLIGHT_SEARCH_URL",
        f"{RYANAIR_API_URL}/availability",  # Example, may vary by market etc.
    )
    RYANAIR_AIRPORTS_LIST_URL = os.getenv(
        "RYANAIR_AIRPORTS_LIST_URL",
        "https://api.ryanair.com/aggregate/3/commonData/airports",
    )
    RYANAIR_ROUTES_URL = os.getenv(
        # Example: "https://services-api.ryanair.com/locate/v1/autocomplete/routes?departureAirportIataCode={origin_code}" # noqa: E501
        # Using a more structured one from client if possible
        "RYANAIR_ROUTES_URL",
        "https://www.ryanair.com/api/locate/v2/routes?departureAirportIataCode={origin_code}",  # noqa: E501 # Matches client usage pattern
    )

    APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
    APIFY_BASE_URL = os.getenv("APIFY_BASE_URL", "https://api.apify.com/v2")

    # Proxy Settings
    PROXY_SETTINGS = os.getenv("PROXY_SETTINGS", "")

    # Default Settings
    DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "EUR")
    DEFAULT_FLEX_DAYS = int(
        os.getenv("DEFAULT_FLEX_DAYS", "0")
    )  # Renamed from DEFAULT_DATE_FLEXIBILITY_DAYS

    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Cache Settings
    CACHE_TTL = int(
        os.getenv("CACHE_TTL", "900")
    )  # Renamed from CACHE_TTL_SECONDS (15 minutes)
    CACHE_MAXSIZE = int(
        os.getenv("CACHE_MAXSIZE", "1000")
    )  # Renamed from CACHE_MAX_SIZE

    # Connection Logic Settings (for FlightAnalyzer, not directly client)
    MIN_LAYOVER_MINUTES = int(os.getenv("MIN_LAYOVER_MINUTES", "90"))
    MAX_LAYOVER_MINUTES = int(os.getenv("MAX_LAYOVER_MINUTES", "360"))

    # Request Settings for RyanairAPIClient
    TIMEOUT = int(os.getenv("TIMEOUT", "30"))  # Renamed from REQUEST_TIMEOUT
    RETRIES = int(os.getenv("RETRIES", "3"))  # Renamed from MAX_RETRIES
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "1"))  # New, in seconds

    # Ryanair API Headers
    RYANAIR_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",  # Added text/plain for broader compatibility
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json;charset=UTF-8",  # Added charset
        # Add any other common headers Ryanair might expect
        # "Referer": "https://www.ryanair.com/",
        # "Origin": "https://www.ryanair.com",
    }

    # Airport Data URL (fallback)
    AIRPORTS_CSV_URL = os.getenv(
        "AIRPORTS_CSV_URL",
        "https://raw.githubusercontent.com/cohaolain/ryanair-py/develop/ryanair/airports.csv",
    )


# The get_config() function might not be needed if direct class access Config.VALUE is used.
# If it's still used elsewhere, it would need to be updated or removed.
# For now, I will comment it out as the client and app will use Config. directly.

# def get_config() -> Dict[str, Any]:
#     """Get all configuration as a dictionary"""
#     return {
# "ryanair_api_url": Config.RYANAIR_API_URL,
# "ryanair_flight_search_url": Config.RYANAIR_FLIGHT_SEARCH_URL,
# "ryanair_airports_list_url": Config.RYANAIR_AIRPORTS_LIST_URL,
# "ryanair_routes_url": Config.RYANAIR_ROUTES_URL,
# "apify_token": Config.APIFY_TOKEN,
# "apify_base_url": Config.APIFY_BASE_URL,
# "proxy_settings": Config.PROXY_SETTINGS,
# "default_currency": Config.DEFAULT_CURRENCY,
# "default_flex_days": Config.DEFAULT_FLEX_DAYS,
# "log_level": Config.LOG_LEVEL,
# "cache_ttl": Config.CACHE_TTL,
# "cache_maxsize": Config.CACHE_MAXSIZE,
# "min_layover_minutes": Config.MIN_LAYOVER_MINUTES,
# "max_layover_minutes": Config.MAX_LAYOVER_MINUTES,
# "timeout": Config.TIMEOUT,
# "retries": Config.RETRIES,
# "retry_delay": Config.RETRY_DELAY,
# "ryanair_headers": Config.RYANAIR_HEADERS,
# "airports_csv_url": Config.AIRPORTS_CSV_URL,
#     }
