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
    result: str = "PENDING"   # WON, LOST, PENDING
    score: str = ""

class Parley(BaseModel):
    parley_id: int
    selections: List[Selection]
    total_odds: float
    status: str = "PENDING"     # WON, LOST, PENDING
    bet_amount: float = 10000
    estimated_return: float = 0.0

class MarketSnapshot(BaseModel):
    timestamp: str
    fixtures: List[Dict]

class SoccerOddsOrchestrator:
    def __init__(self):
        self.api_client = FootballAPIClient()
        self.market_cache = None

    def scan_markets(self, date: str = None):
        """Scans multiple top markets for a specific date (YYYY-MM-DD)."""
        print(f"[{datetime.now()}] Starting scan for date: {date}...")
        
        markets = ["classic", "btts", "over_under_25"]
        all_fixtures = []
        scan_date = date if date else datetime.now().strftime("%Y-%m-%d")
        
        for market in markets:
            fixtures = self.api_client.get_fixtures_today(federation="UEFA", market=market, date=scan_date)
            # Filter strictly by the scan date
            filtered_fixtures = [
                f for f in fixtures 
                if f.get("start_date", "").startswith(scan_date)
            ]
            
            # Add market tag to each fixture for identification
            for f in filtered_fixtures:
                f["api_market"] = market
            all_fixtures.extend(filtered_fixtures)
        
        self.market_cache = MarketSnapshot(
            timestamp=datetime.now().isoformat(),
            fixtures=all_fixtures
        )
        print(f"[{datetime.now()}] Scan complete. {len(all_fixtures)} entries found for {scan_date}.")

    def filter_value_bets(self):
        """Simple model to simulate value bet filtering."""
        return self.market_cache.fixtures

    def generate_parleys(self, date: str = None, bet_amount: float = 10000, premium_only: bool = False) -> List[Parley]:
        """Generates 10 optimized parleys for a specific date."""
        # Always re-scan if a specific date is requested or cache is empty
        if not self.market_cache or date:
            self.scan_markets(date=date)

        fixtures = self.filter_value_bets()
        if not fixtures:
            print("No fixtures found to generate parleys.")
            return []
            
        if premium_only:
            top_leagues = [
                "premier league", "primera division", "serie a", "bundesliga", "ligue 1", 
                "uefa champions league", "uefa europa league", "euro championship", 
                "copa america", "world cup"
            ]
            fixtures = [f for f in fixtures if str(f.get("competition_name", "")).lower() in top_leagues]
            if not fixtures:
                print("No premium fixtures found.")
                return []
            
        parleys = []

        for i in range(1, 11):
            num_selections = random.randint(5, 10)
            selected_fixtures = random.sample(fixtures, min(num_selections, len(fixtures)))
            
            parley_selections = []
            final_odds = 1.0
            
            for fixture in selected_fixtures:
                market = fixture.get("api_market", "classic")
                prediction = fixture.get("prediction", "1")
                
                ui_market = market
                if market == "over_under_25":
                    ui_market = "+2.5 GOLES"
                elif market == "btts":
                    ui_market = "AMBOS MARCAN"
                elif market == "classic":
                    ui_market = "1X2"

                odds_dict = fixture.get("odds", {})
                if prediction not in odds_dict:
                    prediction = list(odds_dict.keys())[0] if odds_dict else "1"
                
                odds = odds_dict.get(prediction, 1.0)
                
                country = fixture.get('competition_cluster', 'Intl')
                competition = fixture.get('competition_name', '')
                
                sel = Selection(
                    match_id=fixture["id"],
                    league=f"{country} - {competition}",
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
                total_odds=round(final_odds, 2),
                bet_amount=bet_amount,
                estimated_return=round(bet_amount * final_odds, 2)
            ))
        
        return parleys

    def verify_results(self, parleys: List[Parley]) -> List[Parley]:
        """Verifies parley results against cached fixture data.
        If ANY selection is lost, the parley is immediately LOST.
        """
        if not self.market_cache or not self.market_cache.fixtures:
            return parleys

        fixture_map = {f["id"]: f for f in self.market_cache.fixtures}

        for parley in parleys:
            parley_won = True
            all_resolved = True

            for sel in parley.selections:
                fixture = fixture_map.get(sel.match_id)
                if not fixture:
                    all_resolved = False
                    continue

                api_status = fixture.get("status", "").lower()
                raw_result = fixture.get("result", "")
                if raw_result and " - " in raw_result:
                    sel.score = raw_result.replace(" - ", "-")
                else:
                    sel.score = raw_result

                if api_status in ["won", "lost"]:
                    is_win = (api_status == "won")
                    sel.result = "WON" if is_win else "LOST"
                    if not is_win:
                        parley_won = False
                elif api_status == "pending":
                    all_resolved = False
                    sel.result = "PENDING"
                else:
                    all_resolved = False
                    sel.result = "PENDING"

            # Key logic: if ANY selection lost, parley is LOST immediately
            if not parley_won:
                parley.status = "LOST"
                parley.estimated_return = 0.0
            elif not all_resolved:
                parley.status = "PENDING"
            else:
                parley.status = "WON"

        return parleys

    def calculate_daily_accuracy(self) -> dict:
        """Calculates global prediction accuracy for the day based on downloaded fixtures."""
        stats = {
            "total_matches": 0,
            "won": 0,
            "lost": 0,
            "pending": 0,
            "accuracy_percentage": 0.0
        }
        
        if not self.market_cache or not self.market_cache.fixtures:
            return stats
            
        for fixture in self.market_cache.fixtures:
            status = fixture.get("status", "").lower()
            prediction = fixture.get("prediction", "")
            
            stats["total_matches"] += 1
            
            if status == "won":
                stats["won"] += 1
            elif status == "lost":
                stats["lost"] += 1
            else:
                stats["pending"] += 1
                
        resolved_matches = stats["won"] + stats["lost"]
        if resolved_matches > 0:
            stats["accuracy_percentage"] = round((stats["won"] / resolved_matches) * 100, 2)
            
        return stats

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
