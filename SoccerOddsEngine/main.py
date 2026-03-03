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
async def get_parleys(date: str = None, bet_amount: float = 10000, mode: str = 'all'):
    """Trigger the morning scan and return the 10 parleys with reconciliation and global stats."""
    try:
        parleys = orchestrator.generate_parleys(date=date, bet_amount=bet_amount, mode=mode)
        parleys = orchestrator.verify_results(parleys)
        global_stats = orchestrator.calculate_daily_accuracy()
        
        return {
            "parleys": parleys,
            "global_stats": global_stats
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# Mount static files for the frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8010))
    uvicorn.run(app, host="0.0.0.0", port=port)
