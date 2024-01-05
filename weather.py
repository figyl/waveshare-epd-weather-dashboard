#!/usr/bin/python
from PIL import Image
import logging
import numpy
import os

from src.drivers import epd7in5b_V2
from draw_forecasts import get_forecast_image
from weather_display import WeatherDisplay

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)

repodir = os.path.dirname(os.path.realpath(__file__))
srcdir = os.path.join(repodir, "src")
fontdir = os.path.join(srcdir, "fonts")


def main():
    try:
        epd = epd7in5b_V2.EPD()

        logging.info("Drawing image ...")
        ## Display configuration
        my_weather_display = WeatherDisplay(pixel_width=epd.width, pixel_height=epd.height, width_mm=163, height_mm=98)
        ## Get the Weather Forecast as image
        image = get_forecast_image(display=my_weather_display)
        image_black, image_red = to_palette(image=image,palette="bwr")
        image.save(os.path.join(repodir, "latest-image.jpg"))
        logging.info("Init EPD ...")
        epd.init()

        # logging.info("Clear EPD ...")
        # epd.Clear()

        logging.info("Painting image ...")
        epd.display(epd.getbuffer(image_black), epd.getbuffer(image_red))

        logging.info("Put EPD to Sleep...")
        epd.sleep()
        exit()

    except KeyboardInterrupt:
        logging.info("ctrl + c:")
        epd7in5b_V2.epdconfig.module_exit()
        exit()

# Stolen from inkycal
def to_palette(image, palette, dither=True) -> (Image, Image):
    """Maps an image to a given colour palette.
    Maps each pixel from the image to a colour from the palette.
    Args:
      - palette: A supported token. (see below)
      - dither:->bool. Use dithering? Set to `False` for solid colour fills.
    Returns:
      - two images: one for the coloured band and one for the black band.
    Raises:
      - ValueError if palette token is not supported
    Supported palette tokens:
    >>> 'bwr' # black-white-red
    >>> 'bwy' # black-white-yellow
    >>> 'bw'  # black-white
    >>> '16gray' # 16 shades of gray
    """
    # 

    image.convert('RGB')
    logger.info('loaded Image')

    if palette == 'bwr':
        # black-white-red palette
        pal = [255, 255, 255, 0, 0, 0, 255, 0, 0]
    elif palette == 'bwy':
        # black-white-yellow palette
        pal = [255, 255, 255, 0, 0, 0, 255, 255, 0]
    elif palette == 'bw':
        pal = None
    elif palette == '16gray':
        pal = [x for x in range(0, 256, 16)] * 3
        pal.sort()
    else:
        logger.error('The given palette is unsupported.')
        raise ValueError('The given palette is not supported.')
    if pal:
        # The palette needs to have 256 colors, for this, the black-colour
        # is added until the
        colours = len(pal) // 3
        # print(f'The palette has {colours} colours')
        if 256 % colours != 0:
            # print('Filling palette with black')
            pal += (256 % colours) * [0, 0, 0]
        # print(pal)
        colours = len(pal) // 3
        # print(f'The palette now has {colours} colours')
        # Create a dummy image to be used as a palette
        palette_im = Image.new('P', (1, 1))
        # Attach the created palette. The palette should have 256 colours
        # equivalent to 768 integers
        palette_im.putpalette(pal * (256 // colours))
        # Quantize the image to given palette
        quantized_im = image.quantize(palette=palette_im, dither=dither)
        quantized_im = quantized_im.convert('RGB')
        # get rgb of the non-black-white colour from the palette
        rgb = [pal[x:x + 3] for x in range(0, len(pal), 3)]
        rgb = [col for col in rgb if col != [0, 0, 0] and col != [255, 255, 255]][0]
        r_col, g_col, b_col = rgb
        # print(f'r:{r_col} g:{g_col} b:{b_col}')
        # Create an image buffer for black pixels
        buffer1 = numpy.array(quantized_im)
        # Get RGB values of each pixel
        r, g, b = buffer1[:, :, 0], buffer1[:, :, 1], buffer1[:, :, 2]
        # convert coloured pixels to white
        buffer1[numpy.logical_and(r == r_col, g == g_col)] = [255, 255, 255]
        # reconstruct image for black-band
        im_black = Image.fromarray(buffer1)
        # Create a buffer for coloured pixels
        buffer2 = numpy.array(quantized_im)
        # Get RGB values of each pixel
        r, g, b = buffer2[:, :, 0], buffer2[:, :, 1], buffer2[:, :, 2]
        # convert black pixels to white
        buffer2[numpy.logical_and(r == 0, g == 0)] = [255, 255, 255]
        # convert non-white pixels to black
        buffer2[numpy.logical_and(g == g_col, b == 0)] = [0, 0, 0]
        # reconstruct image for colour-band
        im_colour = Image.fromarray(buffer2)
        # self.preview(im_black)
        # self.preview(im_colour)

    else:
        im_black = image.convert('1', dither=dither)
        im_colour = Image.new(mode='1', size=im_black.size, color='white')

    logger.info('mapped image to specified palette')

    return im_black, im_colour

if __name__ == "__main__":
    main()
