import os
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CACHE_DIR = os.path.join(os.path.dirname(__file__), ".api_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

class FootballAPIClient:
    def __init__(self):
        self.api_key = os.getenv("RAPIDAPI_KEY")
        self.host = os.getenv("RAPIDAPI_HOST", "football-prediction-api.p.rapidapi.com")
        self.base_url = f"https://{self.host}/api/v2"
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host
        }

    def get_fixtures_today(self, federation: str = "UEFA", market: str = "classic", date: str = None):
        """Fetch fixtures and predictions from the Football Prediction API for a specific date."""
        params_date = date if date else datetime.now().strftime("%Y-%m-%d")
        
        # 1. Check local cache
        cache_file = os.path.join(CACHE_DIR, f"{params_date}_{federation}_{market}.json")
        if os.path.exists(cache_file):
            print(f"[CACHE HIT] Returning local data for {params_date} - {federation} - {market} (0 API cost)")
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading cache: {e}")

        # 2. Not in cache, fetch from API
        endpoint = f"{self.base_url}/predictions"
        params = {
            "market": market,
            "iso_date": params_date,
            "federation": federation
        }
        
        try:
            print(f"[API CALL] Fetching data for {params_date} - {federation} - {market}...")
            response = requests.get(endpoint, headers=self.headers, params=params)
            
            fixtures = []
            if response.status_code in [404, 429]:
                print(f"Error {response.status_code} for {market}. Caching empty result to prevent retries.")
            else:
                response.raise_for_status()
                data = response.json()
                fixtures = data.get("data", [])

            # 3. Always save to cache (even if empty) to prevent hammering API for missing/blocked data
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(fixtures, f, ensure_ascii=False, indent=2)
            print(f"[CACHE SAVED] Data saved for {params_date} - {federation} - {market} ({len(fixtures)} fixtures)")
            
            # Sleep 1.5 seconds to avoid rate limits on the next request
            time.sleep(1.5)
            
            return fixtures
        except Exception as e:
            print(f"Error fetching data from API (Market: {market}): {e}")
            # Cache empty on other errors too so we don't spam
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            return []
