"""
Simple geometric weather icons -- sun, cloud, rain, snow, fog, thunder --
drawn with pygame primitives so there's no image asset to ship. Mapped
from Open-Meteo's weather codes via ICON_FOR_CODE.
"""
import pygame

SUN_YELLOW = (255, 204, 0)
CLOUD_GREY = (200, 200, 210)
CLOUD_DARK = (140, 140, 155)
RAIN_BLUE = (120, 170, 255)
SNOW_WHITE = (235, 235, 245)
BOLT_YELLOW = (255, 221, 51)
FOG_GREY = (170, 170, 180)


def _draw_cloud(surface, cx, cy, scale, color):
    r = int(scale * 0.32)
    pygame.draw.circle(surface, color, (cx - r, cy), r)
    pygame.draw.circle(surface, color, (cx + r, cy), r)
    pygame.draw.circle(surface, color, (cx, cy - int(r * 0.6)), int(r * 1.15))
    body = pygame.Rect(cx - r, cy, r * 2, int(r * 0.9))
    pygame.draw.rect(surface, color, body)


def draw_clear(surface, cx, cy, scale):
    r = int(scale * 0.3)
    pygame.draw.circle(surface, SUN_YELLOW, (cx, cy), r)
    for i in range(8):
        import math
        ang = i * math.pi / 4
        x1 = cx + int((r + 4) * math.cos(ang))
        y1 = cy + int((r + 4) * math.sin(ang))
        x2 = cx + int((r + 10) * math.cos(ang))
        y2 = cy + int((r + 10) * math.sin(ang))
        pygame.draw.line(surface, SUN_YELLOW, (x1, y1), (x2, y2), 2)


def draw_partly_cloudy(surface, cx, cy, scale):
    r = int(scale * 0.22)
    pygame.draw.circle(surface, SUN_YELLOW, (cx - int(r * 0.7), cy - int(r * 0.5)), r)
    _draw_cloud(surface, cx + int(scale * 0.08), cy + int(scale * 0.08), scale * 0.85, CLOUD_GREY)


def draw_cloudy(surface, cx, cy, scale):
    _draw_cloud(surface, cx, cy, scale, CLOUD_GREY)


def draw_fog(surface, cx, cy, scale):
    _draw_cloud(surface, cx, cy - int(scale * 0.1), scale * 0.8, FOG_GREY)
    w = int(scale * 0.45)
    for i, dy in enumerate([0.28, 0.4, 0.52]):
        y = cy + int(scale * dy)
        pygame.draw.line(surface, FOG_GREY, (cx - w, y), (cx + w, y), 2)


def draw_rain(surface, cx, cy, scale):
    _draw_cloud(surface, cx, cy - int(scale * 0.15), scale * 0.85, CLOUD_DARK)
    for dx in (-0.22, 0.0, 0.22):
        x = cx + int(scale * dx)
        y0 = cy + int(scale * 0.18)
        pygame.draw.line(surface, RAIN_BLUE, (x, y0), (x - 3, y0 + 12), 2)


def draw_snow(surface, cx, cy, scale):
    _draw_cloud(surface, cx, cy - int(scale * 0.15), scale * 0.85, CLOUD_GREY)
    for dx in (-0.22, 0.0, 0.22):
        x = cx + int(scale * dx)
        y = cy + int(scale * 0.24)
        pygame.draw.circle(surface, SNOW_WHITE, (x, y), 2)
        pygame.draw.circle(surface, SNOW_WHITE, (x, y + 8), 2)


def draw_thunder(surface, cx, cy, scale):
    _draw_cloud(surface, cx, cy - int(scale * 0.15), scale * 0.85, CLOUD_DARK)
    y0 = cy + int(scale * 0.16)
    bolt = [
        (cx + 3, y0),
        (cx - 4, y0 + 8),
        (cx + 1, y0 + 8),
        (cx - 5, y0 + 16),
        (cx + 6, y0 + 7),
        (cx + 1, y0 + 7),
    ]
    pygame.draw.polygon(surface, BOLT_YELLOW, bolt)


ICON_DRAW_FUNCS = {
    "clear": draw_clear,
    "partly_cloudy": draw_partly_cloudy,
    "cloudy": draw_cloudy,
    "fog": draw_fog,
    "rain": draw_rain,
    "snow": draw_snow,
    "thunder": draw_thunder,
}

# Maps Open-Meteo weather codes (see data/weather.py WEATHER_CODES) to an
# icon key above.
ICON_FOR_CODE = {
    0: "clear", 1: "clear",
    2: "partly_cloudy",
    3: "cloudy",
    45: "fog", 48: "fog",
    51: "rain", 53: "rain", 55: "rain",
    61: "rain", 63: "rain", 65: "rain",
    66: "rain", 67: "rain",
    71: "snow", 73: "snow", 75: "snow", 77: "snow",
    80: "rain", 81: "rain", 82: "rain",
    85: "snow", 86: "snow",
    95: "thunder", 96: "thunder", 99: "thunder",
}


def draw_icon(surface, weather_code, cx, cy, scale=48):
    """Draws the icon for the given Open-Meteo weather code centered at
    (cx, cy). Falls back to 'cloudy' for unrecognized codes."""
    key = ICON_FOR_CODE.get(weather_code, "cloudy")
    ICON_DRAW_FUNCS[key](surface, cx, cy, scale)
