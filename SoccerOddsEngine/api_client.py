import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

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
        endpoint = f"{self.base_url}/predictions"
        params_date = date if date else datetime.now().strftime("%Y-%m-%d")
        
        params = {
            "market": market,
            "iso_date": params_date,
            "federation": federation
        }
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            print(f"Error fetching data from API (Market: {market}): {e}")
            return []
