import schedule
import time
from datetime import datetime
# import your alert function here
# from alert_module import send_daily_alert

def job():
    print(f"Running daily alert at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    # call your main alert script function
    # send_daily_alert()

# Schedule the job at 11:00 PM every day
schedule.every().day.at("23:00").do(job)

print("Scheduler started. Waiting for 11 PM...")

while True:
    schedule.run_pending()
    time.sleep(30)  # check every 30 seconds