import sys
import os
import time
import random

# Add project root to path
sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.models.stock import Stock

def simulate_market():
    db = SessionLocal()
    print("🚀 Market Simulator Started... (Press Ctrl+C to stop)")
    
    try:
        while True:
            stocks = db.query(Stock).all()
            for stock in stocks:
                # Randomly change price between -2% and +2%
                change_percent = random.uniform(0.98, 1.02)
                stock.last_price = round(stock.last_price * change_percent, 2)
                
            db.commit()
            print(f"Updated prices for {len(stocks)} stocks.")
            time.sleep(5)  # Wait 5 seconds before next update
            
    except KeyboardInterrupt:
        print("Stopping simulator...")
    finally:
        db.close()

if __name__ == "__main__":
    simulate_market()