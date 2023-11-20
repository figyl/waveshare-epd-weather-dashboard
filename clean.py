#!/usr/bin/python
import logging

from PIL import Image
from PIL import ImageDraw

import epd7in5_V2

logging.basicConfig(level=logging.DEBUG)

try:
    logging.info("epd7in5_V2")
    epd = epd7in5_V2.EPD()

    logging.info("init and Clear")
    epd.init()
    epd.Clear()

    logging.info("2. Drawing on the Vertical image...")
    Limage = Image.new("1", (epd.height, epd.width), 255)  # 255: clear the frame
    draw = ImageDraw.Draw(Limage)

    logging.info("Goto Sleep...")
    epd.sleep()

except IOError as e:
    logging.info(e)

except KeyboardInterrupt:
    logging.info("ctrl + c:")
    epd7in5_V2.epdconfig.module_exit()
    exit()
