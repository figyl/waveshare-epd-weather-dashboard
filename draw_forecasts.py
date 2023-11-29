import io
import json
import locale
import logging
import os
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from PIL import Image
from PIL import ImageDraw
from PIL import ImageOps

import owm_forecasts
from src.fonts import font
from src.weather_icons import weather_icons
from weather_display import WeatherDisplay


## Configure logger instance for local logging
logging.root.handlers = []
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - [%(levelname)s] - %(message)s")
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

## Paths config
_HERE = os.path.dirname(__file__)
uidir = os.path.join(_HERE, "src", "ui-icons")

## Read Settings
with open(os.path.join(_HERE, "config.json"), "r") as configfile:
    config = json.load(configfile)

lat = float(config["lat"])
lon = float(config["lon"])
wind_units = config["wind_units"]
if wind_units =="beaufort":
    windDispUnit = "bft" 
elif wind_units == "knots":
    windDispUnit = "kn" 
elif wind_units == "km_h":
    windDispUnit = "km/h"
elif wind_units == "miles_hour":
    windDispUnit = "mph"
else:
    windDispUnit = ""
temp_units = config["temp_units"]
if temp_units == "fahrenheit":
    tempDispUnit = "F"
elif temp_units == "celsius":
    tempDispUnit = "°"
token = config["token"]
keep_history = config["history"]
use_owm_icons = bool(config["use_owm_icons"])
min_max_annotations = bool(config["min_max_annotations"])
locale.setlocale(locale.LC_TIME, config["locale"])


def get_image_from_plot(fig: plt) -> Image:
    buf = io.BytesIO()
    fig.savefig(buf)
    buf.seek(0)
    return Image.open(buf)


def createBaseImage(display: WeatherDisplay) -> Image:
    """
    Creates an RGB Image object with the background and current date
    :param display:
        WeatherDisplay object with all display parameters
    :return:
        Background image
    """
    # Create white image
    image = Image.new("RGB", (display.width_px, display.height_px), (255, 255, 255))
    image_draw = ImageDraw.Draw(image)

    # Create black rectangle for the current weather section
    rect_width = int(display.width_px / 4)
    image_draw.rectangle((0, 0, rect_width, display.height_px), fill=0)

    # Add text with current date
    now = datetime.now()
    dateString = now.strftime("%d. %B")
    dateFont = font.font("Poppins", "Bold", 20)
    # Get the width of the text
    dateStringbbox = dateFont.getbbox(dateString)
    dateW = dateStringbbox[2] - dateStringbbox[0]
    # Draw the current date centered
    image_draw.text(((rect_width - dateW) / 2, 5), dateString, font=dateFont, fill=(255, 255, 255))

    return image


