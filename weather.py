#!/usr/bin/python
import logging
import os
from datetime import datetime

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageOps

import epd7in5_V2
from font import font
from weather_draw import addWeather

logging.basicConfig(level=logging.DEBUG)

repodir = os.path.dirname(os.path.realpath(__file__))
srcdir = os.path.join(repodir, "src")
fontdir = os.path.join(srcdir, "fonts")


def createBaseImage(height, width) -> Image:
    # Create white image
    image = Image.new("1", (width, height), 255)
    draw = ImageDraw.Draw(image)

    # Create black rectangle for the current weather
    # draw.rectangle((0, 0, 200, 480), fill=0)

    # Add text with current date and location
    now = datetime.now()
    dateString = now.strftime("%d. %B")
    dateFont = font("Poppins", "Bold", 20, fontdir=fontdir)
    # Get the width of the text
    dateStringbbox = dateFont.getbbox(dateString)
    dateW, dateH = dateStringbbox[2] - dateStringbbox[0], dateStringbbox[3] - dateStringbbox[1]
    # Draw the current date centered
    draw.text(((200 - dateW) / 2, 5), dateString, font=dateFont, fill=0)

    # Draw the location centered
    timeString = now.strftime("%H:%M")
    timeFont = font("Poppins", "Bold", 26, fontdir=fontdir)
    timeStringbbox = timeFont.getbbox(timeString)
    timeW, timeH = timeStringbbox[2] - timeStringbbox[0], timeStringbbox[3] - timeStringbbox[1]
    draw.text(((200 - timeW) / 2, 30), timeString, font=timeFont, fill=0)
    return image


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
    # my_image.save(os.path.join(repodir,"latest-image.png"))
