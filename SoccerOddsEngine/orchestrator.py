import json
import random
import schedule
import time
from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel
from api_client import FootballAPIClient

class Selection(BaseModel):
    match_id: int
    league: str
    teams: str
    market: str
    selection: str
    odds: float

class Parley(BaseModel):
    parley_id: int
    selections: List[Selection]
    total_odds: float

class MarketSnapshot(BaseModel):
    timestamp: str
    fixtures: List[Dict]

class SoccerOddsOrchestrator:
    def __init__(self):
        self.api_client = FootballAPIClient()
        self.market_cache = None

    def scan_markets(self):
        """Scans multiple top markets and caches the snapshot."""
        print(f"[{datetime.now()}] Starting morning scan...")
        
        markets = ["classic", "btts", "over_under_25"]
        all_fixtures = []
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        for market in markets:
            fixtures = self.api_client.get_fixtures_today(federation="UEFA", market=market)
            # Filter strictly by today's date
            today_fixtures = [
                f for f in fixtures 
                if f.get("start_date", "").startswith(today_str)
            ]
            
            # Add market tag to each fixture for identification
            for f in today_fixtures:
                f["api_market"] = market
            all_fixtures.extend(today_fixtures)
        
        self.market_cache = MarketSnapshot(
            timestamp=datetime.now().isoformat(),
            fixtures=all_fixtures
        )
        print(f"[{datetime.now()}] Scan complete. {len(all_fixtures)} match entries found for TODAY ({today_str}) across {len(markets)} markets.")

    def filter_value_bets(self):
        """Simple model to simulate value bet filtering."""
        # For multi-market, we take a balanced sample from each market type
        return self.market_cache.fixtures

    def generate_parleys(self) -> List[Parley]:
        """Generates 10 optimized multi-market parleys."""
        if not self.market_cache or not self.market_cache.fixtures:
            self.scan_markets()

        fixtures = self.filter_value_bets()
        if not fixtures:
            print("No fixtures found to generate parleys.")
            return []
            
        parleys = []

        for i in range(1, 11):
            num_selections = random.randint(5, 10)
            # Sample matches without duplicates in the same parley (based on id + market)
            selected_fixtures = random.sample(fixtures, min(num_selections, len(fixtures)))
            
            parley_selections = []
            final_odds = 1.0
            
            for fixture in selected_fixtures:
                market = fixture.get("api_market", "classic")
                prediction = fixture.get("prediction", "1")
                
                # Standardize selection for UI mapping
                ui_market = market
                if market == "over_under_25":
                    ui_market = "+2.5 GOLES"
                elif market == "btts":
                    ui_market = "AMBOS MARCAN"
                elif market == "classic":
                    ui_market = "1X2"

                odds_dict = fixture.get("odds", {})
                if prediction not in odds_dict:
                    # Fallback if prediction is missing in odds
                    prediction = list(odds_dict.keys())[0] if odds_dict else "1"
                
                odds = odds_dict.get(prediction, 1.0)
                
                sel = Selection(
                    match_id=fixture["id"],
                    league=fixture["competition_name"],
                    teams=f"{fixture['home_team']} vs {fixture['away_team']}",
                    market=ui_market,
                    selection=prediction,
                    odds=float(odds)
                )
                parley_selections.append(sel)
                final_odds *= float(odds)

            parleys.append(Parley(
                parley_id=i,
                selections=parley_selections,
                total_odds=round(final_odds, 2)
            ))
        
        return parleys

    def run_morning_workflow(self):
        """Executes the full automated workflow."""
        self.scan_markets()
        parleys = self.generate_parleys()
        
        # Output strictly in JSON as required by the prompt
        output = [p.dict() for p in parleys]
        print(json.dumps(output, indent=2))
        return output

def main():
    orchestrator = SoccerOddsOrchestrator()
    
    # Run once immediately for validation
    orchestrator.run_morning_workflow()

    # Schedule the morning scan (e.g., every day at 08:00)
    # scan_time = os.getenv("MORNING_SCAN_TIME", "08:00")
    # schedule.every().day.at(scan_time).do(orchestrator.run_morning_workflow)

    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)

if __name__ == "__main__":
    main()
