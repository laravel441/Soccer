import sys
import os
sys.path.append(os.getcwd())
from orchestrator import SoccerOddsOrchestrator
import json

def test_save():
    orchestrator = SoccerOddsOrchestrator()
    test_parley = {
        "parley_id": "TEST-001",
        "total_odds": 5.5,
        "bet_amount": 10000,
        "estimated_return": 55000,
        "status": "PENDING",
        "selections": []
    }
    
    print("Testing save_parley...")
    orchestrator.save_parley(test_parley)
    
    storage_path = os.path.join(os.getcwd(), "saved_parleys.json")
    if os.path.exists(storage_path):
        with open(storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"Saved parleys found: {len(data)}")
            print(f"First parley ID: {data[0]['parley_id']}")
    else:
        print("Error: saved_parleys.json not found!")

if __name__ == "__main__":
    test_save()
