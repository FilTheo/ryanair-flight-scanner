from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from api import flights, airports, health
from lib.ryanair_client import RyanairAPIClient
from lib.config import Config

app = FastAPI(
    title="Ryanair Flight Scanner API",
    description="API for searching Ryanair flights, including direct and connecting flights.",
    version="0.1.0",
)

# Initialize RyanairAPIClient instance globally for Vercel
ryanair_client = RyanairAPIClient(
    currency=Config.DEFAULT_CURRENCY,
)
app.state.ryanair_client = ryanair_client

# Include routers
app.include_router(health.router, prefix="/api")
app.include_router(airports.router, prefix="/api")
app.include_router(flights.router, prefix="/api")

# Mount static files if in production (static folder exists)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", tags=["Root"])
async def read_root():
    """
    Root endpoint, serves the main page or returns a welcome message.
    """
    # Try to serve index.html if it exists, otherwise return JSON
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": "Welcome to the Ryanair Flight Scanner API"}


# To run the app (e.g., for local development):
# uvicorn main:app --reload

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
