import os
import urllib

from PIL import Image
from PIL import ImageOps


def get_weather_icon(icon_name, size, use_owm_icons: bool = False) -> Image:
    # Returns the requested weather icon as Image

    weatherdir = os.path.dirname(os.path.abspath(__file__))

    if use_owm_icons == True:
        urllib.request.urlretrieve(
            url=f"https://openweathermap.org/img/wn/{icon_name}@2x.png", filename="./forecast_image.png"
        )
        icon = Image.open("./forecast_image.png")
    else:
        icon = Image.open(os.path.join(weatherdir, f"{icon_name}.png"))
        icon = icon.convert("L")
        icon = ImageOps.invert(icon)

    icon = icon.resize((size, size))

    return icon
