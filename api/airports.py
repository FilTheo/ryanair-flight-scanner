from fastapi import APIRouter, HTTPException, Depends, Request as FastAPIRequest
from typing import List
import requests.exceptions
from lib.models import AirportInfo
from lib.ryanair_client import RyanairAPIClient

# from lib.config import Config # No longer needed directly here

router = APIRouter()


# Dependency to get RyanairAPIClient from app.state
def get_ryanair_client(
    fast_api_request: FastAPIRequest,
) -> RyanairAPIClient:  # Use FastAPIRequest
    return fast_api_request.app.state.ryanair_client


@router.get("/airports", response_model=List[AirportInfo], tags=["Airports"])
async def get_all_airports(client: RyanairAPIClient = Depends(get_ryanair_client)):
    """
    Get a list of all Ryanair airports.
    """
    try:
        airports = await client.get_airports()
        if not airports:  # Added check for empty list from client
            # This could mean primary and fallback failed, or simply no airports (unlikely)
            # Returning 204 No Content might be more appropriate if it's a valid empty result
            # For now, sticking to 500 if client returns empty, implying an issue.
            # Or, we can return 404 if client explicitly signals no data found vs error.
            # Current client returns empty list on errors or no data, so 500 might be too strong.
            # Let client raise specific exceptions or return None to differentiate.
            # Assuming client returning empty list means "no data could be fetched/found"
            raise HTTPException(
                status_code=404,
                detail="No airports could be fetched from Ryanair or its fallback.",
            )
        return airports
    except (
        requests.exceptions.RequestException
    ) as req_ex:  # Catch specific request errors
        # Log req_ex here
        raise HTTPException(
            status_code=503, detail=f"Error connecting to Ryanair services: {req_ex}"
        )
    except Exception as e:
        # Log e here
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )


@router.get(
    "/airports/{origin_airport_code}/destinations",
    response_model=List[AirportInfo],
    tags=["Airports"],
)
async def get_destinations(
    origin_airport_code: str, client: RyanairAPIClient = Depends(get_ryanair_client)
):
    """
    Get a list of available destinations from a specific origin airport.
    """
    try:
        destinations = await client.get_destinations_from_origin(
            origin_airport_code.upper()
        )
        if not destinations:
            # This handles both "origin not found" and "origin has no destinations"
            raise HTTPException(
                status_code=404,
                detail=f"No destinations found for origin airport {origin_airport_code}, or origin airport not valid.",
            )
        return destinations
    except requests.exceptions.RequestException as req_ex:
        # Log req_ex here
        raise HTTPException(
            status_code=503,
            detail=f"Error connecting to Ryanair services for destinations: {req_ex}",
        )
    except HTTPException:  # Re-raise HTTPExceptions (like the 404 above) directly
        raise
    except Exception as e:
        # Log e here
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while fetching destinations: {e}",
        )


@router.get(
    "/airports/iata-lookup/{city_name}",
    response_model=List[AirportInfo],
    tags=["Airports"],
)
async def get_iata_by_city(
    city_name: str, client: RyanairAPIClient = Depends(get_ryanair_client)
):
    """
    Get a list of airports and their IATA codes for a specific city.
    """
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
    except HTTPException:  # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )
