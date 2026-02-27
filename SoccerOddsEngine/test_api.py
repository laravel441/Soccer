from api_client import FootballAPIClient
import json
from datetime import datetime

client = FootballAPIClient()
date = "2024-03-01" # A random date
try:
    fixtures = client.get_fixtures_today(federation="UEFA", market="classic", date=date)
    print(f"Total fixtures for {date}: {len(fixtures)}")
    if fixtures:
        print("Sample fixture:")
        print(json.dumps(fixtures[0], indent=2))
        
        # Check start dates
        start_dates = [f.get("start_date") for f in fixtures[:5]]
        print(f"Sample start dates: {start_dates}")
except Exception as e:
    print(f"Error: {e}")
