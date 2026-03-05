import os
import json
import random
import schedule
import time
from datetime import datetime, timedelta, timezone
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
    start_time: str = ""
    result: str = "PENDING"   # WON, LOST, PENDING
    score: str = ""

class Parley(BaseModel):
    parley_id: int
    selections: List[Selection]
    total_odds: float
    status: str = "PENDING"     # WON, LOST, PENDING
    bet_amount: float = 10000
    estimated_return: float = 0.0
    timestamp: str = ""

class MarketSnapshot(BaseModel):
    timestamp: str
    fixtures: List[Dict]

class SoccerOddsOrchestrator:
    def __init__(self):
        self.api_client = FootballAPIClient()
        self.market_cache = None

    def scan_markets(self, date: str = None, force_refresh: bool = False):
        """Scans multiple top markets for a specific date (YYYY-MM-DD)."""
        bogota_tz = timezone(timedelta(hours=-5))
        now_bogota = datetime.now(timezone.utc).astimezone(bogota_tz)
        print(f"[{now_bogota}] Starting scan for date: {date}...")
        
        markets = ["classic", "btts", "over_under_25"]
        raw_fixtures = []
        scan_date_str = date if date else now_bogota.strftime("%Y-%m-%d")
        
        # Determine the next day in Bogota to catch UTC rollovers (Matches at 7PM-11PM Bogota are next day UTC)
        scan_datetime = datetime.strptime(scan_date_str, "%Y-%m-%d")
        tomorrow_date_str = (scan_datetime + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Fetch from both API dates to ensure we have every possible match for the Bogota 24h window
        for d_str in [scan_date_str, tomorrow_date_str]:
            for market in markets:
                fixtures = self.api_client.get_fixtures_today(federation="ALL", market=market, date=d_str, force_refresh=force_refresh)
                if fixtures:
                    for f in fixtures:
                        f["api_market"] = market
                        raw_fixtures.append(f)
        
        # Re-bucket and filter
        all_fixtures = []
        is_today = scan_date_str == now_bogota.strftime("%Y-%m-%d")
        seen_keys = set()

        for f in raw_fixtures:
            key = (f.get("id"), f.get("api_market"))
            if key in seen_keys:
                continue
            seen_keys.add(key)

            try:
                start_str = f.get("start_date", "")
                if not start_str:
                    continue
                
                # API yields UTC time. Convert to Bogota for comparison.
                dt_utc = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                dt_bogota = dt_utc.astimezone(bogota_tz)
                
                # Rule 2: Validation of matching the selected day
                if dt_bogota.strftime("%Y-%m-%d") != scan_date_str:
                    continue
                
                # Pre-calculate prediction_odds for the UI
                pred_key = f.get("prediction")
                odds_dict = f.get("odds", {})
                f["prediction_odds"] = float(odds_dict.get(pred_key, 1.0)) if pred_key in odds_dict else 1.0
                
                all_fixtures.append(f)
            except Exception as e:
                print(f"Error processing fixture {f.get('id')}: {e}")
                continue
        
        self.market_cache = MarketSnapshot(
            timestamp=datetime.now(timezone.utc).astimezone(bogota_tz).isoformat(),
            fixtures=all_fixtures
        )
        print(f"[{datetime.now()}] Scan complete. {len(all_fixtures)} entries found for {scan_date_str}.")

    def filter_value_bets(self):
        """Simple model to simulate value bet filtering."""
        return self.market_cache.fixtures

    def generate_parleys(self, date: str = None, bet_amount: float = 10000, mode: str = 'all', federation_filter: str = None, force_refresh: bool = False, show_all: bool = False) -> List[Parley]:
        """Generates 10 optimized parleys for a specific date."""
        # Always re-scan if a specific date is requested, cache is empty, or force_refresh is True
        # Note: We do NOT re-scan purely because of show_all anymore, we use the in-memory cache.
        if not self.market_cache or date or force_refresh:
            self.scan_markets(date=date, force_refresh=force_refresh)

        fixtures = self.filter_value_bets()
        if not fixtures:
            print("No fixtures found to generate parleys.")
            return []

        # In-memory filtering by time if NOT show_all (upcoming only)
        bogota_tz = timezone(timedelta(hours=-5))
        now_bogota = datetime.now(timezone.utc).astimezone(bogota_tz)
        is_today = (date == now_bogota.strftime("%Y-%m-%d")) or (date is None)

        if is_today and not show_all:
            filtered = []
            for f in fixtures:
                try:
                    dt_utc = datetime.strptime(f["start_date"], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                    dt_bogota = dt_utc.astimezone(bogota_tz)
                    if dt_bogota >= now_bogota:
                        filtered.append(f)
                except:
                    continue
            fixtures = filtered
            
        if federation_filter:
            fixtures = [f for f in fixtures if str(f.get("federation", "")).lower() == federation_filter.lower()]
            if not fixtures:
                print(f"No fixtures found for federation: {federation_filter}")
                return []
            
        if mode == 'premium':
            top_leagues = [
                "premier league", "primera division", "serie a", "bundesliga", "ligue 1", 
                "uefa champions league", "uefa europa league", "euro championship", 
                "copa america", "world cup", "eredivisie", "primeira liga", "championship",
                "brasileiro serie a", "liga profesional argentina", "mls", "primera a", "super lig"
            ]
            fixtures = [f for f in fixtures if str(f.get("competition_name", "")).lower() in top_leagues]
            if not fixtures:
                print("No premium fixtures found.")
                return []
                
        if mode == 'safe':
            # "Safe Strategy" takes matches from ALL leagues but applies strict safety filters
            safe_fixtures = []
            for f in fixtures:
                market = f.get("api_market", "classic")
                prediction = f.get("prediction", "1")
                odds_dict = f.get("odds", {})
                
                # Apply Double Chance
                if market == "classic" and prediction in ["1", "2"]:
                    new_pred = "1X" if prediction == "1" else "X2"
                    if new_pred in odds_dict:
                        prediction = new_pred
                        f["prediction"] = prediction # Update inline for downstream
                        
                # Filter by Odds Range (Strict safety: 1.15 to 1.60 instead of 1.85)
                odds = float(odds_dict.get(prediction, 1.0))
                if 1.15 <= odds <= 1.60:
                    safe_fixtures.append(f)
                    
            fixtures = safe_fixtures
            if not fixtures:
                print("No safe fixtures matching criteria found.")
                return []
            
        parleys = []
        seen_signatures = set()
        
        attempts = 0
        while len(parleys) < 10 and attempts < 150:
            attempts += 1
            
            if mode == 'safe':
                min_sel = 2
                max_sel = min(4, len(fixtures))
            else:
                min_sel = 3 if len(fixtures) < 5 else 5
                max_sel = min(10, len(fixtures))
                
            if min_sel > max_sel:
                min_sel = max_sel
                
            if max_sel == 0:
                break
                
            num_selections = random.randint(min_sel, max_sel)
            selected_fixtures = random.sample(fixtures, num_selections)
            
            signature = tuple(sorted(f["id"] for f in selected_fixtures))
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            
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
                
                match_time = ""
                try:
                    start_date_str = fixture.get("start_date", "")
                    if start_date_str:
                        dt_utc = datetime.strptime(start_date_str, "%Y-%m-%dT%H:%M:%S")
                        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                        dt_bogota = dt_utc.astimezone(timezone(timedelta(hours=-5)))
                        match_time = dt_bogota.strftime("%H:%M")
                except Exception as e:
                    pass
                
                sel = Selection(
                    match_id=fixture["id"],
                    league=f"{country} - {competition}",
                    teams=f"{fixture['home_team']} vs {fixture['away_team']}",
                    market=ui_market,
                    selection=prediction,
                    odds=float(odds),
                    start_time=match_time
                )
                parley_selections.append(sel)
                final_odds *= float(odds)

            parleys.append(Parley(
                parley_id=len(parleys) + 1,
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
        """Calculates global and federation-specific prediction accuracy."""
        stats = {
            "total_matches": 0,
            "won": 0,
            "lost": 0,
            "pending": 0,
            "accuracy_percentage": 0.0,
            "federations": {}
        }
        
        if not self.market_cache or not self.market_cache.fixtures:
            return stats
            
        for fixture in self.market_cache.fixtures:
            status = fixture.get("status", "").lower()
            fed = fixture.get("federation", "Unknown")
            
            # Global Tally
            stats["total_matches"] += 1
            if status == "won":
                stats["won"] += 1
            elif status == "lost":
                stats["lost"] += 1
            else:
                stats["pending"] += 1
                
            # Federation Tally
            if fed not in stats["federations"]:
                stats["federations"][fed] = {"won": 0, "lost": 0, "pending": 0, "total": 0}
                
            stats["federations"][fed]["total"] += 1
            if status == "won":
                stats["federations"][fed]["won"] += 1
            elif status == "lost":
                stats["federations"][fed]["lost"] += 1
            else:
                stats["federations"][fed]["pending"] += 1
                
        # Calculate Global Percentage
        resolved_matches = stats["won"] + stats["lost"]
        if resolved_matches > 0:
            stats["accuracy_percentage"] = round((stats["won"] / resolved_matches) * 100, 2)
            
        # Calculate Federation Percentages and format as list
        fed_list = []
        for fed, counts in stats["federations"].items():
            fed_resolved = counts["won"] + counts["lost"]
            accuracy = 0.0
            if fed_resolved > 0:
                accuracy = round((counts["won"] / fed_resolved) * 100, 2)
            fed_list.append({
                "name": fed,
                "accuracy": accuracy,
                "won": counts["won"],
                "lost": counts["lost"],
                "pending": counts["pending"],
                "total": counts["total"]
            })
            
        # Optional: Sort by accuracy descending or total volume
        fed_list.sort(key=lambda x: x["total"], reverse=True)
        stats["federations"] = fed_list
            
        return stats

    def run_morning_workflow(self):
        """Executes the full automated workflow."""
        self.scan_markets()
        parleys = self.generate_parleys()
        
        # Output strictly in JSON as required by the prompt
        output = [p.dict() for p in parleys]
        print(json.dumps(output, indent=2))
        return output

    def save_parley(self, parley_data: dict):
        """Saves a parley to saved_parleys.json."""
        storage_path = os.path.join(os.path.dirname(__file__), "saved_parleys.json")
        saved = []
        if os.path.exists(storage_path):
            try:
                with open(storage_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
            except:
                saved = []
        
        # Add to beginning of list
        bogota_tz = timezone(timedelta(hours=-5))
        parley_data["timestamp"] = datetime.now(bogota_tz).strftime("%Y-%m-%d %H:%M")
        saved.insert(0, parley_data)
        
        with open(storage_path, "w", encoding="utf-8") as f:
            json.dump(saved, f, indent=2, ensure_ascii=False)
        return True

    def get_saved_parleys(self) -> List[Parley]:
        """Retrieves and verifies all saved parleys."""
        storage_path = os.path.join(os.path.dirname(__file__), "saved_parleys.json")
        if not os.path.exists(storage_path):
            return []
            
        try:
            with open(storage_path, "r", encoding="utf-8") as f:
                saved_dicts = json.load(f)
        except:
            return []
            
        # Convert to Pydantic models
        parleys = []
        for d in saved_dicts:
            try:
                parleys.append(Parley(**d))
            except Exception as e:
                print(f"Error parsing saved parley: {e}")
        
        # Trigger verification against CURRENT cache (matches may have finished)
        return self.verify_results(parleys)

def main():
    orchestrator = SoccerOddsOrchestrator()
    orchestrator.run_morning_workflow()

if __name__ == "__main__":
    main()