def addCurrentWeather(display: WeatherDisplay, image: Image, current_weather, hourly_forecasts) -> Image:
    """
    Adds current weather situation to the left of the image
    :param display:
        WeatherDisplay object with all display parameters
    :param image:
        Image object to add the forecast to
    :param current_weather:
        Dict of current weather
    :param hourly_forecasts:
        List of hourly weather forecasts
    :return:
        Current weather added to image
    """
    ## Create drawing object for image
    image_draw = ImageDraw.Draw(image)

    ## Add detailed weather status text to the image
    sumString = current_weather.detailed_status.replace(" ", "\n ")
    sumFont = font.font("Poppins", "Regular", 28)
    maxW = 0
    totalH = 0
    for word in sumString.split("\n "):
        sumStringbbox = sumFont.getbbox(word)
        sumW = sumStringbbox[2] - sumStringbbox[0]
        sumH = sumStringbbox[3] - sumStringbbox[1]
        maxW = max(maxW, sumW)
        totalH += sumH
    sumtext_x = int((display.left_section_width - maxW) / 2)
    sumtext_y = int(display.height_px * 0.19) - totalH
    image_draw.multiline_text((sumtext_x, sumtext_y), sumString, font=sumFont, fill=(255, 255, 255), align="center")

    ## Add current weather icon to the image
    icon = weather_icons.get_weather_icon(
        icon_name=current_weather.weather_icon_name, size=150, use_owm_icons=use_owm_icons
    )
    # Create a mask from the alpha channel of the weather icon
    if len(icon.split()) == 4:
        mask = icon.split()[-1]
    else:
        mask = None
    # Paste the foreground of the icon onto the background 7with the help of the mask
    icon_x = int((display.left_section_width - icon.width) / 2)
    icon_y = int(display.height_px * 0.2)
    image.paste(icon, (icon_x, icon_y), mask)

    ## Add current temperature to the image
    tempString = f"{current_weather.temperature(temp_units)['feels_like']:.0f}{tempDispUnit}"
    tempFont = font.font("Poppins", "Bold", 68)
    # Get the width of the text
    tempStringbbox = tempFont.getbbox(tempString)
    tempW = tempStringbbox[2] - tempStringbbox[0]
    temp_x = int((display.left_section_width - tempW) / 2)
    temp_y = int(display.height_px * 0.4375)
    # Draw the current temp centered
    image_draw.text((temp_x, temp_y), tempString, font=tempFont, fill=(255, 255, 255))

    # Add icon for rain forecast
    rainIcon = Image.open(os.path.join(uidir, "rain-chance.bmp"))
    rainIcon = rainIcon.resize((40, 40))
    rain_y = int(display.height_px * 0.625)
    image.paste(rainIcon, (15, rain_y))

    # Amount of precipitation within next 3h
    rain = hourly_forecasts[0]["precip_3h_mm"]
    precipString = f"{rain:.1g} mm" if rain > 0.0 else " "
    precipFont = font.font("Poppins", "Bold", 28)
    image_draw.text((65, rain_y), precipString, font=precipFont, fill=(255, 255, 255))

    # Add icon for wind speed
    windIcon = Image.open(os.path.join(uidir, "wind.bmp"))
    windIcon = windIcon.resize((40, 40))
    wind_y = int(display.height_px * 0.719)
    image.paste(windIcon, (15, wind_y))

    # Max. wind speed within next 3h
    wind_gust = f"{hourly_forecasts[0]['wind_gust']:.0f}"
    wind = f"{hourly_forecasts[0]['wind']:.0f}"
    if wind == wind_gust:
        windString = f"{wind} {windDispUnit}"
    else:
        windString = f"{wind} - {wind_gust} {windDispUnit}"
    windFont = font.font("Poppins", "Bold", 28)
    image_draw.text((65, wind_y), windString, font=windFont, fill=(255, 255, 255))

    # Add icon for Humidity
    humidityIcon = Image.open(os.path.join(uidir, "humidity.bmp"))
    humidityIcon = humidityIcon.resize((40, 40))
    humidity_y = int(display.height_px * 0.8125)
    image.paste(humidityIcon, (15, humidity_y))

    # Humidity
    humidityString = f"{current_weather.humidity} %"
    humidityFont = font.font("Poppins", "Bold", 28)
    image_draw.text((65, humidity_y), humidityString, font=humidityFont, fill=(255, 255, 255))

    # Add icon for uv
    uvIcon = Image.open(os.path.join(uidir, "uv.bmp"))
    uvIcon = uvIcon.resize((40, 40))
    ux_y = int(display.height_px * 0.90625)
    image.paste(uvIcon, (15, ux_y))

    # uvindex
    uvString = f"{current_weather.uvi if current_weather.uvi else ''}"
    uvFont = font.font("Poppins", "Bold", 28)
    image_draw.text((65, ux_y), uvString, font=uvFont, fill=(255, 255, 255))

    return image


