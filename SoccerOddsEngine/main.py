from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from orchestrator import SoccerOddsOrchestrator
import uvicorn
import os

app = FastAPI(title="Soccer Odds Engine API")

# Initialize orchestrator
orchestrator = SoccerOddsOrchestrator()

@app.get("/api/parleys")
async def get_parleys():
    """Trigger the morning scan and return the 10 parleys."""
    try:
        # For simplicity, we trigger a scan every time the user requests parleys
        # In production, this would be cached or scheduled
        parleys = orchestrator.generate_parleys()
        return parleys
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# Mount static files for the frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8010))
    uvicorn.run(app, host="0.0.0.0", port=port)
