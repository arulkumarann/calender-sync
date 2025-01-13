import os
import json
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from fetch_dayorder import get_next_5_day_orders

SUBJECT_COLORS = {
    "PQT": "1",    # Lavender
    "AI": "9",     # Blueberry
    "UHV": "6",    # Tangerine
    "DAA": "3",    # Tomato
    "DIP": "2",    # Sage
    "DBMS": "7",   # Peacock
    "SE": "10",    # Basil
}

def get_calendar_service():
    """Sets up and returns the Google Calendar service."""
    google_credentials = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    creds = service_account.Credentials.from_service_account_info(google_credentials, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds)

def get_calendar_id():
    """Retrieves calendar ID from environment variables."""
    calendar_id = os.getenv("CALENDAR_ID")
    if not calendar_id:
        raise ValueError("CALENDAR_ID environment variable is not set")
    return calendar_id

def format_datetime(date, time_str):
    """
    Formats date and time string into proper ISO format.
    Returns datetime string in format: YYYY-MM-DDTHH:mm:ss+05:30
    """
    if len(time_str) == 4:  # If time is like "9:30"
        time_str = f"0{time_str}"
    datetime_str = f"{date}T{time_str}:00+05:30"
    return datetime_str

def get_events_for_specific_date(service, date_str):
    """Get all events for a specific date."""
    calendar_id = get_calendar_id()

    day_start = format_datetime(date_str, "00:00")
    day_end = format_datetime(date_str, "23:59")
    
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=day_start,
        timeMax=day_end,
        timeZone="Asia/Kolkata",
        singleEvents=True
    ).execute()
    
    return events_result.get("items", [])

def delete_all_events_for_date(service, date_str):
    """Delete all events for a specific date."""
    calendar_id = get_calendar_id()

    print(f"Checking for events to delete on {date_str}")
    events = get_events_for_specific_date(service, date_str)
    deleted_count = 0
    
    for event in events:
        try:
            service.events().delete(
                calendarId=calendar_id,
                eventId=event["id"]
            ).execute()
            deleted_count += 1
            print(f"Deleted event: {event.get('summary', 'Unknown event')} on {date_str}")
        except Exception as e:
            print(f"Error deleting event: {str(e)}")
    
    if deleted_count > 0:
        print(f"Deleted {deleted_count} events for {date_str}")
    else:
        print(f"No events found to delete for {date_str}")

def create_event(service, class_info, date_str, day_order):
    calendar_id = get_calendar_id()
    """Create a new calendar event."""
    start_datetime = format_datetime(date_str, class_info['start_time'])
    end_datetime = format_datetime(date_str, class_info['end_time'])
    #base_subject = class_info["subject"].split(" (")[0]
    
    event = {
        "summary": class_info["subject"],
        "description": f"Day Order {day_order}",
        "start": {
            "dateTime": start_datetime,
            "timeZone": "Asia/Kolkata"
        },
        "end": {
            "dateTime": end_datetime,
            "timeZone": "Asia/Kolkata"
        },
        "colorId": SUBJECT_COLORS.get(base_subject, "8")
    }
    
    try:
        response = service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"Added event: {class_info['subject']} on {date_str}")
        return True
    except Exception as e:
        print(f"Error adding event: {str(e)}")
        return False

def update_calendar():
    """Update the calendar with the latest schedule and handle holidays."""
    
    # Get new schedule
    day_orders = get_next_5_day_orders()
    if not day_orders:
        print("No valid day orders found. Skipping calendar update.")
        return
    
    try:
        service = get_calendar_service()
        today = datetime.now().date()

        # Convert day_orders keys to integers and find min/max
        date_numbers = [int(d) for d in day_orders.keys()]
        min_date = min(date_numbers)
        max_date = max(date_numbers)
        
        # Generate all dates in the range
        all_dates_in_range = set()
        current_date = min_date
        while current_date <= max_date:
            all_dates_in_range.add(str(current_date))
            current_date += 1
        
        # Find dates that are in the range but not in day_orders (holidays)
        scheduled_dates = set(day_orders.keys())
        holiday_dates = all_dates_in_range - scheduled_dates
        
        print("\nProcessing schedule updates...")
        print(f"Date range: {min_date} to {max_date}")
        print(f"Found {len(holiday_dates)} holidays in the range")
        
        # First, handle holidays (missing dates)
        for date_num in holiday_dates:
            event_date = today + timedelta(days=int(date_num) - today.day)
            formatted_date = event_date.strftime("%Y-%m-%d")
            print(f"\nProcessing holiday on {formatted_date}")
            delete_all_events_for_date(service, formatted_date)
        
        # Then handle regular days
        class_schedule = load_class_schedule()
        if not class_schedule:
            return
            
        for date_str, day_order in day_orders.items():
            event_date = today + timedelta(days=int(date_str) - today.day)
            formatted_date = event_date.strftime("%Y-%m-%d")
            
            print(f"\nProcessing regular day {formatted_date} (Day Order: {day_order})")
            
            # First delete any existing events
            delete_all_events_for_date(service, formatted_date)
            
            # Then add new events if it's a regular day
            if str(day_order) in class_schedule:
                for class_info in class_schedule[str(day_order)]:
                    create_event(service, class_info, formatted_date, day_order)
            else:
                print(f"No schedule found for Day Order {day_order}")

    except Exception as e:
        print(f"Error updating calendar: {str(e)}")

def load_class_schedule():
    """Loads the class schedule from JSON file."""
    try:
        with open(r"config/class_schedule.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print("Error: class_schedule.json not found in config directory")
        return None
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in class_schedule.json")
        return None

if __name__ == "__main__":
    update_calendar()