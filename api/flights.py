from fastapi import APIRouter, HTTPException, Body, Depends, Request as FastAPIRequest
from lib.models import FlightSearchRequest, FlightSearchResponse
from lib.ryanair_client import RyanairAPIClient
from lib.flight_analyzer import FlightAnalyzer
import requests.exceptions
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def get_ryanair_client(fast_api_request: FastAPIRequest) -> RyanairAPIClient:
    return fast_api_request.app.state.ryanair_client


@router.post("/flights/search", response_model=FlightSearchResponse, tags=["Flights"])
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
