import os

from PIL import ImageFont


def font(family, style, size):
    # Returns the TrueType font object for the given characteristics
    fontdir = os.path.dirname(os.path.abspath(__file__))
    if family == "Roboto" and style == "ExtraBold":
        style = "Black"
    elif family == "Ubuntu" and style in ["ExtraBold", "Black"]:
        style = "Bold"
    elif family == "OpenSans" and style == "Black":
        style = "ExtraBold"
    return ImageFont.truetype(os.path.join(fontdir, f"{family}/{family}-{style}.ttf"), size)
