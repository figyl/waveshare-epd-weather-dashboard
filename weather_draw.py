from PIL import Image, ImageDraw, ImageOps
from font import font
from datetime import datetime
from dateutil import tz
import arrow
import numpy as np
import os
import json
import logging
import urllib.request 
from pyowm import OWM
from pyowm.utils import config
from pyowm.utils import timestamps as owm_timestamps
from pyowm.utils.config import get_default_config
from scipy.interpolate import make_interp_spline
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import math
import io

## DPI calculation
# TODO: move this to screen class
resolution_width = 800.0
resolution_height = 480.0
screen_width_in = 163/25.4
screen_height_in = 98/25.4
dpi = math.sqrt((resolution_width ** 2 + resolution_height ** 2) / (screen_width_in ** 2 + screen_height_in ** 2))

def get_image_from_plot(fig:plt)->Image:
    buf = io.BytesIO()
    fig.savefig(buf)
    buf.seek(0)
    return Image.open(buf)

def plot_hourly_forecast(hourly_forecasts)->Image:
    # Extract temperature values and timestamps from the hourly data
    # Number of ticks you want on each axis
    num_ticks_x = 20  # ticks*3 hours
    timestamps = [item["datetime"] for item in hourly_forecasts][:num_ticks_x]
    temperatures = np.array([item["temp_celsius"] for item in hourly_forecasts])[:num_ticks_x]
    percipitation = np.array([item["percip_3h_mm"] for item in hourly_forecasts])[:num_ticks_x]

    # Calculate min_temp and max_temp values based on the minimum and maximum temperatures in the hourly data
    min_temp = np.min(temperatures)
    max_temp = np.max(temperatures)
    # Find positions of min and max values
    min_temp_index = np.argmin(temperatures)
    max_temp_index = np.argmax(temperatures)

    # Define the chart parameters
    w, h = 520, 180  # Width and height of the graph
    plt.figure(figsize=(w/dpi, h/dpi), dpi=dpi)  # Adjust the figure size if needed
    plt.plot(timestamps, temperatures, marker='.', linestyle=None, color='r')
    # optional: min/max annotations
    #plt.text(timestamps[min_temp_index], min_temp, f'Min: {min_temp:.1f}°C', ha='left', va='top', color='red', fontsize=12)
    #plt.text(timestamps[max_temp_index], max_temp, f'Max: {max_temp:.1f}°C', ha='left', va='bottom', color='blue', fontsize=12)

    plt.grid(True) # Adding grid
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%a'))
    plt.gca().yaxis.set_major_locator(ticker.MultipleLocator(base=2))
    #plt.ylabel("°C", rotation=0, loc="top")
    plt.tight_layout()  # Adjust layout to prevent clipping of labels
    return get_image_from_plot(plt)

# Configure logger instance for local logging
logging.root.handlers = []
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

repodir = os.path.dirname(os.path.realpath(__file__))
srcdir = os.path.join(repodir, "src")
fontdir = os.path.join(srcdir, "fonts")
uidir = os.path.join(srcdir, "ui-icons")
weatherdir = os.path.join(srcdir, "weather-icons")
historydir = os.path.join(srcdir, "history")

with open(os.path.join(repodir,"config.json"),"r") as configfile:
    config = json.load(configfile)

lat = float(config["lat"])
lon = float(config["lon"])
units = config["units"]
token = config["token"]
keep_history = config["history"]

def saveToFile(data):
    try:
        with open(os.path.join(historydir, f"{datetime.now().strftime('openweather_%Y-%m-%d_%H-%M-%S')}.json"),"w",) as outfile:
            json.dump(data, outfile, indent=4)
    except:
        logging.error("Error while writing openweather response to file.")

def get_weather_icon(icon_name):
    # TODO: use OWM icon or alternatively local ones from weather-icons
    urllib.request.urlretrieve(url=f"https://openweathermap.org/img/wn/{icon_name}@2x.png", filename="./forecast_image.png")
    icon = Image.open("./forecast_image.png")
    icon = icon.resize((150, 150))
    icon = icon.convert("L")
    icon = ImageOps.invert(icon)
    icon = icon.convert("1")
    return icon

