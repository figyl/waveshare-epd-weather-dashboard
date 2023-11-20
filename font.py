from PIL import ImageFont
import os

def font(family, style, size, fontdir):
    return ImageFont.truetype(
        os.path.join(fontdir, f"{family}/{family}-{style}.ttf"), size
    )