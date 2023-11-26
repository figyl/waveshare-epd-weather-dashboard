#!/usr/bin/python
import logging
import os

import epd7in5_V2
from draw_forecasts import get_forecast_image
from weather_display import WeatherDisplay

logging.basicConfig(level=logging.DEBUG)

repodir = os.path.dirname(os.path.realpath(__file__))
srcdir = os.path.join(repodir, "src")
fontdir = os.path.join(srcdir, "fonts")


def main():
    try:
        epd = epd7in5_V2.EPD()
        logging.info("Init EPD and clear ...")
        epd.init()
        epd.Clear()

        logging.info("Drawing image ...")
        ## Display configuration
        my_weather_display = WeatherDisplay(pixel_width=epd.width, pixel_height=epd.height, width_mm=163, height_mm=98)
        ## Get the Weather Forecast as image
        image = get_forecast_image(display=my_weather_display)
        ## Display and save
        epd.display(epd.getbuffer(image))
        image.save(os.path.join(repodir, "latest-image.jpg"))

        logging.info("Goto Sleep...")
        epd.sleep()
        exit()

    except KeyboardInterrupt:
        logging.info("ctrl + c:")
        epd7in5_V2.epdconfig.module_exit()
        exit()


if __name__ == "__main__":
    main()
