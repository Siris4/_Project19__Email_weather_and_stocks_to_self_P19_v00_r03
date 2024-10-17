import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
import pytz
import os  # To access environment variables

# Your wakeup time (e.g., 9:00 AM)
WAKEUP_TIME = "09:00"
TIMEZONE = "America/New_York"  # Adjust this to your timezone

# Fetch email and API key from environment variables
SENDER_EMAIL = os.getenv('EMAIL_USER')  # Your email from environment variable
SENDER_PASSWORD = os.getenv('EMAIL_PASS')  # Your email password (app password) from environment variable
RECEIVER_EMAIL = SENDER_EMAIL  # Email where you want to receive the daily update (same email in this case)

# Weather API (OpenWeatherMap)
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')  # Your OpenWeatherMap API key from environment variable
LOCATION = 'Monterrey'

# Alpha Vantage API Key (replace with your own key)
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')

# Stock symbols for live financial data (use 'SPX' for the S&P 500 in Alpha Vantage)
STOCKS = ['AAPL', 'NVDA', 'PWR', 'TSLA', 'CEG']  # S&P 500 symbol is 'SPX'


# Function to fetch current weather in Fahrenheit and check for rain
def get_weather():
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={LOCATION}&appid={WEATHER_API_KEY}&units=imperial"
    response = requests.get(url)
    data = response.json()

    if data["cod"] != "200":
        return "Weather information unavailable."

    # Get current weather
    weather_desc = data['list'][0]['weather'][0]['description'].capitalize()
    temp = data['list'][0]['main']['temp']

    # Initialize variables to track the highest rain point
    max_rain = 0
    max_rain_time = None

    # Check for rain in the next 24 hours
    for forecast in data['list'][:8]:  # Next 24 hours = 8 * 3-hour intervals
        if 'rain' in forecast:
            rain_amount = forecast['rain'].get('3h', 0)
            if rain_amount > max_rain:
                max_rain = rain_amount
                max_rain_time = forecast['dt_txt']

    # Determine rain status
    if max_rain_time:
        rain_status = f"It will rain in the next 24 hours. The highest rain point will be at {max_rain_time}, with {max_rain}mm of rain."
    else:
        rain_status = "No rain expected in the next 24 hours."

    return f"Current weather in {LOCATION}: {weather_desc}, {temp}°F. {rain_status}"


# Function to fetch current stock prices using Alpha Vantage API
def get_stock_data():
    stock_info = ""
    for stock in STOCKS:
        try:
            url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={stock}&apikey={ALPHA_VANTAGE_API_KEY}'
            response = requests.get(url)
            data = response.json()

            if 'Global Quote' in data and '05. price' in data['Global Quote']:
                current_price = data['Global Quote']['05. price']
                stock_info += f"{stock}: ${float(current_price):.2f}\n"
            else:
                stock_info += f"{stock}: No current price data available\n"
        except Exception as e:
            stock_info += f"{stock}: Failed to fetch data ({str(e)})\n"

    return stock_info


# Function to send email
def send_email(weather_info, stock_info):
    msg = MIMEMultipart("alternative")
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"Morning Update - {datetime.now().strftime('%Y-%m-%d')}"

    # Create the email content
    text = f"""
    Good Morning!

    Here is your daily update for {datetime.now().strftime('%Y-%m-%d')}:

    {weather_info}

    Live Stock Prices:
    {stock_info}

    Have a great day!
    """

    msg.attach(MIMEText(text, "plain"))

    # Send the email via Gmail's SMTP server
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")


# Scheduler to run every weekday at the specified wake-up time
def schedule_task():
    scheduler = BlockingScheduler(timezone=TIMEZONE)

    @scheduler.scheduled_job('cron', day_of_week='mon-fri', hour=int(WAKEUP_TIME.split(":")[0]),
                             minute=int(WAKEUP_TIME.split(":")[1]))
    def job():
        weather_info = get_weather()
        stock_info = get_stock_data()
        send_email(weather_info, stock_info)

    scheduler.start()


# Manually trigger the job to test it now
if __name__ == "__main__":
    # Manually trigger the job to test it now
    weather_info = get_weather()
    stock_info = get_stock_data()
    send_email(weather_info, stock_info)

    # Run the scheduler to ensure the task will continue to run at the scheduled time
    schedule_task()
