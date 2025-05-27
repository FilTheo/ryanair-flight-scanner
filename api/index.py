from fastapi import FastAPI, HTTPException, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import requests.exceptions
import logging
import sys

# Import your models and client
from lib.models import AirportInfo, FlightSearchRequest, FlightSearchResponse
from lib.ryanair_client import RyanairAPIClient
from lib.flight_analyzer import FlightAnalyzer
from lib.config import Config

# Configure logging for Vercel
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Ryanair Flight Scanner API",
    description="API for searching Ryanair flights, including direct and connecting flights.",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RyanairAPIClient globally for Vercel (no startup events)
logger.info("Initializing RyanairAPIClient globally")
ryanair_client = RyanairAPIClient(
    currency=Config.DEFAULT_CURRENCY,
)
logger.info("RyanairAPIClient initialized successfully")


def get_ryanair_client() -> RyanairAPIClient:
    return ryanair_client


# Root endpoint
@app.get("/", tags=["Root"])
async def read_root():
    """Root endpoint, returns a welcome message."""
    return {"message": "Welcome to the Ryanair Flight Scanner API"}


# Health endpoint
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# Airport endpoints
@app.get("/api/airports", response_model=List[AirportInfo], tags=["Airports"])
async def get_all_airports(client: RyanairAPIClient = Depends(get_ryanair_client)):
    """Get a list of all Ryanair airports."""
    try:
        airports = await client.get_airports()
        if not airports:
            raise HTTPException(
                status_code=404,
                detail="No airports could be fetched from Ryanair or its fallback.",
            )
        return airports
    except requests.exceptions.RequestException as req_ex:
        raise HTTPException(
            status_code=503, detail=f"Error connecting to Ryanair services: {req_ex}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )


@app.get(
    "/api/airports/{origin_airport_code}/destinations",
    response_model=List[AirportInfo],
    tags=["Airports"],
)
async def get_destinations(
    origin_airport_code: str, client: RyanairAPIClient = Depends(get_ryanair_client)
):
    """Get a list of available destinations from a specific origin airport."""
    try:
        destinations = await client.get_destinations_from_origin(
            origin_airport_code.upper()
        )
        if not destinations:
            raise HTTPException(
                status_code=404,
                detail=f"No destinations found for origin airport {origin_airport_code}, or origin airport not valid.",
            )
        return destinations
    except requests.exceptions.RequestException as req_ex:
        raise HTTPException(
            status_code=503,
            detail=f"Error connecting to Ryanair services for destinations: {req_ex}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while fetching destinations: {e}",
        )


@app.get(
    "/api/airports/iata-lookup/{city_name}",
    response_model=List[AirportInfo],
    tags=["Airports"],
)
async def get_iata_by_city(
    city_name: str, client: RyanairAPIClient = Depends(get_ryanair_client)
):
    """Get a list of airports and their IATA codes for a specific city."""
    try:
        airports = await client.get_airports()
        if not airports:
            raise HTTPException(
                status_code=404,
                detail="No airports could be fetched from Ryanair or its fallback.",
            )

        matching_airports = [
            airport
            for airport in airports
            if city_name.lower() in airport.city_name.lower()
        ]

        if not matching_airports:
            raise HTTPException(
                status_code=404,
                detail=f"No airports found for city: {city_name}",
            )
        return matching_airports
    except requests.exceptions.RequestException as req_ex:
        raise HTTPException(
            status_code=503, detail=f"Error connecting to Ryanair services: {req_ex}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )


# Flight search endpoint
@app.post("/api/flights/search", response_model=FlightSearchResponse, tags=["Flights"])
async def search_flights_api(
    request_body: FlightSearchRequest = Body(...),
    client: RyanairAPIClient = Depends(get_ryanair_client),
):
    """
    Search for flights based on the provided criteria.
    This endpoint supports direct flights and one-stop connections.
    """
    try:
        analyzer = FlightAnalyzer(client)

        logger.info(
            f"Received flight search request: {request_body.model_dump_json(indent=2)}"
        )
        response = await analyzer.search_flights(request_body)

        if not response.flights:
            logger.info(
                f"No flights found for request: {request_body.model_dump_json()}"
            )

        logger.info(f"Returning {len(response.flights)} flight options.")
        return response
    except ValueError as ve:
        logger.warning(f"Validation error in flight search request: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except requests.exceptions.RequestException as req_ex:
        logger.error(
            f"Ryanair API request failed during flight search: {req_ex}", exc_info=True
        )
        raise HTTPException(
            status_code=503,
            detail=f"Error communicating with Ryanair services: {req_ex}",
        )
    except Exception:
        logger.error(
            "An unexpected error occurred during flight search.", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while searching for flights.",
        )


# Export the app for Vercel
handler = app
