#!/usr/bin/python
import logging

from src.drivers import epd7in5b_V2

logging.basicConfig(level=logging.DEBUG)

try:
    logging.info("epd7in5b_V2")
    epd = epd7in5b_V2.EPD()

    logging.info("init and Clear")
    epd.init()
    epd.Clear()

    logging.info("Goto Sleep...")
    epd.sleep()

except IOError as e:
    logging.info(e)

except KeyboardInterrupt:
    logging.info("ctrl + c:")
    epd7in5b_V2.epdconfig.module_exit()
    exit()
