from fastapi import FastAPI
from api import flights, airports, health
from lib.ryanair_client import RyanairAPIClient
from lib.config import Config

app = FastAPI(
    title="Ryanair Flight Scanner API",
    description="API for searching Ryanair flights, including direct and connecting flights.",
    version="0.1.0",
)


# Initialize RyanairAPIClient instance
@app.on_event("startup")
async def startup_event():
    app.state.ryanair_client = RyanairAPIClient(
        currency=Config.DEFAULT_CURRENCY,
    )


@app.on_event("shutdown")
async def shutdown_event():
    # Clean up resources if necessary, e.g., close session
    if hasattr(app.state, "ryanair_client"):
        await app.state.ryanair_client.close_session()


# Include routers
app.include_router(health.router, prefix="/api")
app.include_router(airports.router, prefix="/api")
app.include_router(flights.router, prefix="/api")


@app.get("/", tags=["Root"])
async def read_root():
    """
    Root endpoint, returns a welcome message.
    """
    return {"message": "Welcome to the Ryanair Flight Scanner API"}


# To run the app (e.g., for local development):
# uvicorn main:app --reload

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
