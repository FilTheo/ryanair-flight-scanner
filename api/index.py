from fastapi import FastAPI
from api import flights, airports, health
from lib.ryanair_client import RyanairAPIClient
from lib.config import Config
import logging
import sys

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


# Initialize RyanairAPIClient instance
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up FastAPI application")
    app.state.ryanair_client = RyanairAPIClient(
        currency=Config.DEFAULT_CURRENCY,
    )
    logger.info("RyanairAPIClient initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    # Clean up resources if necessary, e.g., close session
    if hasattr(app.state, "ryanair_client"):
        await app.state.ryanair_client.close_session()


# Include routers
logger.info("Including API routers")
app.include_router(health.router)
app.include_router(airports.router)
app.include_router(flights.router)
logger.info("All routers included successfully")


@app.get("/", tags=["Root"])
async def read_root():
    """
    Root endpoint, returns a welcome message.
    """
    return {"message": "Welcome to the Ryanair Flight Scanner API"}


# Export the app for Vercel
handler = app
