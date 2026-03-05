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
async def get_parleys(date: str = None, bet_amount: float = 10000, mode: str = 'all', federation_filter: str = None, force_refresh: bool = False, show_all: bool = False):
    """Trigger the morning scan and return the 10 parleys with reconciliation and global stats."""
    try:
        parleys = orchestrator.generate_parleys(date=date, bet_amount=bet_amount, mode=mode, federation_filter=federation_filter, force_refresh=force_refresh, show_all=show_all)
        parleys = orchestrator.verify_results(parleys)
        global_stats = orchestrator.calculate_daily_accuracy()
        
        # Get all predictions for the sidebar, verified
        all_preds = orchestrator.market_cache.fixtures if orchestrator.market_cache else []
        
        return {
            "parleys": parleys,
            "all_predictions": all_preds,
            "global_stats": global_stats
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/parleys/saved")
async def get_saved_parleys():
    """Retrieve all parleys saved by the user with updated statuses."""
    try:
        saved_parleys = orchestrator.get_saved_parleys()
        return {"saved_parleys": saved_parleys}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/parleys/save")
async def save_parley(parley: dict):
    """Save a specific parley to the persistent storage."""
    try:
        success = orchestrator.save_parley(parley)
        return {"success": success}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# Mount static files for the frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8010))
    uvicorn.run(app, host="0.0.0.0", port=port)
