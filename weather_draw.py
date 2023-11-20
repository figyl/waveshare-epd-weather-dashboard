from PIL import Image, ImageDraw, ImageOps
from font import font
from datetime import datetime
import arrow
import numpy as np
import requests
import sys
import os
import json
import logging
import urllib.request 
from pyowm import OWM
from pyowm.utils import config
from pyowm.utils import timestamps as owm_timestamps
from pyowm.utils.config import get_default_config

logging.basicConfig(level=logging.DEBUG)

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

def callOwm(lat, lon, token):
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
        icon = forecast.weather_icon_name
        hourly_data_dict.append({
            "temp_celsius": temp,
            "precip_liter": None, # TODO
            "icon": icon,
            "datetime": forecast_timings[forecasts.index(forecast)].datetime
        })
   
    return (current_weather, hourly_data_dict)

def addWeather(image:Image, height, width):
    ## Create drawing object from image
    image_draw = ImageDraw.Draw(image)

    ## Grab OWM API data
    (current_weather, hourly_forecasts) = callOwm(lat=lat, lon=lon, token=token)
    
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

    # Add icon for rain probability
    rainIcon = Image.open(os.path.join(uidir, "rain-chance.bmp"))
    rainIcon = rainIcon.resize((40, 40))
    image.paste(rainIcon, (15, 300))

    # Rain probability
    percipString = f"{current_weather.rain['1h']*100}%"
    percipFont = font("Poppins", "Bold", 28, fontdir=fontdir)
    image_draw.text((65, 300), percipString, font=percipFont, fill=0)

    # Add icon for wind speed
    windIcon = Image.open(os.path.join(uidir, "wind.bmp"))
    windIcon = windIcon.resize((40, 40))
    image.paste(windIcon, (15, 345))

    # Wind speed
    windSpeedUnit = "km/h" if units == "metric" else "mp/h"
    windString = f"{current_weather.wnd['speed']}{windSpeedUnit}"
    windFont = font("Poppins", "Bold", 28, fontdir=fontdir)
    image_draw.text((65, 345), windString, font=windFont, fill=0)

    # Add icon for Humidity
    humidityIcon = Image.open(os.path.join(uidir, "humidity.bmp"))
    humidityIcon = humidityIcon.resize((40, 40))
    image.paste(humidityIcon, (15, 390))

    # Humidity
    humidityString = f"{current_weather.humidity}%"
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
    
    # Draw chart title
    chartTitleString = "Stündliche Vorhersage"
    chartTitleFont = font("Poppins", "Bold", 32, fontdir=fontdir)
    image_draw.text((220, 5), chartTitleString, font=chartTitleFont, fill=0)

    # Extract temperature values and timestamps from the hourly data
    timestamps = [item["datetime"] for item in hourly_forecasts]
    temperatures = np.array([item["temp_celsius"] for item in hourly_forecasts])

    # Calculate ymin and ymax values based on the minimum and maximum temperatures in the hourly data and add/take some extra
    ymin = np.min(temperatures) - 2
    ymax = np.max(temperatures) + 2

    # Define the chart parameters
    x, y = 250, 55  # Start position on the image
    w, h = 520, 150  # Width and height of the graph

    # Number of ticks you want on each axis
    num_ticks_x = 24  # For 24 hours
    num_ticks_y = 10  # One tick for every 2 degrees Celsius

    # Calculate tick increments
    x_increment = 1  # 1 hour increments for 24 hours
    y_increment = 2

    # Calculate the position of the y-axis
    y_axis_x = x
    y_axis_y = y + h

    # Draw x axis and ticks
    image_draw.line((x, y_axis_y, x + w, y_axis_y), fill=0, width=3)  # Draw x axis
    labelFont = font("Poppins", "Bold", 12, fontdir=fontdir)  # You can change the font and size as needed

    for i in range(num_ticks_x):
        tick_x = x + (i / (num_ticks_x - 1)) * w
        image_draw.line((tick_x, y_axis_y, tick_x, y_axis_y + 5), fill=0, width=2)
        label = timestamps[i].strftime('%H')
        label_bbox = image_draw.textbbox((tick_x, y_axis_y + 5), label, font=labelFont)
        image_draw.text((tick_x - (label_bbox[2] - label_bbox[0]) / 2, y_axis_y + 5 + 5), label, fill=0, font=labelFont)

    # Draw y axis and ticks
    image_draw.line((x, y, x, y_axis_y), fill=0, width=3)  # Draw y axis

    for i in range(num_ticks_y):
        tick_y = y + (i / (num_ticks_y - 1)) * h
        image_draw.line((x - 5, tick_y, x, tick_y), fill=0, width=2)
        label = f"{ymax - i * y_increment:.0f}"  # Display float values with one decimal place
        label_bbox = image_draw.textbbox((x - 5, tick_y), label, font=labelFont)
        image_draw.text((x - 10 - (label_bbox[2] - label_bbox[0]), tick_y - (label_bbox[3] - label_bbox[1]) / 2), label, fill=0, font=labelFont)

    # Normalize temperature data to fit within the graph
    normalized_temperatures = (temperatures - ymin) * h / (ymax - ymin)
    x_coords = np.linspace(x, x + w, num_ticks_x)
    y_coords = y + h - normalized_temperatures

    # Plot the temperature data on the graph
    for i in range(num_ticks_x - 1):
        image_draw.line([x_coords[i], y_coords[i], x_coords[i + 1], y_coords[i + 1]], fill=0, width=3)

    # Find and draw lowest and highest temperatures within the displayed hours
    lowest_temp_index = np.argmin(temperatures[:num_ticks_x])
    highest_temp_index = np.argmax(temperatures[:num_ticks_x])

    # Draw labels for lowest and highest temperatures
    lowest_temp_label = f"min: {temperatures[lowest_temp_index]:.1f}°"
    highest_temp_label = f"max: {temperatures[highest_temp_index]:.1f}°"

    # Draw the lowest temperature label
    image_draw.text((x_coords[lowest_temp_index]+2, y_coords[lowest_temp_index] + 5), lowest_temp_label, fill=0, font=labelFont,
                    anchor="lt", align="center")

    # Draw the highest temperature label
    image_draw.text((x_coords[highest_temp_index]+2, y_coords[highest_temp_index] - 15), highest_temp_label, fill=0, font=labelFont,
                    anchor="lt", align="center")

    # Draw chart title
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