def addHourlyForecast(display: WeatherDisplay, image: Image, current_weather: dict, hourly_forecasts: list) -> Image:
    """
    Adds a plot for temperature and amount of rain for the upcoming hours
    :param display:
        WeatherDisplay object with all display parameters
    :param image:
        Image object to add the forecast to
    :param current_weather:
        Dict of current weather
    :param hourly_forecasts:
        List of hourly weather forecasts
    :return:
        Weather plot added to image
    """
    ## Create drawing object for image
    image_draw = ImageDraw.Draw(image)

    ## Draw hourly chart title
    title_x = display.left_section_width + 20  # X-coordinate of the title
    title_y = 5
    chartTitleString = "Temperatur und Niederschlag"
    chartTitleFont = font.font("Poppins", "Bold", 20)
    image_draw.text((title_x, title_y), chartTitleString, font=chartTitleFont, fill=0)

    ## Plot the data
    # Define the chart parameters
    w, h = int(0.75 * display.width_px), int(0.45 * display.height_px)  # Width and height of the graph

    # Length of our time axis
    num_ticks_x = 22  # ticks*3 hours
    timestamps = [item["datetime"] for item in hourly_forecasts][:num_ticks_x]
    temperatures = np.array([item["temp"] for item in hourly_forecasts])[:num_ticks_x]
    precipitation = np.array([item["precip_3h_mm"] for item in hourly_forecasts])[:num_ticks_x]

    # Create the figure
    fig, ax1 = plt.subplots(figsize=(w / display.dpi, h / display.dpi), dpi=display.dpi)

    # Plot Temperature as line plot in red
    ax1.plot(timestamps, temperatures, marker=".", linestyle="-", color="r")
    temp_base = 3 if temp_units == "celsius" else 5
    fig.gca().yaxis.set_major_locator(ticker.MultipleLocator(base=temp_base))
    ax1.tick_params(axis="y", colors="red")
    ax1.set_yticks(ax1.get_yticks())
    ax1.set_yticklabels([f"{int(value)}{tempDispUnit}" for value in ax1.get_yticks()])
    ax1.grid(visible=True, axis="both")  # Adding grid

    if min_max_annotations == True:
        # Calculate min_temp and max_temp values based on the minimum and maximum temperatures in the hourly data
        min_temp = np.min(temperatures)
        max_temp = np.max(temperatures)
        # Find positions of min and max values
        min_temp_index = np.argmin(temperatures)
        max_temp_index = np.argmax(temperatures)
        ax1.text(
            timestamps[min_temp_index],
            min_temp,
            f"Min: {min_temp:.1f}{tempDispUnit}",
            ha="left",
            va="top",
            color="red",
            fontsize=12,
        )
        ax1.text(
            timestamps[max_temp_index],
            max_temp,
            f"Max: {max_temp:.1f}{tempDispUnit}",
            ha="left",
            va="bottom",
            color="blue",
            fontsize=12,
        )

    # Create the second part of the plot as a bar chart for amount of precipitation
    ax2 = ax1.twinx()
    width = np.min(np.diff(mdates.date2num(timestamps)))
    ax2.bar(timestamps, precipitation, color="blue", width=width, alpha=0.2)
    ax2.tick_params(axis="y", colors="blue")
    ax2.set_ylim([0, 10])
    ax2.set_yticks(ax2.get_yticks())
    ax2.set_yticklabels([f"{value:.0f}" for value in ax2.get_yticks()])

    fig.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
    fig.gca().xaxis.set_major_formatter(mdates.DateFormatter("%a"))
    fig.gca().xaxis.set_minor_locator(mdates.HourLocator(interval=3))
    fig.tight_layout()  # Adjust layout to prevent clipping of labels

    # Get image from plot and add it to the image
    hourly_forecast_plot = get_image_from_plot(plt)
    plot_x = display.left_section_width + 5
    plot_y = title_y + 30
    image.paste(hourly_forecast_plot, (plot_x, plot_y))
    return image


