import os

from PIL import ImageFont


def font(family, style, size, fontdir):
    return ImageFont.truetype(os.path.join(fontdir, f"{family}/{family}-{style}.ttf"), size)
