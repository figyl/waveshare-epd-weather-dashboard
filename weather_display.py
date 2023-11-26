import math


class WeatherDisplay:
    def __init__(self, pixel_width: int, pixel_height: int, width_mm: float, height_mm: float):
        ## DPI calculation
        screen_width_in = width_mm / 25.4  # 163 mm for 7in5
        screen_height_in = height_mm / 25.4  # 98 mm for 7in5
        self.dpi = math.sqrt(
            (float(pixel_width) ** 2 + float(pixel_height) ** 2) / (screen_width_in**2 + screen_height_in**2)
        )
        self.width_px = pixel_width
        self.height_px = pixel_height
        self.left_section_width = int(pixel_width / 4)