def get_owm_data(lat, lon, token):
    config_dict = get_default_config()
    config_dict['language'] = "de"

    owm = OWM(token, config_dict)

    mgr = owm.weather_manager()

    current_observation = mgr.weather_at_coords(lat=lat,lon=lon)
    current_weather = current_observation.weather
    hourly_forecasts = mgr.forecast_at_coords(lat=lat,lon=lon,interval="3h")

    # Forecasts are provided for every 3rd full hour
    # - find out how many hours there are until the next 3rd full hour
    now = arrow.utcnow()
    tz_zone = tz.gettz("Europe/Berlin")
    if (now.hour % 3) != 0:
        hour_gap = 3 - (now.hour % 3)
    else:
        hour_gap = 3

    # Create timings for hourly forcasts
    forecast_timings = [now.shift(hours=+ hour_gap + step).floor('hour') for step in range(0, 120, 3)]

    # Create forecast objects for given timings
    forecasts = [hourly_forecasts.get_weather_at(forecast_time.datetime) for
                    forecast_time in forecast_timings]

    # Add forecast-data to fc_data list of dictionaries
    hourly_data_dict = []
    for forecast in forecasts:
        temp = forecast.temperature(unit='celsius')['temp']
        try: 
            percip_mm = forecast.rain["3h"]
        except KeyError:
            percip_mm = 0.0
        icon = forecast.weather_icon_name
        hourly_data_dict.append({
            "temp_celsius": temp,
            "percip_3h_mm": percip_mm,
            "icon": icon,
            # TODO: check whether this TZ conversion is actually right
            "datetime": forecast_timings[forecasts.index(forecast)].datetime.astimezone(tz=tz_zone)
        })
   
    return (current_weather, hourly_data_dict)