def addDailyForecast(display: WeatherDisplay, image: Image, hourly_forecasts) -> Image:
    """
    Adds daily weather forecasts to the given image
    :param display:
        WeatherDisplay object with all display parameters
    :param image:
        Image object to add the forecast to
    :param hourly_forecasts:
        List of hourly weather forecasts
    :return:
        Daily forecasts added to image
    """
    ## Create drawing object for image
    image_draw = ImageDraw.Draw(image)

    ## Draw daily chart title
    title_y = int(display.height_px / 2)  # Y-coordinate of the title
    weeklyTitleString = "Tageswerte"
    chartTitleFont = font.font("Poppins", "Bold", 20)
    image_draw.text((display.left_section_width + 20, title_y), weeklyTitleString, font=chartTitleFont, fill=0)

    # Define the parameters
    number_of_forecast_days = 5  # including today
    # Spread evenly, starting from title width
    rectangle_width = int((display.width_px - (display.left_section_width + 40)) / number_of_forecast_days)
    # Maximum height for each rectangle (avoid overlapping with title)
    rectangle_height = int(display.height_px / 2 - 20)

    # Rain icon is static
    rainIcon = Image.open(os.path.join(uidir, "rain-chance.bmp"))
    rainIcon.convert("L")
    rainIcon = ImageOps.invert(rainIcon)
    weeklyRainIcon = rainIcon.resize((20, 20))

    # Loop through the upcoming days' data and create rectangles
    for i in range(number_of_forecast_days):
        x_rect = display.left_section_width + 20 + i * rectangle_width  # Start from the title width
        y_rect = int(display.height_px / 2 + 30)

        day_data = owm_forecasts.get_forecast_for_day(days_from_today=i, hourly_forecasts=hourly_forecasts)
        rect = Image.new("RGBA", (int(rectangle_width), int(rectangle_height)), (255, 255, 255))
        rect_draw = ImageDraw.Draw(rect)

        # Date string: Day of week on line 1, date on line 2
        short_day_font = font.font("Poppins", "ExtraBold", 24)
        short_month_day_font = font.font("Poppins", "Bold", 16)
        short_day_name = datetime.fromtimestamp(day_data["datetime"]).strftime("%a")
        short_month_day = datetime.fromtimestamp(day_data["datetime"]).strftime("%b %d")
        short_day_name_text = rect_draw.textbbox((0, 0), short_day_name, font=short_day_font)
        short_month_day_text = rect_draw.textbbox((0, 0), short_month_day, font=short_month_day_font)
        day_name_x = (rectangle_width - short_day_name_text[2] + short_day_name_text[0]) / 2
        short_month_day_x = (rectangle_width - short_month_day_text[2] + short_month_day_text[0]) / 2
        rect_draw.text((day_name_x, 0), short_day_name, fill=0, font=short_day_font)
        rect_draw.text(
            (short_month_day_x, 30),
            short_month_day,
            fill=0,
            font=short_month_day_font,
        )

        ## Min and max temperature split into diagonal placement
        min_temp = day_data["temp_min"]
        max_temp = day_data["temp_max"]
        temp_text_min = f"{min_temp:.0f}{tempDispUnit}"
        temp_text_max = f"{max_temp:.0f}{tempDispUnit}"
        rect_temp_font = font.font("Poppins", "ExtraBold", 24)
        temp_text_max_bbox = rect_draw.textbbox((0, 0), temp_text_max, font=rect_temp_font)
        temp_x_offset = 20
        # this is upper left: max temperature
        temp_text_max_x = temp_x_offset
        temp_text_max_y = int(rectangle_height * 0.25)
        # this is lower right: min temperature
        temp_text_min_x = int((rectangle_width - temp_text_max_bbox[2] + temp_text_max_bbox[0]) / 2) + temp_x_offset + 7
        temp_text_min_y = int(rectangle_height * 0.33)
        rect_draw.text((temp_text_min_x, temp_text_min_y), temp_text_min, fill=0, font=rect_temp_font)
        rect_draw.text(
            (temp_text_max_x, temp_text_max_y),
            temp_text_max,
            fill=0,
            font=rect_temp_font,
        )

        # Weather icon for the day
        icon_code = day_data["icon"]
        icon = weather_icons.get_weather_icon(icon_name=icon_code, size=80, use_owm_icons=use_owm_icons)
        icon_x = int((rectangle_width - icon.width) / 2)
        icon_y = int(rectangle_height * 0.4)
        # Create a mask from the alpha channel of the weather icon
        if len(icon.split()) == 4:
            mask = icon.split()[-1]
        else:
            mask = None
        # Paste the foreground of the icon onto the background with the help of the mask
        rect.paste(icon, (int(icon_x), icon_y), mask)

        ## Precipitation icon and text
        rain = day_data["precip_mm"]
        rain_text = f"{rain:.0f}" if rain > 0.0 else " "
        rain_font = font.font("Poppins", "ExtraBold", 22)
        # Icon
        rain_icon_x = int((rectangle_width - icon.width) / 2)
        rain_icon_y = int(rectangle_height * 0.82)
        rect.paste(weeklyRainIcon, (rain_icon_x, rain_icon_y))
        # Text
        rain_text_y = int(rectangle_height * 0.8)
        rect_draw.text(
            (rain_icon_x + weeklyRainIcon.width + 10, rain_text_y), rain_text, fill=0, font=rain_font, align="right"
        )
        image.paste(rect, (int(x_rect), int(y_rect)))
    return image


def get_forecast_image(display: WeatherDisplay) -> Image:
    ## Grab OWM API data
    (current_weather, hourly_forecasts) = owm_forecasts.get_owm_data(lat=lat, lon=lon, token=token)

    ## Create Base Image
    my_image = createBaseImage(display=display)

    ## Add Current Weather
    my_image = addCurrentWeather(
        display=display, image=my_image, current_weather=current_weather, hourly_forecasts=hourly_forecasts
    )

    ## Add Hourly Forecast
    my_image = addHourlyForecast(
        display=display, image=my_image, current_weather=current_weather, hourly_forecasts=hourly_forecasts
    )

    ## Add Daily Forecast
    my_image = addDailyForecast(display=display, image=my_image, hourly_forecasts=hourly_forecasts)

    return my_image


if __name__ == "__main__":
    # if called directly, this gives you the entire weather forecast display as an image

    ## Configure Display
    my_weather_display = WeatherDisplay(pixel_width=800, pixel_height=480, width_mm=163, height_mm=98)

    ## Get the Weather Forecast as image
    my_image = get_forecast_image(my_weather_display)

    ## Save the Image as PNG
    my_image = my_image.rotate(90, expand=1)
    my_image.save("./openweather_full.png")

