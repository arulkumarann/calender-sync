import os
import requests
import json
from datetime import datetime, timedelta

def get_next_5_day_orders():
    """Fetches day orders for the next 5 days from the API."""
    API_URL = os.getenv("API_URL")

    response = requests.get(API_URL)

    if response.status_code == 200:
        data = response.json()
        today_date = datetime.now().day  
        month_data = data["calendar"][0]["days"]  

        next_5_days = {}
        count = 0
        
        for day in month_data:
            if count >= 5:
                break  

            if int(day["date"]) >= today_date:  
                if day["dayOrder"] != "-":
                    next_5_days[day["date"]] = day["dayOrder"]
                    count += 1

        return next_5_days

    return None  
 
print(get_next_5_day_orders())