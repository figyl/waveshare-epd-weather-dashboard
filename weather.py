#!/usr/bin/python
import logging
import os
from datetime import datetime

from PIL import Image
from PIL import ImageDraw

import epd7in5_V2
from font import font
from weather_draw import addWeather
from weather_draw import createBaseImage

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

        width = epd.width
        height = epd.height
        image = createBaseImage(height=height, width=width)

        image = addWeather(image=image, height=height, width=width)

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
    # my_image = createBaseImage(height=480, width=800)
    # my_image = addWeather(image=my_image, height=480, width=800)
    # my_image.save(os.path.join(repodir, "latest-image.png"))