def addWeather(image:Image, height, width)->Image:
    ## Create drawing object from image
    image_draw = ImageDraw.Draw(image)

    ## Grab OWM API data
    (current_weather, hourly_forecasts) = get_owm_data(lat=lat, lon=lon, token=token)
    
    ## Add current weather icon to the image
    icon = get_weather_icon(current_weather.weather_icon_name)
    image.paste(icon, (25, 85))

    ## Add current temperature to the image
    tempString = f"{current_weather.temperature('celsius')['feels_like']:.1f}°"
    tempFont = font("Poppins", "Bold", 68, fontdir=fontdir)
    # Get the width of the text
    tempStringbbox = tempFont.getbbox(tempString)
    tempW, tempH = tempStringbbox[2] - tempStringbbox[0], tempStringbbox[3] - tempStringbbox[1]
    # Draw the current temp centered
    image_draw.text(((200 - tempW) / 2, 210), tempString, font=tempFont, fill=0)

    sumString = current_weather.detailed_status
    sumFont = font("Poppins", "Regular", 28, fontdir=fontdir)
    sumStringbbox = sumFont.getbbox(sumString)
    sumW, sumH = sumStringbbox[2] - sumStringbbox[0], sumStringbbox[3] - sumStringbbox[1]
    # Draw the current temp centered
    image_draw.text(((200 - sumW) / 2, 60), sumString, font=sumFont, fill=0)

    # Add icon for rain forecast
    rainIcon = Image.open(os.path.join(uidir, "rain-chance.bmp"))
    rainIcon = rainIcon.resize((40, 40))
    image.paste(rainIcon, (15, 300))

    # Amount of precipitation within next 3h
    percipString = f"{hourly_forecasts[0]['percip_3h_mm']:.1f} mm"
    percipFont = font("Poppins", "Bold", 28, fontdir=fontdir)
    image_draw.text((65, 300), percipString, font=percipFont, fill=0)

    # Add icon for wind speed
    windIcon = Image.open(os.path.join(uidir, "wind.bmp"))
    windIcon = windIcon.resize((40, 40))
    image.paste(windIcon, (15, 345))

    # Wind speed
    windSpeedUnit = "km/h" if units == "metric" else "mp/h"
    windString = f"{current_weather.wnd['gust']:.0f} {windSpeedUnit}"
    windFont = font("Poppins", "Bold", 28, fontdir=fontdir)
    image_draw.text((65, 345), windString, font=windFont, fill=0)

    # Add icon for Humidity
    humidityIcon = Image.open(os.path.join(uidir, "humidity.bmp"))
    humidityIcon = humidityIcon.resize((40, 40))
    image.paste(humidityIcon, (15, 390))

    # Humidity
    humidityString = f"{current_weather.humidity} %"
    humidityFont = font("Poppins", "Bold", 28, fontdir=fontdir)
    image_draw.text((65, 390), humidityString, font=humidityFont, fill=0)

    # Add icon for uv
    uvIcon = Image.open(os.path.join(uidir, "uv.bmp"))
    uvIcon = uvIcon.resize((40, 40))
    image.paste(uvIcon, (15, 435))

    # uvindex
    uvString = f"{current_weather.uvi}"
    uvFont = font("Poppins", "Bold", 28, fontdir=fontdir)
    image_draw.text((65, 435), uvString, font=uvFont, fill=255)

    ## Draw hourly chart title
    chartTitleString = "Stündliche Vorhersage"
    chartTitleFont = font("Poppins", "Bold", 32, fontdir=fontdir)
    image_draw.text((220, 5), chartTitleString, font=chartTitleFont, fill=0)
    hourly_forecast_plot = plot_hourly_forecast(hourly_forecasts=hourly_forecasts)
    image.paste(hourly_forecast_plot, (220, 55))

    ## Draw daily chart title
    weeklyTitleString = "Kommende Tage"
    image_draw.text((220, 240), weeklyTitleString, font=chartTitleFont, fill=0)

    # Define the rectangle parameters
    #TODO: daily_data = data['daily']
    num_rectangles = 7
    rectangle_width = (width - 240) / num_rectangles  # Spread evenly, starting from title width
    title_height = 240  # Y-coordinate of the title
    rectangle_height = (height - title_height - 40)  # Maximum height for each rectangle (avoid overlapping with title)
    weeklyRainIcon = rainIcon.resize((30,30))
    weeklyRainIcon = weeklyRainIcon.convert("L")
    weeklyRainIcon = ImageOps.invert(weeklyRainIcon)
    weeklyRainIcon = weeklyRainIcon.convert("1")
    # Loop through the next 7 days' data and create rectangles
    #for i in range(num_rectangles):
    #    day_data = daily_data[i]
    #    x_rect = 220 + i * rectangle_width  # Start from the title width
    #    y_rect = title_height + 50
    #    rect = Image.new("1", (int(rectangle_width), int(rectangle_height)), 255)
    #    rect_draw = ImageDraw.Draw(rect)

        # Date in two lines: full day name and short month, 0 padded day
    #    short_day_font = font("Poppins", "Black", 24, fontdir=fontdir)
    #    short_month_day_font = font("Poppins", "Bold", 20, fontdir=fontdir)
    #    short_day_name = datetime.utcfromtimestamp(day_data['dt']).strftime('%a')
    #    short_month_day = datetime.utcfromtimestamp(day_data['dt']).strftime('%b %d')
    #    short_day_name_text = rect_draw.textbbox((0, 0), short_day_name, font=short_day_font)
    #    short_month_day_text = rect_draw.textbbox((0, 0), short_month_day, font=short_month_day_font)
    #    day_name_x = (rectangle_width - short_day_name_text[2] + short_day_name_text[0]) / 2
    #    short_month_day_x = (rectangle_width - short_month_day_text[2] + short_month_day_text[0]) / 2
    #    rect_draw.text((day_name_x, 5), short_day_name, fill=0, font=short_day_font)
    #    rect_draw.text((short_month_day_x, 10 + short_day_name_text[3] - short_day_name_text[1]), short_month_day, fill=0, font=short_month_day_font)

        # Icon for the day (resized to fit, increased size by 20 pixels)
    #    icon_code = day_data['weather'][0]['icon']
    #    icon = Image.open(os.path.join(weatherdir, f"{icon_code}.png"))
    #    icon = icon.resize((60, 60))
    #    icon_x = (rectangle_width - icon.width) / 2
    #    icon_y = 55
    #    rect.paste(icon, (int(icon_x), icon_y))

        # Min and max temperature split into two lines with 5 pixels spacing
    #    min_temp = day_data['temp']['min']
    #    max_temp = day_data['temp']['max']
    #    temp_text_min = f"Min: {min_temp:.0f}°"
    #    temp_text_max = f"Max: {max_temp:.0f}°"
    #    rect_temp_font=font("Poppins","Bold",16, fontdir=fontdir)
    #    temp_text_min_bbox = rect_draw.textbbox((0, 0), temp_text_min, font=rect_temp_font)
    #    temp_text_max_bbox = rect_draw.textbbox((0, 0), temp_text_max, font=rect_temp_font)
    #    temp_text_min_x = (rectangle_width - temp_text_min_bbox[2] + temp_text_min_bbox[0]) / 2
    #    temp_text_max_x = (rectangle_width - temp_text_max_bbox[2] + temp_text_max_bbox[0]) / 2
    #    rect_draw.text((temp_text_min_x, 140), temp_text_min, fill=0, font=rect_temp_font)
    #    rect_draw.text((temp_text_max_x, 150 + temp_text_min_bbox[3] - temp_text_min_bbox[1]), temp_text_max, fill=0, font=rect_temp_font)

        # Precipitation icon and text centered
    #    pop = day_data['pop'] * 100
    #    pop_text = f"{pop:.0f}%"
    #    pop_font = font("Poppins","Black",20, fontdir=fontdir)
    #    pop_text_bbox = rect_draw.textbbox((0, 0), pop_text, font=pop_font)
    #    combined_width = rainIcon.width + pop_text_bbox[2] - pop_text_bbox[0]
    #    combined_x = (rectangle_width - combined_width) / 2
    #    rect.paste(weeklyRainIcon, (int(combined_x), 110))
    #    rect_draw.text((int(combined_x) + rainIcon.width, 110), pop_text, fill=0, font=pop_font)

    #    image.paste(rect, (int(x_rect), int(y_rect)))
    return image

if __name__ == "__main__":
    # Create white display
    width = 800
    height = 480
    my_image = Image.new("1", (width, height), 255)
    my_image = addWeather(image=my_image, width=width, height=height)
    my_image.save("./owm_weather_test.png")