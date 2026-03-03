from api_client import FootballAPIClient
import os
from dotenv import load_dotenv

load_dotenv()

client = FootballAPIClient()
print(f"Testing with key: {os.getenv('RAPIDAPI_KEY')[:10]}...")
data = client.get_fixtures_today(market='classic', date='2026-03-03')
print(f"Data received: {len(data)} fixtures.")
if data:
    print("Sample fixture:", data[0].get('home_team'), "vs", data[0].get('away_team'))
else:
    print("No data received or API error.")
