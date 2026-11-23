#!/usr/bin/env python3
"""
v5opt Broadsheet News Infographic Builder — Sunday 22 November 2026
Pure Python + Pillow deterministic 1024x1024 renderer + 300x300 preview.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# 1. Canvas, Palette & Font Configuration
# ---------------------------------------------------------------------------

CANVAS_W = 1024
CANVAS_H = 1024
MARGIN_X = 12
INNER_W = CANVAS_W - 2 * MARGIN_X  # 1000 px
MAX_BYTES = 1_048_576  # 1 MiB limit

OUT_DIR = Path(__file__).resolve().parent
ENTRY_PATH = OUT_DIR / "entry.png"
PREVIEW_PATH = OUT_DIR / "preview-300.png"

# Warm editorial broadsheet palette (inspired by 99-pt broadsheet references)
BG_PAPER = "#F7F2E8"
CARD_BG = "#FFFDF8"
CARD_BORDER = "#CFC6B6"
CARD_ART_BG = "#F3ECE0"
KPI_BG = "#FAF5EB"
DATE_CHECK_BG = "#FFF4F2"

INK_DARK = "#141B26"
INK_BODY = "#1D2430"
INK_MUTED = "#3A4352"
RULE_SOFT = "#CFC5B4"
RULE_DARK = "#18202D"

NAVY_TOP = "#101D3D"
NAVY_UTC = "#14213D"
NAVY_SUB = "#273A63"
CRIMSON = "#9E1F28"
GOLD = "#F2C864"
WHITE = "#FFFFFF"

REGION_ORDER = [
    "EUROPE",
    "ASIA-PACIFIC",
    "AMERICAS",
    "MIDDLE EAST",
    "AFRICA",
    "OCEANIA",
    "WORLD",
]

REGION_COLORS: Dict[str, str] = {
    "EUROPE": "#21557A",
    "ASIA-PACIFIC": "#B8561B",
    "AMERICAS": "#6C458F",
    "MIDDLE EAST": "#A6232A",
    "AFRICA": "#2D7445",
    "OCEANIA": "#1B7B7B",
    "WORLD": "#48505C",
}

REGION_MAP_FILL: Dict[str, str] = {
    "EUROPE": "#8FB2C9",
    "ASIA-PACIFIC": "#DFAA84",
    "AMERICAS": "#B9A1CE",
    "MIDDLE EAST": "#D89498",
    "AFRICA": "#93BF9F",
    "OCEANIA": "#8DC5C4",
    "WORLD": "#ADB4BE",
}

REGION_SHORT: Dict[str, str] = {
    "EUROPE": "EU",
    "ASIA-PACIFIC": "APAC",
    "AMERICAS": "AMER",
    "MIDDLE EAST": "ME",
    "AFRICA": "AFR",
    "OCEANIA": "OCE",
    "WORLD": "WLD",
}

STATUS_STYLE: Dict[str, Tuple[str, str, str]] = {
    # status -> (fill, border, text)
    "CONFIRMED": ("#E4F3EA", "#287A45", "#1A5930"),
    "ONGOING": ("#FDF1D8", "#B67812", "#845308"),
    "REPORTED": ("#E6EFF8", "#2B5E8E", "#1C4469"),
    "CLAIM": ("#FBE6E8", "#B3252D", "#8B171E"),
}

FONT_PATHS = {
    "serif_bold": "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "serif_reg": "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "serif_cond_bold": "/usr/share/fonts/truetype/dejavu/DejaVuSerifCondensed-Bold.ttf",
    "sans_bold": "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "sans_reg": "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "sans_cond_bold": "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
    "sans_cond_reg": "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
    "mono_bold": "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
}

_FONT_CACHE: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}


def get_font(key: str, size: int) -> ImageFont.FreeTypeFont:
    cache_key = (key, size)
    if cache_key not in _FONT_CACHE:
        path = FONT_PATHS[key]
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing required font: {path}")
        _FONT_CACHE[cache_key] = ImageFont.truetype(path, size)
    return _FONT_CACHE[cache_key]


# ---------------------------------------------------------------------------
# 2. Data Model & 34 Verified Stories (Sunday 22 November 2026)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Story:
    id: int
    region: str
    domain: str
    location: str
    headline: str
    lead: str
    source: str
    status: str
    coords: Optional[Tuple[float, float]] = None  # (lon, lat) for map pins #10-#23


STORIES: List[Story] = [
    # --- Main 3x3 Feature Cards (#1-#9) ---
    Story(
        1, "WORLD", "CLIMATE", "ANTALYA",
        "COP31 collapses in Antalya without a deal",
        "Nearly 200 nations deadlock past 03:00 UTC over fossil fuels and a $120bn floor.",
        "Reuters, AFP, BBC", "CONFIRMED",
    ),
    Story(
        2, "EUROPE", "MILITARY", "UKRAINE",
        "Russia fires 186 drones; 161 downed",
        "Overnight wave of 72 jet UAVs batters Dymer flats and triggers grid blackouts.",
        "Ukr. Air Force, BBC", "CONFIRMED",
    ),
    Story(
        3, "AFRICA", "MILITARY", "BENGHAZI",
        "Russian warship Merkury sinks in Benghazi",
        "Corvette capsizes after suspected sea-drone strike in Libya; Maltese ship hit.",
        "Reuters, Al Jazeera", "CONFIRMED",
    ),
    Story(
        4, "MIDDLE EAST", "MILITARY", "BAHRAIN",
        "Bahrain: Iran strike hurts 2; IRGC claims hit",
        "Manama cites industrial fire near Sitra; Iran alleges US Patriot radar struck.",
        "MEE, Times of Israel", "CLAIM",
    ),
    Story(
        5, "ASIA-PACIFIC", "POLITICS", "HONG KONG",
        "Hong Kong polls hit 98.8% with 856 hopefuls",
        "Election Committee vote fills 723 seats as 5,640 electors vote 01:00-10:00 UTC.",
        "info.gov.hk, China Daily", "CONFIRMED",
    ),
    Story(
        6, "WORLD", "SPACE", "MERCURY",
        "BepiColombo reaches Mercury after 8 yrs",
        "European-Japanese spacecraft enters orbit to map the planet's crust and field.",
        "BBC, ESA", "CONFIRMED",
    ),
    Story(
        7, "AMERICAS", "SECURITY", "MEXICO",
        "Mexico arrests FBI Most Wanted cartel chief",
        "Special forces seize Sinaloa boss Fausto Meza Flores after an intense shootout.",
        "BBC, Reuters", "CONFIRMED",
    ),
    Story(
        8, "OCEANIA", "SPORT", "WELLINGTON",
        "India posts record 720/9; NZ holds draw",
        "Visitors shatter New Zealand's Test record before hosts bat 120 overs to draw.",
        "ESPN, Jamaica Observer", "CONFIRMED",
    ),
    Story(
        9, "ASIA-PACIFIC", "DISASTER", "BANTEN",
        "Indonesia plant fire kills 3; 36 still missing",
        "Rescuers comb gutted Banten confectionery plant while four injured recover.",
        "AFP, BBC, France 24", "ONGOING",
    ),
    # --- Two-Column Wire Briefs (#10-#25; #10-#23 mapped with coordinates) ---
    Story(
        10, "EUROPE", "POLITICS", "BRATISLAVA",
        "Fico refuses EU's €45bn loan to Ukraine",
        "", "Reuters, Kyiv Post", "CONFIRMED", (17.1, 48.1),
    ),
    Story(
        11, "MIDDLE EAST", "HUMANITARIAN", "GAZA",
        "Gaza toll hits 74,742; Hamas urges mediator talks",
        "", "WAFA, Anadolu", "ONGOING", (34.5, 31.5),
    ),
    Story(
        12, "AMERICAS", "SPORT", "SAN ANTONIO",
        "Wembanyama posts historic 50-pt, 19-reb game",
        "", "CBS, KSAT", "CONFIRMED", (-98.5, 29.4),
    ),
    Story(
        13, "AMERICAS", "DISASTER", "TUPANCIRETÃ",
        "Supercell storm kills 5, hurts 250+ in Brazil",
        "", "AFP", "CONFIRMED", (-53.8, -29.1),
    ),
    Story(
        14, "ASIA-PACIFIC", "TECH/AI", "SEOUL",
        "S. Korea education chief quits over AI exam chaos",
        "", "AFP, BBC", "CONFIRMED", (127.0, 37.6),
    ),
    Story(
        15, "AFRICA", "CONFLICT", "KHARTOUM",
        "RSF drones hit Khartoum homes & UN site, 4 dead",
        "", "Al Jazeera", "REPORTED", (32.5, 15.6),
    ),
    Story(
        16, "AFRICA", "DISASTER", "BAYELSA",
        "Boat capsize kills at least 24 mourners in Nigeria",
        "", "AllAfrica", "CONFIRMED", (6.1, 4.8),
    ),
    Story(
        17, "AFRICA", "DIPLOMACY", "OYO, CONGO",
        "Kenya's Ruto & DRC's Tshisekedi restore full ties",
        "", "Pan African Visions", "CONFIRMED", (15.9, -1.2),
    ),
    Story(
        18, "OCEANIA", "POLITICS", "CANBERRA",
        "Albanese backs Bowen after COP31 collapse uproar",
        "", "Guardian AU", "CONFIRMED", (149.1, -35.3),
    ),
    Story(
        19, "OCEANIA", "CLIMATE", "PORT MORESBY",
        "Pope Leo XIV urges aid as drought grips all 22 PNG zones",
        "", "Crux, CathNews", "ONGOING", (147.2, -9.4),
    ),
    Story(
        20, "EUROPE", "SPORT", "TURIN",
        "Alcaraz beats Zverev for first ATP Finals title",
        "", "Reuters, Guardian", "CONFIRMED", (7.7, 45.1),
    ),
    Story(
        21, "EUROPE", "SAFETY", "MANCHESTER",
        "12,000 evacuated at Co-op Live over suspected gas",
        "", "BBC, SBS", "REPORTED", (-2.2, 53.5),
    ),
    Story(
        22, "ASIA-PACIFIC", "CULTURE", "OKINAWA",
        "Japan marks Shuri Castle hall rebuild 7 yrs post-fire",
        "", "Wash. Post, JT", "CONFIRMED", (127.7, 26.2),
    ),
    Story(
        23, "MIDDLE EAST", "POLITICS", "BEIRUT",
        "Lebanon marks 83rd Independence Day as locals return",
        "", "NPR, L'Orient", "ONGOING", (35.5, 33.9),
    ),
    Story(
        24, "EUROPE", "SPORT", "PORTIMÃO",
        "Márquez clinches 8th MotoGP title, ties Agostini",
        "", "AP", "CONFIRMED",
    ),
    Story(
        25, "AMERICAS", "SPORT", "LAS VEGAS",
        "Verstappen wins Las Vegas GP ahead of McLarens",
        "", "Guardian, National", "CONFIRMED",
    ),
    # --- Full-Width 3-Column Supplemental Briefs (#26-#34) ---
    Story(
        26, "EUROPE", "SHIPPING", "GULF OF FINLAND",
        "Russia-bound ship towed after suspected drone hit",
        "", "BBC, Finnish DF", "REPORTED",
    ),
    Story(
        27, "EUROPE", "SPORT", "LIVERPOOL",
        "Liverpool routs Man Utd 4-0 in Pochettino debut",
        "", "Guardian, BBC", "CONFIRMED",
    ),
    Story(
        28, "MIDDLE EAST", "MILITARY", "RIYADH",
        "Saudi coalition intercepts Houthi missiles & drones",
        "", "Anadolu, ISW", "REPORTED",
    ),
    Story(
        29, "MIDDLE EAST", "CONFLICT", "WEST BANK",
        "Israeli opposition slams settler arson on villages",
        "", "Guardian", "ONGOING",
    ),
    Story(
        30, "AMERICAS", "AVIATION", "ATLANTA",
        "Software fault delays 1,000+ Delta Air Lines flights",
        "", "AP, The Hindu", "CONFIRMED",
    ),
    Story(
        31, "AMERICAS", "MILITARY", "IOWA",
        "US Army to detonate unstable munitions despite court",
        "", "BBC", "CONFIRMED",
    ),
    Story(
        32, "ASIA-PACIFIC", "ECONOMY", "GAZIPUR",
        "Bangladesh garment clashes; 95 BGB platoons sent",
        "", "Business Standard", "ONGOING",
    ),
    Story(
        33, "ASIA-PACIFIC", "SPACE", "ISLAMABAD",
        "Pakistan's first astronaut departs for Tiangong",
        "", "APP, Arab News", "CONFIRMED",
    ),
    Story(
        34, "WORLD", "TRADE", "GENEVA",
        "WTO flags record $1.5tn export & $5.4tn import curbs",
        "", "WTO, SunStar", "CONFIRMED",
    ),
]

UTC_TIMELINE: List[Tuple[str, str]] = [
    ("01:00", "HK polls open"),
    ("01:25", "Cartel boss held"),
    ("03:00", "COP31 stalls"),
    ("04:00", "Vegas F1 start"),
    ("09:20", "Korea ed. quits"),
    ("10:44", "Bepi at Mercury"),
    ("14:05", "Indo. plant fire"),
    ("20:43", "Alcaraz wins ATP"),
]

EXCLUDED_ITEMS: List[str] = [
    "Peru M6.7 quake (Fri 20 Nov)",
    "Russia 400-drone wave (19-20 Nov; 22 Nov = 186)",
    "APEC Shenzhen trilateral (Thu 19 Nov)",
    "French Senate 205-110 vote (Fri 20 Nov)",
    "2025 Bangladesh quake & Vietnam floods",
]


def extract_verified_kpis(stories: Sequence[Story]) -> List[Tuple[str, str, int, str]]:
    """
    Extract all 6 KPI figures directly from STORIES text via regex and assert
    exact correspondence — zero unverified hardcoding.
    Returns list of (value, label, story_id, region).
    """
    by_id = {s.id: s for s in stories}

    def pull(sid: int, pattern: str) -> str:
        s = by_id[sid]
        blob = f"{s.headline} {s.lead}"
        m = re.search(pattern, blob)
        if not m:
            raise AssertionError(f"KPI pattern {pattern!r} not found in story #{sid}: {blob!r}")
        return m.group(1)

    specs = [
        (2, r"\bfires\s+(\d+)\s+drones\b", "DRONES AT UKRAINE"),
        (2, r";\s*(\d+)\s+downed\b", "DRONES DOWNED"),
        (1, r"(\$120bn)\b", "COP31 FINANCE FLOOR"),
        (11, r"hits\s+([\d,]+);", "GAZA DEATH TOLL"),
        (5, r"with\s+(\d+)\s+hopefuls", "HK POLL CANDIDATES"),
        (8, r"record\s+(\d+/\d+);", "INDIA TEST RECORD"),
    ]
    kpis: List[Tuple[str, str, int, str]] = []
    for sid, pat, label in specs:
        val = pull(sid, pat)
        kpis.append((val, label, sid, by_id[sid].region))

    expected = ["186", "161", "$120bn", "74,742", "856", "720/9"]
    got = [k[0] for k in kpis]
    assert got == expected, f"KPI extraction mismatch: got {got}, expected {expected}"
    return kpis


def validate_dataset(stories: Sequence[Story]) -> Counter:
    assert len(stories) == 34, f"Expected 34 stories, got {len(stories)}"
    assert [s.id for s in stories] == list(range(1, 35)), "Story IDs must be 1..34"
    counts = Counter(s.region for s in stories)
    assert set(counts.keys()) == set(REGION_ORDER), f"Unexpected regions: {set(counts.keys())}"
    assert sum(counts.values()) == 34
    for r in REGION_ORDER:
        assert counts[r] >= 3, f"Region {r} has < 3 stories ({counts[r]})"
    mapped = [s for s in stories if s.coords is not None]
    assert [s.id for s in mapped] == list(range(10, 24)), "Map pins must be exactly #10..#23"
    return counts


# ---------------------------------------------------------------------------
# 3. Real Typography Fitting (fit / fit_multiline) & Collision Detection
# ---------------------------------------------------------------------------

def measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def fit(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_key: str,
    max_size: int,
    min_size: int,
    max_width: float,
    max_height: Optional[float] = None,
) -> Tuple[ImageFont.FreeTypeFont, int, int, int]:
    """
    Find the largest font size in [min_size, max_size] where `text` fits strictly
    inside `max_width` (and `max_height` if provided). Fails loudly if impossible.
    Returns (font, size, width, height).
    """
    for size in range(max_size, min_size - 1, -1):
        font = get_font(font_key, size)
        w, h = measure_text(draw, text, font)
        if w <= max_width and (max_height is None or h <= max_height):
            return font, size, w, h
    raise RuntimeError(
        f"fit() overflow: {text!r} cannot fit in w={max_width}, h={max_height} "
        f"even at min_size={min_size} ({font_key})"
    )


def _wrap_words(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: float,
) -> List[str]:
    words = text.split()
    if not words:
        return [""]
    lines: List[str] = []
    cur = words[0]
    for w in words[1:]:
        cand = f"{cur} {w}"
        cw, _ = measure_text(draw, cand, font)
        if cw <= max_width:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def fit_multiline(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_key: str,
    max_size: int,
    min_size: int,
    max_width: float,
    max_lines: int,
    line_spacing: float = 1.18,
    max_height: Optional[float] = None,
) -> Tuple[ImageFont.FreeTypeFont, int, List[str], int]:
    """
    Wrap `text` into at most `max_lines` lines within `max_width` (and `max_height`),
    choosing the largest size in [min_size, max_size]. Returns (font, size, lines, line_h).
    """
    for size in range(max_size, min_size - 1, -1):
        font = get_font(font_key, size)
        lines = _wrap_words(draw, text, font, max_width)
        if len(lines) > max_lines:
            continue
        widths = [measure_text(draw, ln, font)[0] for ln in lines]
        if any(w > max_width for w in widths):
            continue
        line_h = max(int(round(size * line_spacing)), measure_text(draw, "Ag", font)[1])
        total_h = line_h * len(lines)
        if max_height is not None and total_h > max_height:
            continue
        return font, size, lines, line_h
    raise RuntimeError(
        f"fit_multiline() overflow: {text!r} cannot fit in {max_lines} lines x "
        f"w={max_width}, h={max_height} even at min_size={min_size} ({font_key})"
    )


def draw_text_centered(
    draw: ImageDraw.ImageDraw,
    box: Tuple[float, float, float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
) -> Tuple[float, float, float, float]:
    """Draw text visually centered inside `box` using exact ink bbox metrics."""
    x0, y0, x1, y1 = box
    tb = draw.textbbox((0, 0), text, font=font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    tx = x0 + (x1 - x0 - tw) / 2.0 - tb[0]
    ty = y0 + (y1 - y0 - th) / 2.0 - tb[1]
    draw.text((tx, ty), text, font=font, fill=fill)
    return (tx + tb[0], ty + tb[1], tx + tb[2], ty + tb[3])


def draw_text_aligned(
    draw: ImageDraw.ImageDraw,
    box: Tuple[float, float, float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
    align: str = "left",
) -> Tuple[float, float, float, float]:
    """Draw text flush-left or flush-right, vertically centered inside `box`."""
    x0, y0, x1, y1 = box
    tb = draw.textbbox((0, 0), text, font=font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    if align == "right":
        tx = x1 - tw - tb[0]
    else:
        tx = x0 - tb[0]
    ty = y0 + (y1 - y0 - th) / 2.0 - tb[1]
    draw.text((tx, ty), text, font=font, fill=fill)
    return (tx + tb[0], ty + tb[1], tx + tb[2], ty + tb[3])


def draw_text_baseline_centered(
    draw: ImageDraw.ImageDraw,
    x0: float,
    x1: float,
    baseline_y: float,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
) -> Tuple[float, float, float, float]:
    """Horizontally center `text` in [x0, x1] aligned to a shared typographic baseline."""
    ascent, _ = font.getmetrics()
    tb = draw.textbbox((0, 0), text, font=font)
    tw = tb[2] - tb[0]
    tx = x0 + (x1 - x0 - tw) / 2.0 - tb[0]
    ty = baseline_y - ascent
    draw.text((tx, ty), text, font=font, fill=fill)
    return (tx + tb[0], ty + tb[1], tx + tb[2], ty + tb[3])


class CollisionTracker:
    """
    Tracks bounding boxes grouped by layer/container and verifies zero overlap
    and strict containment inside the 1024x1024 canvas.
    """

    def __init__(self, canvas_w: int = CANVAS_W, canvas_h: int = CANVAS_H) -> None:
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        self.groups: Dict[str, List[Tuple[str, Tuple[float, float, float, float]]]] = {}
        self.total_registered = 0

    def add(self, group: str, label: str, box: Tuple[float, float, float, float]) -> None:
        x0, y0, x1, y1 = box
        if x1 < x0 or y1 < y0:
            raise ValueError(f"Invalid inverted box for {group}/{label}: {box}")
        if x0 < -0.5 or y0 < -0.5 or x1 > self.canvas_w + 0.5 or y1 > self.canvas_h + 0.5:
            raise AssertionError(f"Out-of-canvas box {group}/{label}: {box}")
        self.groups.setdefault(group, []).append((label, box))
        self.total_registered += 1

    def assert_no_collisions(self, tolerance: float = 0.25) -> int:
        checked_pairs = 0
        collisions: List[str] = []
        for group, items in self.groups.items():
            n = len(items)
            for i in range(n):
                l1, (ax0, ay0, ax1, ay1) = items[i]
                for j in range(i + 1, n):
                    l2, (bx0, by0, bx1, by1) = items[j]
                    checked_pairs += 1
                    ix = min(ax1, bx1) - max(ax0, bx0)
                    iy = min(ay1, by1) - max(ay0, by0)
                    if ix > tolerance and iy > tolerance:
                        collisions.append(
                            f"[{group}] {l1} {tuple(round(v, 1) for v in items[i][1])} "
                            f"overlaps {l2} {tuple(round(v, 1) for v in items[j][1])} "
                            f"by ({ix:.1f}x{iy:.1f})"
                        )
        if collisions:
            raise AssertionError(
                f"Detected {len(collisions)} layout collision(s):\n" + "\n".join(collisions[:15])
            )
        return checked_pairs


# ---------------------------------------------------------------------------
# 4. World Map Polygons & Iterative Pin Collision Solver (#10-#23)
# ---------------------------------------------------------------------------

# Equirectangular simplified continent/region polygons: (region_key, [(lon, lat), ...])
WORLD_POLYGONS: List[Tuple[str, List[Tuple[float, float]]]] = [
    # AMERICAS
    ("AMERICAS", [
        (-166, 65), (-150, 71), (-132, 69), (-112, 68), (-95, 62), (-82, 63),
        (-65, 60), (-54, 52), (-62, 44), (-71, 41), (-76, 35), (-81, 25),
        (-84, 29), (-90, 29), (-97, 26), (-97, 19), (-88, 21), (-83, 15),
        (-78, 9), (-84, 9), (-93, 15), (-105, 20), (-112, 29), (-118, 33),
        (-125, 42), (-125, 49), (-135, 57), (-152, 60), (-163, 55),
    ]),
    ("AMERICAS", [  # Greenland
        (-52, 60), (-42, 60), (-22, 70), (-18, 79), (-44, 81), (-62, 76), (-55, 67),
    ]),
    ("AMERICAS", [  # South America
        (-79, 10), (-71, 12), (-61, 10), (-50, 1), (-35, -6), (-38, -14),
        (-41, -23), (-50, -29), (-54, -35), (-63, -41), (-68, -53), (-74, -52),
        (-73, -40), (-71, -30), (-71, -18), (-81, -5),
    ]),
    # EUROPE
    ("EUROPE", [  # Continental Europe
        (-9, 37), (-9, 43), (-2, 43), (-4, 48), (2, 51), (8, 54), (10, 57),
        (14, 54), (21, 55), (28, 60), (38, 66), (48, 66), (52, 54), (42, 47),
        (34, 46), (28, 41), (24, 37), (19, 40), (15, 38), (12, 44), (6, 43),
        (3, 42), (-5, 36),
    ]),
    ("EUROPE", [  # UK & Ireland
        (-6, 50), (1, 51), (0, 54), (-2, 58), (-6, 58), (-8, 54), (-10, 52),
    ]),
    ("EUROPE", [  # Scandinavia
        (5, 59), (10, 58), (18, 60), (22, 65), (29, 70), (18, 70), (11, 64),
    ]),
    # AFRICA
    ("AFRICA", [
        (-17, 15), (-13, 27), (-6, 36), (10, 37), (12, 33), (25, 32), (33, 31),
        (43, 12), (51, 11), (42, 0), (40, -11), (35, -24), (28, -33), (18, -35),
        (15, -26), (12, -14), (9, -1), (9, 5), (-4, 5), (-16, 11),
    ]),
    ("AFRICA", [  # Madagascar
        (44, -25), (47, -25), (50, -15), (48, -12), (44, -18),
    ]),
    # MIDDLE EAST
    ("MIDDLE EAST", [
        (26, 41), (36, 42), (45, 40), (54, 38), (61, 35), (61, 25), (56, 26),
        (59, 22), (52, 16), (44, 13), (39, 21), (35, 29), (34, 33), (36, 37),
        (27, 37),
    ]),
    # ASIA-PACIFIC
    ("ASIA-PACIFIC", [  # Main Asia landmass
        (52, 54), (58, 68), (85, 73), (115, 73), (145, 71), (172, 66),
        (162, 58), (142, 54), (136, 44), (129, 40), (126, 35), (122, 38),
        (118, 39), (122, 31), (116, 23), (109, 21), (109, 12), (104, 1),
        (100, 7), (98, 16), (90, 22), (80, 8), (73, 19), (68, 24), (61, 25),
        (61, 35), (54, 38), (52, 47),
    ]),
    ("ASIA-PACIFIC", [  # Japan
        (130, 31), (135, 34), (141, 36), (145, 44), (140, 44), (136, 37), (130, 33),
    ]),
    ("ASIA-PACIFIC", [  # Sumatra & Java
        (95, 5), (105, -6), (115, -8), (114, -9), (103, -7), (95, 2),
    ]),
    ("ASIA-PACIFIC", [  # Borneo / Philippines
        (109, 1), (118, 5), (119, -3), (111, -3),
    ]),
    ("ASIA-PACIFIC", [  # Philippines
        (120, 18), (124, 15), (126, 7), (122, 8), (120, 14),
    ]),
    # OCEANIA
    ("OCEANIA", [  # Australia
        (114, -22), (123, -16), (131, -12), (137, -15), (142, -11), (146, -18),
        (153, -27), (150, -37), (141, -38), (135, -34), (128, -32), (115, -34),
        (113, -27),
    ]),
    ("OCEANIA", [  # Papua New Guinea
        (131, -2), (141, -3), (150, -10), (146, -10), (137, -5),
    ]),
    ("OCEANIA", [  # New Zealand
        (173, -35), (178, -38), (174, -42), (167, -46), (166, -45), (172, -41),
    ]),
]


def project_lonlat(
    lon: float,
    lat: float,
    map_box: Tuple[float, float, float, float],
) -> Tuple[float, float]:
    """Equirectangular projection covering lon [-168, 178], lat [-54, 76]."""
    x0, y0, x1, y1 = map_box
    lon_min, lon_max = -168.0, 178.0
    lat_min, lat_max = -54.0, 76.0
    px = x0 + (lon - lon_min) / (lon_max - lon_min) * (x1 - x0)
    py = y0 + (lat_max - lat) / (lat_max - lat_min) * (y1 - y0)
    return px, py


def resolve_map_pin_collisions(
    pin_stories: Sequence[Story],
    map_box: Tuple[float, float, float, float],
    pin_radius: float = 8.5,
    min_gap: float = 2.5,
) -> List[Tuple[Story, Tuple[float, float], Tuple[float, float]]]:
    """
    Compute exact anchor (ax, ay) and collision-free display position (px, py)
    for every mapped story (#10-#23). Deterministic iterative repulsion + wall clamp.
    """
    x0, y0, x1, y1 = map_box
    pad = pin_radius + 2.5
    min_dist = 2.0 * pin_radius + min_gap

    anchors: List[Tuple[float, float]] = []
    pos: List[List[float]] = []
    for s in pin_stories:
        assert s.coords is not None
        ax, ay = project_lonlat(s.coords[0], s.coords[1], map_box)
        anchors.append((ax, ay))
        pos.append([
            max(x0 + pad, min(x1 - pad, ax)),
            max(y0 + pad, min(y1 - pad, ay)),
        ])

    n = len(pin_stories)
    box_min = 2.0 * pin_radius + min_gap
    for _ in range(300):
        moved = False
        # Gentle spring pull toward geographic anchor
        for i in range(n):
            ax, ay = anchors[i]
            pos[i][0] += (ax - pos[i][0]) * 0.03
            pos[i][1] += (ay - pos[i][1]) * 0.03

        # Pairwise repulsion enforcing both circular and AABB non-overlap
        for i in range(n):
            for j in range(i + 1, n):
                dx = pos[j][0] - pos[i][0]
                dy = pos[j][1] - pos[i][1]
                ov_x = box_min - abs(dx)
                ov_y = box_min - abs(dy)
                dist = math.hypot(dx, dy)
                if ov_x > 0 and ov_y > 0:
                    if dist < 1e-4:
                        angle = ((pin_stories[i].id * 47 + pin_stories[j].id * 29) % 360) * math.pi / 180.0
                        ux, uy = math.cos(angle), math.sin(angle)
                        push = box_min * 0.6
                    else:
                        ux, uy = dx / dist, dy / dist
                        push = max(min(ov_x, ov_y), max(0.0, min_dist - dist)) * 0.65 + 0.4
                    pos[i][0] -= ux * push
                    pos[i][1] -= uy * push
                    pos[j][0] += ux * push
                    pos[j][1] += uy * push
                    moved = True

        # Strict boundary clamp
        for i in range(n):
            pos[i][0] = max(x0 + pad, min(x1 - pad, pos[i][0]))
            pos[i][1] = max(y0 + pad, min(y1 - pad, pos[i][1]))

        if not moved:
            break

    # Final hard verification: zero pairwise circle overlap
    for i in range(n):
        for j in range(i + 1, n):
            d = math.hypot(pos[j][0] - pos[i][0], pos[j][1] - pos[i][1])
            assert d >= 2.0 * pin_radius + 0.5, (
                f"Map pins #{pin_stories[i].id} and #{pin_stories[j].id} overlap (d={d:.2f})"
            )

    return [(pin_stories[i], anchors[i], (pos[i][0], pos[i][1])) for i in range(n)]


# ---------------------------------------------------------------------------
# 5. Editorial 2px Line-Art Illustrations (No Faces) for Cards #1-#9
# ---------------------------------------------------------------------------

def draw_card_art(
    draw: ImageDraw.ImageDraw,
    story: Story,
    box: Tuple[int, int, int, int],
    accent: str,
) -> None:
    """
    Draw a crisp 2px-stroke geometric editorial line illustration inside `box`
    (68x110 px). Strictly zero human faces; high contrast for 300px readability.
    """
    x0, y0, x1, y1 = box
    w = x1 - x0
    h = y1 - y0
    cx = (x0 + x1) // 2
    ink = INK_DARK
    lw = 2

    # Subtle art frame + bottom domain ribbon inside art box
    draw.rectangle(box, fill=CARD_ART_BG, outline="#D4C9B6", width=1)
    cap_h = 17
    cap_box = (x0 + 1, y1 - cap_h, x1 - 1, y1 - 1)
    draw.rectangle(cap_box, fill=accent)
    cap_txt = story.domain
    f_cap, _, _, _ = fit(draw, cap_txt, "sans_cond_bold", 10, 8, w - 6, cap_h - 2)
    draw_text_centered(draw, cap_box, cap_txt, f_cap, WHITE)

    # Usable art viewport above caption
    ay0 = y0 + 5
    ay1 = y1 - cap_h - 4
    acy = (ay0 + ay1) // 2

    if story.id == 1:
        # COP31 collapse: cracked globe + tilted gavel
        r = 19
        gy = acy + 10
        draw.ellipse((cx - r, gy - r, cx + r, gy + r), outline=ink, width=lw)
        draw.ellipse((cx - 9, gy - r, cx + 9, gy + r), outline=accent, width=lw)
        draw.line((cx - r, gy, cx + r, gy), fill=accent, width=lw)
        draw.line(
            [(cx - 5, gy - r - 2), (cx + 2, gy - 5), (cx - 4, gy + 4), (cx + 5, gy + r + 2)],
            fill=CRIMSON, width=lw,
        )
        draw.line((cx - 16, ay0 + 15, cx + 8, ay0 + 7), fill=ink, width=lw)
        draw.rectangle((cx + 3, ay0 + 3, cx + 17, ay0 + 13), outline=ink, fill=CARD_ART_BG, width=lw)

    elif story.id == 2:
        # 186 drones / 161 downed: radar rings + delta UAVs + intercept crosshair
        ry = acy + 5
        for rr in (23, 15, 7):
            draw.ellipse((cx - rr, ry - rr, cx + rr, ry + rr), outline="#AAB6C6", width=1)
        draw.line((cx - 24, ry, cx + 24, ry), fill="#AAB6C6", width=1)
        draw.line((cx, ry - 24, cx, ry + 24), fill="#AAB6C6", width=1)
        draw.line((cx, ry, cx + 18, ry - 16), fill=accent, width=lw)
        for dx, dy in [(-14, -20), (10, -8)]:
            pts = [(cx + dx, ry + dy - 6), (cx + dx + 8, ry + dy + 5), (cx + dx, ry + dy + 2), (cx + dx - 8, ry + dy + 5)]
            draw.polygon(pts, outline=ink, fill=CARD_ART_BG)
            draw.line(pts + [pts[0]], fill=ink, width=lw)
        bx, by = cx + 10, ry - 8
        draw.line((bx - 6, by - 6, bx + 6, by + 6), fill=CRIMSON, width=lw)
        draw.line((bx - 6, by + 6, bx + 6, by - 6), fill=CRIMSON, width=lw)

    elif story.id == 3:
        # Warship Merkury capsizing in waves (vertically balanced)
        wy = acy + 12
        hull = [(x0 + 9, wy - 15), (x1 - 9, wy + 1), (x1 - 15, wy + 9), (x0 + 13, wy - 5)]
        draw.polygon(hull, fill=CARD_ART_BG)
        draw.line(hull + [hull[0]], fill=ink, width=lw)
        draw.line((cx - 6, wy - 10, cx + 2, wy - 31), fill=ink, width=lw)
        draw.line((cx - 5, wy - 27, cx + 10, wy - 22), fill=accent, width=lw)
        draw.line((cx + 10, wy - 6, cx + 19, wy - 19), fill=CRIMSON, width=lw)
        draw.line((cx + 13, wy - 3, cx + 23, wy - 10), fill=CRIMSON, width=lw)
        for offset in (2, 10):
            pts = []
            for k in range(0, w - 10, 6):
                px = x0 + 5 + k
                py = wy + offset + (3 if (k // 6) % 2 == 0 else -2)
                pts.append((px, py))
            draw.line(pts, fill=accent, width=lw)

    elif story.id == 4:
        # Bahrain refinery tanks + rising smoke + Patriot radar dish
        base_y = ay1 - 7
        draw.line((x0 + 6, base_y, x1 - 6, base_y), fill=ink, width=lw)
        draw.rectangle((x0 + 8, base_y - 21, x0 + 27, base_y), outline=ink, width=lw)
        draw.arc((x0 + 8, base_y - 27, x0 + 27, base_y - 15), 180, 360, fill=ink, width=lw)
        draw.rectangle((x0 + 31, base_y - 15, x0 + 46, base_y), outline=ink, width=lw)
        draw.arc((x0 + 15, base_y - 42, x0 + 35, base_y - 20), 150, 340, fill=CRIMSON, width=lw)
        draw.arc((x0 + 22, ay0 + 5, x0 + 48, base_y - 26), 170, 350, fill=CRIMSON, width=lw)
        draw.arc((x1 - 26, ay0 + 14, x1 - 7, ay0 + 36), 110, 260, fill=accent, width=lw)
        draw.line((x1 - 16, ay0 + 25, x1 - 8, ay0 + 17), fill=accent, width=lw)

    elif story.id == 5:
        # Hong Kong polls: ballot box + dropping ballot + gauge lines
        bx0, by0, bx1, by1 = cx - 20, acy + 1, cx + 20, ay1 - 7
        draw.rectangle((bx0, by0, bx1, by1), outline=ink, width=lw)
        draw.line((bx0 - 3, by0, bx1 + 3, by0), fill=ink, width=lw)
        draw.line((cx - 11, by0 + 4, cx + 11, by0 + 4), fill=accent, width=lw)
        draw.rectangle((cx - 10, ay0 + 7, cx + 10, by0 + 2), outline=ink, fill=CARD_ART_BG, width=lw)
        draw.line([(cx - 5, ay0 + 17), (cx - 1, ay0 + 22), (cx + 6, ay0 + 12)], fill=accent, width=lw)
        draw.line((bx0 + 6, by1 - 9, bx1 - 6, by1 - 9), fill=accent, width=lw)
        draw.line((bx0 + 6, by1 - 15, bx1 - 12, by1 - 15), fill=ink, width=lw)

    elif story.id == 6:
        # BepiColombo orbiter at Mercury
        py = acy + 8
        pr = 17
        draw.ellipse((cx - pr, py - pr, cx + pr, py + pr), outline=ink, width=lw)
        draw.ellipse((cx - 8, py - 6, cx - 1, py + 1), outline=accent, width=lw)
        draw.ellipse((cx + 3, py + 2, cx + 9, py + 8), outline=accent, width=lw)
        draw.ellipse((cx + 2, py - 10, cx + 7, py - 5), outline=ink, width=1)
        draw.arc((x0 + 5, ay0 + 7, x1 - 5, ay1 - 7), 195, 355, fill=accent, width=lw)
        sx, sy = cx, ay0 + 11
        draw.rectangle((sx - 5, sy - 4, sx + 5, sy + 4), outline=ink, fill=CARD_ART_BG, width=lw)
        draw.rectangle((sx - 20, sy - 3, sx - 7, sy + 3), outline=accent, width=lw)
        draw.rectangle((sx + 7, sy - 3, sx + 20, sy + 3), outline=accent, width=lw)

    elif story.id == 7:
        # Mexico cartel arrest: Sierra ridge + helicopter & searchlight
        base_y = ay1 - 7
        peaks = [(x0 + 6, base_y), (x0 + 21, base_y - 24), (x0 + 34, base_y - 11), (x0 + 48, base_y - 27), (x1 - 6, base_y)]
        draw.line(peaks, fill=ink, width=lw)
        hx, hy = cx, ay0 + 13
        draw.line((hx - 20, hy - 6, hx + 20, hy - 6), fill=ink, width=lw)
        draw.line((hx, hy - 6, hx, hy - 1), fill=ink, width=lw)
        draw.ellipse((hx - 10, hy - 1, hx + 8, hy + 10), outline=ink, width=lw)
        draw.line((hx + 8, hy + 4, hx + 20, hy + 2), fill=ink, width=lw)
        draw.line((hx + 20, hy - 2, hx + 20, hy + 6), fill=ink, width=lw)
        draw.line((hx - 2, hy + 10, x0 + 18, base_y - 5), fill=accent, width=lw)
        draw.line((hx + 2, hy + 10, x0 + 42, base_y - 5), fill=accent, width=lw)

    elif story.id == 8:
        # India 720/9 cricket: three stumps + bails + diagonal bat + clean ball arc
        base_y = ay1 - 7
        draw.line((x0 + 10, base_y, x1 - 10, base_y), fill=ink, width=lw)
        for sx in (cx - 10, cx, cx + 10):
            draw.line((sx, base_y, sx, ay0 + 22), fill=ink, width=lw)
        draw.line((cx - 11, ay0 + 20, cx - 1, ay0 + 20), fill=accent, width=lw)
        draw.line((cx + 1, ay0 + 20, cx + 11, ay0 + 20), fill=accent, width=lw)
        draw.line((x0 + 12, ay1 - 14, x1 - 16, ay0 + 10), fill=accent, width=lw)
        draw.line((x0 + 16, ay1 - 10, x1 - 12, ay0 + 14), fill=accent, width=lw)
        draw.ellipse((x0 + 9, ay0 + 6, x0 + 19, ay0 + 16), outline=CRIMSON, width=lw)
        draw.arc((x0 + 14, ay0 + 4, cx + 8, ay0 + 28), 215, 315, fill=CRIMSON, width=lw)

    elif story.id == 9:
        # Indonesia factory fire: sawtooth factory + stylized flame plumes
        base_y = ay1 - 7
        draw.line((x0 + 6, base_y, x1 - 6, base_y), fill=ink, width=lw)
        roof = [
            (x0 + 8, base_y), (x0 + 8, base_y - 24),
            (x0 + 22, base_y - 33), (x0 + 22, base_y - 24),
            (x0 + 36, base_y - 33), (x0 + 36, base_y - 24),
            (x0 + 50, base_y - 33), (x0 + 50, base_y),
        ]
        draw.line(roof, fill=ink, width=lw)
        draw.rectangle((x0 + 14, base_y - 16, x0 + 24, base_y - 7), outline=ink, width=lw)
        draw.rectangle((x0 + 32, base_y - 16, x0 + 42, base_y - 7), outline=ink, width=lw)
        flame1 = [(cx - 10, base_y - 31), (cx - 14, ay0 + 14), (cx - 4, ay0 + 5), (cx + 2, ay0 + 18), (cx + 10, ay0 + 9), (cx + 14, base_y - 31)]
        draw.line(flame1, fill=CRIMSON, width=lw)
        flame2 = [(cx - 3, base_y - 31), (cx + 1, ay0 + 16), (cx + 7, base_y - 31)]
        draw.line(flame2, fill=accent, width=lw)


# ---------------------------------------------------------------------------
# 6. Band Renderers (Bands 1 to 8)
# ---------------------------------------------------------------------------

def draw_status_pill(
    draw: ImageDraw.ImageDraw,
    right_x: float,
    cy: float,
    status: str,
    font_size: int = 8,
    height: int = 13,
) -> Tuple[float, float, float, float]:
    """Draw a right-aligned status pill centered vertically on `cy`; return bbox."""
    fill, border, txt_col = STATUS_STYLE[status]
    font = get_font("sans_bold", font_size)
    tw, _ = measure_text(draw, status, font)
    pw = tw + 8
    x0 = right_x - pw
    y0 = cy - height / 2.0
    box = (x0, y0, right_x, y0 + height)
    draw.rounded_rectangle(box, radius=2, fill=fill, outline=border, width=1)
    draw_text_centered(draw, box, status, font, txt_col)
    return box


def draw_band1_topbar(
    draw: ImageDraw.ImageDraw,
    story_count: int,
    region_count: int,
    tracker: CollisionTracker,
) -> None:
    box = (0, 0, CANVAS_W, 24)
    draw.rectangle(box, fill=NAVY_TOP)
    tracker.add("bands", "band1_topbar", box)

    left_txt = "THE WORLD IN ONE DAY"
    right_txt = f"{story_count} STORIES · {region_count} REGIONS · EVERY ONE DATED SUNDAY 22 NOVEMBER 2026"

    f_l, _, _, _ = fit(draw, left_txt, "sans_bold", 12, 10, 260, 18)
    f_r, _, _, _ = fit(draw, right_txt, "sans_bold", 12, 10, 740, 18)

    lb = draw_text_aligned(draw, (MARGIN_X, 0, 280, 24), left_txt, f_l, GOLD, align="left")
    rb = draw_text_aligned(draw, (280, 0, CANVAS_W - MARGIN_X, 24), right_txt, f_r, WHITE, align="right")
    tracker.add("band1_text", "left", lb)
    tracker.add("band1_text", "right", rb)


def draw_band2_masthead(draw: ImageDraw.ImageDraw, tracker: CollisionTracker) -> None:
    title = "Sunday 22 November 2026"
    mast_box = (MARGIN_X, 25, CANVAS_W - MARGIN_X, 99)
    tracker.add("bands", "band2_masthead", mast_box)

    f_title, _, _, _ = fit(draw, title, "serif_bold", 82, 56, INNER_W - 10, 72)
    tb = draw_text_centered(draw, mast_box, title, f_title, INK_DARK)
    tracker.add("band2_text", "masthead_title", tb)

    # Double editorial rule (101..106): 3px dark ink + 1.5px crimson accent
    draw.rectangle((MARGIN_X, 101, CANVAS_W - MARGIN_X, 103), fill=RULE_DARK)
    draw.rectangle((MARGIN_X, 105, CANVAS_W - MARGIN_X, 106), fill=CRIMSON)
    tracker.add("bands", "band2_rules", (MARGIN_X, 101, CANVAS_W - MARGIN_X, 106))


def draw_band3_kpi_strip(
    draw: ImageDraw.ImageDraw,
    kpis: Sequence[Tuple[str, str, int, str]],
    tracker: CollisionTracker,
) -> None:
    y0, y1 = 109, 173
    strip_box = (MARGIN_X, y0, CANVAS_W - MARGIN_X, y1)
    draw.rectangle(strip_box, fill=KPI_BG, outline=RULE_SOFT, width=1)
    tracker.add("bands", "band3_kpi", strip_box)

    n = len(kpis)
    cell_w = INNER_W / n
    shared_baseline = y0 + 38.0  # Common typographic baseline across all 6 numerals

    for idx, (val, label, sid, region) in enumerate(kpis):
        cx0 = MARGIN_X + idx * cell_w
        cx1 = MARGIN_X + (idx + 1) * cell_w
        if idx > 0:
            draw.line((cx0, y0 + 6, cx0, y1 - 6), fill=RULE_SOFT, width=1)
        tracker.add("kpi_cells", f"kpi_{idx}", (cx0 + 1, y0 + 1, cx1 - 1, y1 - 1))

        # Big crimson serif figure (>= 44px per SPEC) aligned on shared baseline
        f_val, sz_val, _, _ = fit(draw, val, "serif_bold", 46, 44, (cx1 - cx0) - 10, 44)
        assert sz_val >= 44, f"KPI {val} shrunk below 44px ({sz_val})"
        vb = draw_text_baseline_centered(draw, cx0 + 4, cx1 - 4, shared_baseline, val, f_val, CRIMSON)

        # Bottom label (11px TrueType condensed bold) + story ref pill (#N)
        ref_txt = f"#{sid}"
        f_ref = get_font("sans_bold", 10)
        rw, _ = measure_text(draw, ref_txt, f_ref)
        pill_w = rw + 7
        max_lbl_w = (cx1 - cx0) - pill_w - 10
        f_lbl, _, lw, _ = fit(draw, label, "sans_cond_bold", 11, 9, max_lbl_w, 14)

        total_w = lw + 4 + pill_w
        start_x = cx0 + ((cx1 - cx0) - total_w) / 2.0
        lbl_box = (start_x, y0 + 46, start_x + lw, y1 - 2)
        pill_box = (start_x + lw + 4, y0 + 47, start_x + lw + 4 + pill_w, y1 - 3)

        lb = draw_text_centered(draw, lbl_box, label, f_lbl, INK_DARK)
        draw.rounded_rectangle(pill_box, radius=2, fill=REGION_COLORS[region])
        draw_text_centered(draw, pill_box, ref_txt, f_ref, WHITE)

        tracker.add(f"kpi_inner_{idx}", "val", vb)
        tracker.add(f"kpi_inner_{idx}", "lbl", lb)
        tracker.add(f"kpi_inner_{idx}", "pill", pill_box)


def draw_band4_utc_timeline(draw: ImageDraw.ImageDraw, tracker: CollisionTracker) -> None:
    y0, y1 = 177, 213
    bar_box = (MARGIN_X, y0, CANVAS_W - MARGIN_X, y1)
    draw.rectangle(bar_box, fill=NAVY_UTC)
    tracker.add("bands", "band4_utc", bar_box)

    # Left title block (12px bold gold)
    lead_w = 90
    draw.rectangle((MARGIN_X, y0, MARGIN_X + 3, y1), fill=GOLD)
    title_box = (MARGIN_X + 5, y0 + 2, MARGIN_X + lead_w, y1 - 2)
    f_t, _, _, _ = fit(draw, "DAY IN UTC", "sans_bold", 12, 10, lead_w - 8, 24)
    draw_text_centered(draw, title_box, "DAY IN UTC", f_t, GOLD)
    draw.line((MARGIN_X + lead_w + 2, y0 + 5, MARGIN_X + lead_w + 2, y1 - 5), fill=NAVY_SUB, width=1)

    # 8 equal UTC event slots (11px mono gold + 11px condensed bold white)
    slots_x0 = MARGIN_X + lead_w + 4
    slots_w = (CANVAS_W - MARGIN_X) - slots_x0
    n = len(UTC_TIMELINE)
    slot_w = slots_w / n

    for idx, (utc_time, desc) in enumerate(UTC_TIMELINE):
        sx0 = slots_x0 + idx * slot_w
        sx1 = slots_x0 + (idx + 1) * slot_w
        if idx > 0:
            draw.line((sx0, y0 + 5, sx0, y1 - 5), fill=NAVY_SUB, width=1)
        tracker.add("utc_slots", f"utc_{idx}", (sx0 + 1, y0 + 1, sx1 - 1, y1 - 1))

        f_tm, _, tw, _ = fit(draw, utc_time, "mono_bold", 11, 10, slot_w - 14, 14)
        dot_r = 2.4
        combo_w = 2 * dot_r + 4 + tw
        tx_start = sx0 + (slot_w - combo_w) / 2.0
        dot_cy = y0 + 10
        draw.ellipse(
            (tx_start, dot_cy - dot_r, tx_start + 2 * dot_r, dot_cy + dot_r),
            fill=GOLD,
        )
        draw_text_centered(
            draw,
            (tx_start + 2 * dot_r + 4, y0 + 2, tx_start + combo_w + 1, y0 + 18),
            utc_time, f_tm, GOLD,
        )

        f_ds, _, _, _ = fit(draw, desc, "sans_cond_bold", 11, 9, slot_w - 6, 15)
        draw_text_centered(draw, (sx0 + 3, y0 + 18, sx1 - 3, y1 - 2), desc, f_ds, WHITE)


def draw_band5_region_bar(
    draw: ImageDraw.ImageDraw,
    counts: Counter,
    tracker: CollisionTracker,
) -> None:
    y0, y1 = 217, 241
    tracker.add("bands", "band5_regions", (MARGIN_X, y0, CANVAS_W - MARGIN_X, y1))
    total = sum(counts.values())

    raw = [counts[r] / total * INNER_W for r in REGION_ORDER]
    widths = [int(math.floor(v)) for v in raw]
    rem = INNER_W - sum(widths)
    order_rem = sorted(range(len(raw)), key=lambda i: raw[i] - widths[i], reverse=True)
    for i in order_rem[:rem]:
        widths[i] += 1

    cx = MARGIN_X
    for r, w in zip(REGION_ORDER, widths):
        seg_box = (cx, y0, cx + w, y1)
        draw.rectangle(seg_box, fill=REGION_COLORS[r])
        if cx > MARGIN_X:
            draw.line((cx, y0, cx, y1), fill=BG_PAPER, width=1)
        tracker.add("region_bar", r, (cx + 0.5, y0, cx + w - 0.5, y1))

        lbl = f"{r} {counts[r]}"
        f_r, _, _, _ = fit(draw, lbl, "sans_cond_bold", 12, 9, w - 6, 18)
        draw_text_centered(draw, seg_box, lbl, f_r, WHITE)
        cx += w


def draw_band6_cards(
    draw: ImageDraw.ImageDraw,
    card_stories: Sequence[Story],
    tracker: CollisionTracker,
) -> None:
    assert len(card_stories) == 9
    y_start = 246
    card_w = 328
    card_h = 113
    gap_x = 8
    gap_y = 6
    y_end = y_start + 3 * card_h + 2 * gap_y  # 597
    tracker.add("bands", "band6_cards", (MARGIN_X, y_start, CANVAS_W - MARGIN_X, y_end))

    for idx, s in enumerate(card_stories):
        row = idx // 3
        col = idx % 3
        x0 = MARGIN_X + col * (card_w + gap_x)
        y0 = y_start + row * (card_h + gap_y)
        x1 = x0 + card_w
        y1 = y0 + card_h
        accent = REGION_COLORS[s.region]

        draw.rectangle((x0, y0, x1, y1), fill=CARD_BG, outline=CARD_BORDER, width=1)
        draw.rectangle((x0, y0, x1, y0 + 3), fill=accent)
        tracker.add("cards", f"card_{s.id}", (x0, y0, x1, y1))

        # Right-side 68x101 2px editorial line-art illustration
        art_box = (x1 - 73, y0 + 6, x1 - 5, y1 - 6)
        draw_card_art(draw, s, art_box, accent)
        tracker.add(f"card_{s.id}_inner", "art", art_box)

        lx0 = x0 + 7
        lx1 = art_box[0] - 6  # width = 242px

        # Top-left 30x30 solid region-colored number block
        num_box = (lx0, y0 + 7, lx0 + 30, y0 + 37)
        draw.rectangle(num_box, fill=accent)
        f_num = get_font("sans_bold", 19)
        draw_text_centered(draw, num_box, str(s.id), f_num, WHITE)
        tracker.add(f"card_{s.id}_inner", "num", num_box)

        # 2-line bold serif headline beside number block (18-19px)
        hl_x0 = num_box[2] + 6
        hl_w = lx1 - hl_x0  # 206px
        try:
            f_hl, _, hl_lines, hl_lh = fit_multiline(
                draw, s.headline, "serif_bold", 19, 17, hl_w, max_lines=2,
                line_spacing=1.08, max_height=42,
            )
        except RuntimeError:
            f_hl, _, hl_lines, hl_lh = fit_multiline(
                draw, s.headline, "serif_cond_bold", 19, 15, hl_w, max_lines=2,
                line_spacing=1.08, max_height=42,
            )
        hy = y0 + 6
        hl_bottom = hy
        for ln in hl_lines:
            tb = draw.textbbox((0, 0), ln, font=f_hl)
            draw.text((hl_x0 - tb[0], hy - tb[1]), ln, font=f_hl, fill=INK_DARK)
            hl_bottom = hy + (tb[3] - tb[1])
            hy += hl_lh
        tracker.add(f"card_{s.id}_inner", "headline", (hl_x0, y0 + 6, lx1, hl_bottom))

        # 2-line sans lead (12px darker ink) immediately below headline/number
        lead_y0 = max(num_box[3] + 7, hl_bottom + 5)
        lead_y0 = min(lead_y0, y0 + 50)
        f_ld, _, ld_lines, ld_lh = fit_multiline(
            draw, s.lead, "sans_reg", 12, 11, lx1 - lx0, max_lines=2,
            line_spacing=1.22, max_height=32,
        )
        ly = lead_y0
        ld_bottom = ly
        for ln in ld_lines:
            tb = draw.textbbox((0, 0), ln, font=f_ld)
            draw.text((lx0 - tb[0], ly - tb[1]), ln, font=f_ld, fill=INK_BODY)
            ld_bottom = ly + (tb[3] - tb[1])
            ly += ld_lh
        tracker.add(f"card_{s.id}_inner", "lead", (lx0, lead_y0, lx1, ld_bottom))

        # Bottom hairline + 10px darker meta + 9px status pill
        rule_y = y1 - 24
        draw.line((lx0, rule_y, lx1, rule_y), fill="#DFD7C8", width=1)
        foot_cy = y1 - 12
        pill_box = draw_status_pill(draw, lx1, foot_cy, s.status, font_size=9, height=15)
        tracker.add(f"card_{s.id}_inner", "status", pill_box)

        meta_txt = f"{s.location} · {s.source}"
        avail_w = pill_box[0] - lx0 - 5
        f_mt, _, mw, mh = fit(draw, meta_txt, "sans_cond_bold", 10, 8, avail_w, 14)
        mb = draw_text_aligned(draw, (lx0, rule_y + 1, pill_box[0] - 4, y1 - 2), meta_txt, f_mt, INK_MUTED, align="left")
        tracker.add(f"card_{s.id}_inner", "meta", mb)


def draw_band7a_map_and_briefs(
    draw: ImageDraw.ImageDraw,
    brief_stories: Sequence[Story],
    tracker: CollisionTracker,
) -> int:
    """
    Band 7A (y=603..839, h=236):
      - Left: 408x236 World Map with 7-region continents, 14 collision-free pins (r=9.5, 10px), & 10px legend
      - Right: 584x236 2-column numbered briefs (#10-#25, 8 rows x 2 cols, row_h=26.875px)
        with unified TrueType headlines and strict inner-row collision checks.
    """
    assert len(brief_stories) == 16
    y0, y1 = 603, 839
    tracker.add("bands", "band7a_row", (MARGIN_X, y0, CANVAS_W - MARGIN_X, y1))

    # --- Left World Map (x=12..420, w=408, h=236) ---
    mx0, mx1 = MARGIN_X, MARGIN_X + 408
    draw.rectangle((mx0, y0, mx1, y1), fill=CARD_BG, outline=CARD_BORDER, width=1)
    tracker.add("band7a_panes", "map", (mx0, y0, mx1, y1))

    # Flush-left / flush-right Map Header (h=21)
    mh = 21
    draw.rectangle((mx0, y0, mx1, y0 + mh), fill=NAVY_UTC)
    f_mh = get_font("sans_bold", 11)
    f_mr = get_font("sans_bold", 10)
    draw_text_aligned(draw, (mx0 + 8, y0, mx1 - 80, y0 + mh), "WORLD MAP · STORIES #10–#23", f_mh, GOLD, align="left")
    draw_text_aligned(draw, (mx1 - 100, y0, mx1 - 8, y0 + mh), "14 LOCATED", f_mr, WHITE, align="right")

    # Map Legend strip at bottom (h=20)
    lh = 20
    map_viewport = (mx0 + 1, y0 + mh, mx1 - 1, y1 - lh)
    vx0, vy0, vx1, vy1 = map_viewport
    draw.rectangle(map_viewport, fill="#DCE8F1")

    for lon in (-120, -60, 0, 60, 120):
        gx, _ = project_lonlat(lon, 0, map_viewport)
        draw.line((gx, vy0, gx, vy1), fill="#C7D7E4", width=1)
    for lat in (-30, 0, 30, 60):
        _, gy = project_lonlat(0, lat, map_viewport)
        draw.line((vx0, gy, vx1, gy), fill="#C7D7E4", width=1)

    for reg, poly in WORLD_POLYGONS:
        pts = [project_lonlat(lon, lat, map_viewport) for lon, lat in poly]
        draw.polygon(pts, fill=REGION_MAP_FILL[reg], outline=REGION_COLORS[reg])

    # Larger collision-resolved pins (r=9.5, 10px bold white numerals)
    pin_stories = [s for s in brief_stories if s.coords is not None]
    pin_r = 9.5
    resolved = resolve_map_pin_collisions(pin_stories, map_viewport, pin_radius=pin_r, min_gap=2.0)
    displaced_count = 0

    for s, (ax, ay), (px, py) in resolved:
        dist = math.hypot(px - ax, py - ay)
        if dist > 3.0:
            displaced_count += 1
            draw.line((ax, ay, px, py), fill=INK_DARK, width=1)
            draw.ellipse((ax - 2.2, ay - 2.2, ax + 2.2, ay + 2.2), fill=CRIMSON, outline=WHITE, width=1)

    f_pin = get_font("sans_bold", 10)
    for s, _, (px, py) in resolved:
        pin_box = (px - pin_r, py - pin_r, px + pin_r, py + pin_r)
        draw.ellipse(pin_box, fill=REGION_COLORS[s.region], outline=WHITE, width=1)
        draw_text_centered(draw, pin_box, str(s.id), f_pin, WHITE)
        tracker.add("map_pins", f"pin_{s.id}", pin_box)

    # Evenly distributed 10px TrueType Map Legend
    leg_box = (mx0 + 1, y1 - lh, mx1 - 1, y1 - 1)
    draw.rectangle(leg_box, fill="#F5EFE3")
    draw.line((mx0 + 1, y1 - lh, mx1 - 1, y1 - lh), fill=CARD_BORDER, width=1)
    f_lg = get_font("sans_cond_bold", 10)
    leg_w = (mx1 - mx0 - 12) / len(REGION_ORDER)
    for idx, r in enumerate(REGION_ORDER):
        sx0 = mx0 + 6 + idx * leg_w
        cy = y1 - lh / 2.0
        sw_box = (sx0, cy - 4.5, sx0 + 9, cy + 4.5)
        draw.rectangle(sw_box, fill=REGION_COLORS[r])
        draw_text_aligned(
            draw, (sx0 + 11, y1 - lh + 1, sx0 + leg_w, y1 - 1),
            REGION_SHORT[r], f_lg, INK_DARK, align="left",
        )

    # --- Right 2-Column Numbered Briefs (x=428..1012, w=584, h=236) ---
    bx0, bx1 = mx1 + 8, CANVAS_W - MARGIN_X  # 428..1012 (584px)
    draw.rectangle((bx0, y0, bx1, y1), fill=CARD_BG, outline=CARD_BORDER, width=1)
    tracker.add("band7a_panes", "briefs_2col", (bx0, y0, bx1, y1))

    # Flush-left / flush-right Header (h=21)
    draw.rectangle((bx0, y0, bx1, y0 + mh), fill=NAVY_UTC)
    draw_text_aligned(
        draw, (bx0 + 8, y0, bx1 - 160, y0 + mh),
        "ALSO ON SUNDAY 22 NOVEMBER · #10–#25", f_mh, GOLD, align="left",
    )
    draw_text_aligned(
        draw, (bx1 - 170, y0, bx1 - 8, y0 + mh),
        "16 WIRE BRIEFS · 2 COLS", f_mr, WHITE, align="right",
    )

    body_y0 = y0 + mh
    body_h = y1 - body_y0  # 215px -> 26.875px per row!
    row_h = body_h / 8.0
    col_w = (bx1 - bx0) / 2.0  # 292px
    mid_x = bx0 + col_w
    draw.line((mid_x, body_y0 + 3, mid_x, y1 - 3), fill=RULE_SOFT, width=1)

    for idx, s in enumerate(brief_stories):
        col = idx // 8
        row = idx % 8
        cx0 = bx0 + col * col_w + 5
        cx1 = bx0 + (col + 1) * col_w - 5
        ry0 = body_y0 + row * row_h
        ry1 = ry0 + row_h

        if row > 0:
            draw.line((cx0, ry0, cx1, ry0), fill="#E5DEC9", width=1)
        tracker.add("briefs_7a", f"brief_{s.id}", (cx0, ry0 + 0.5, cx1, ry1 - 0.5))

        # Left colored number badge
        badge = (cx0, ry0 + 3.5, cx0 + 22, ry1 - 3.5)
        draw.rectangle(badge, fill=REGION_COLORS[s.region])
        f_bn = get_font("sans_bold", 10)
        draw_text_centered(draw, badge, str(s.id), f_bn, WHITE)

        tx0 = badge[2] + 5
        tw_avail = cx1 - tx0  # ~255px

        # Unified TrueType LiberationSans-Bold headline (zero mixed typefaces)
        f_h, _, _, _ = fit(draw, s.headline, "sans_bold", 11, 9, tw_avail, 12)
        hl_box = draw_text_aligned(draw, (tx0, ry0 + 1.5, cx1, ry0 + 13.0), s.headline, f_h, INK_DARK, align="left")

        # Bottom row: 10px darker TrueType meta + 8px crisp status pill (strictly separated)
        pill_cy = ry1 - 7.0
        pill = draw_status_pill(draw, cx1, pill_cy, s.status, font_size=8, height=12)
        meta = f"{s.location} · {s.source}"
        f_m, _, _, _ = fit(draw, meta, "sans_cond_reg", 10, 8, pill[0] - tx0 - 4, 11)
        meta_box = draw_text_aligned(draw, (tx0, ry1 - 12.5, pill[0] - 4, ry1 - 1.5), meta, f_m, INK_MUTED, align="left")

        # Register inner row boxes so CollisionTracker mathematically proves zero overlap
        tracker.add(f"brief_7a_inner_{s.id}", "badge", badge)
        tracker.add(f"brief_7a_inner_{s.id}", "headline", hl_box)
        tracker.add(f"brief_7a_inner_{s.id}", "meta", meta_box)
        tracker.add(f"brief_7a_inner_{s.id}", "pill", pill)

    return displaced_count


def draw_band7b_supplemental_briefs(
    draw: ImageDraw.ImageDraw,
    extra_stories: Sequence[Story],
    tracker: CollisionTracker,
) -> None:
    """
    Band 7B (y=845..944, h=99): Full-width 3-column supplemental briefs (#26-#34),
    strictly aligned to the 3x3 main cards above (328px cols, 8px gutters, row_h=27px).
    """
    assert len(extra_stories) == 9
    y0, y1 = 845, 944
    tracker.add("bands", "band7b_extra", (MARGIN_X, y0, CANVAS_W - MARGIN_X, y1))

    hh = 18
    draw.rectangle((MARGIN_X, y0, CANVAS_W - MARGIN_X, y0 + hh), fill=NAVY_UTC)
    f_h1 = get_font("sans_bold", 11)
    f_h2 = get_font("sans_bold", 10)
    draw_text_aligned(
        draw, (MARGIN_X + 8, y0, MARGIN_X + 420, y0 + hh),
        "MORE FROM SUNDAY 22 NOVEMBER · #26–#34", f_h1, GOLD, align="left",
    )
    draw_text_aligned(
        draw, (CANVAS_W - MARGIN_X - 300, y0, CANVAS_W - MARGIN_X - 8, y0 + hh),
        "9 SUPPLEMENTAL VERIFIED DISPATCHES", f_h2, WHITE, align="right",
    )

    body_y0 = y0 + hh
    body_h = y1 - body_y0  # 81px -> 27.0px per row
    row_h = body_h / 3.0
    col_w = 328
    gap_x = 8

    for col in range(3):
        cx0 = MARGIN_X + col * (col_w + gap_x)
        cx1 = cx0 + col_w
        draw.rectangle((cx0, body_y0, cx1, y1), fill=CARD_BG, outline=CARD_BORDER, width=1)
        tracker.add("band7b_cols", f"col_{col}", (cx0, body_y0, cx1, y1))

        for row in range(3):
            s = extra_stories[col * 3 + row]
            ry0 = body_y0 + row * row_h
            ry1 = ry0 + row_h
            if row > 0:
                draw.line((cx0 + 5, ry0, cx1 - 5, ry0), fill="#E5DEC9", width=1)
            tracker.add("briefs_7b", f"brief_{s.id}", (cx0 + 4, ry0 + 0.5, cx1 - 4, ry1 - 0.5))

            badge = (cx0 + 5, ry0 + 3.5, cx0 + 27, ry1 - 3.5)
            draw.rectangle(badge, fill=REGION_COLORS[s.region])
            f_bn = get_font("sans_bold", 10)
            draw_text_centered(draw, badge, str(s.id), f_bn, WHITE)

            tx0 = badge[2] + 6
            tw_avail = cx1 - 5 - tx0

            f_hl, _, _, _ = fit(draw, s.headline, "sans_bold", 11, 10, tw_avail, 12)
            hl_box = draw_text_aligned(draw, (tx0, ry0 + 1.5, cx1 - 5, ry0 + 13.0), s.headline, f_hl, INK_DARK, align="left")

            pill_cy = ry1 - 7.0
            pill = draw_status_pill(draw, cx1 - 5, pill_cy, s.status, font_size=8, height=12)
            meta = f"{s.location} · {s.source}"
            f_mt, _, _, _ = fit(draw, meta, "sans_cond_reg", 10, 8, pill[0] - tx0 - 4, 11)
            meta_box = draw_text_aligned(draw, (tx0, ry1 - 12.5, pill[0] - 4, ry1 - 1.5), meta, f_mt, INK_MUTED, align="left")

            tracker.add(f"brief_7b_inner_{s.id}", "badge", badge)
            tracker.add(f"brief_7b_inner_{s.id}", "headline", hl_box)
            tracker.add(f"brief_7b_inner_{s.id}", "meta", meta_box)
            tracker.add(f"brief_7b_inner_{s.id}", "pill", pill)


def draw_band8_date_check(draw: ImageDraw.ImageDraw, tracker: CollisionTracker) -> None:
    """
    Band 8 (y=950..1020, h=70): 2px crimson-bordered DATE CHECK & verification legend.
    """
    x0, y0, x1, y1 = MARGIN_X, 950, CANVAS_W - MARGIN_X, 1020
    box = (x0, y0, x1, y1)
    draw.rectangle(box, fill=DATE_CHECK_BG, outline=CRIMSON, width=2)
    tracker.add("bands", "band8_date_check", box)

    # Row 1 (y=954..972): 11px crimson badge + 11px Cutoff + 10px art note
    badge_txt = "DATE CHECK — READ THIS FIRST"
    f_b = get_font("sans_bold", 11)
    bw, _ = measure_text(draw, badge_txt, f_b)
    badge_box = (x0 + 7, y0 + 4, x0 + 7 + bw + 12, y0 + 22)
    draw.rectangle(badge_box, fill=CRIMSON)
    draw_text_centered(draw, badge_box, badge_txt, f_b, WHITE)

    art_note = "Line-art: 2px editorial drawings, no faces"
    f_an, _, anw, _ = fit(draw, art_note, "sans_cond_bold", 10, 9, 250, 15)
    an_box = draw_text_aligned(draw, (x1 - 8 - anw - 4, y0 + 4, x1 - 8, y0 + 22), art_note, f_an, INK_MUTED, align="right")

    cutoff = "Cutoff: Sun 22 Nov 2026 23:59 UTC · Every story verified to this date; prior-day news excluded."
    c_x0 = badge_box[2] + 8
    c_x1 = an_box[0] - 8
    f_c, _, _, _ = fit(draw, cutoff, "sans_bold", 11, 9, c_x1 - c_x0, 15)
    c_box = draw_text_aligned(draw, (c_x0, y0 + 4, c_x1, y0 + 22), cutoff, f_c, INK_DARK, align="left")
    tracker.add("band8_row1", "badge", badge_box)
    tracker.add("band8_row1", "cutoff", c_box)
    tracker.add("band8_row1", "art_note", an_box)

    # Row 2 (y=974..993): Explicit excluded near-date stories list in crisp TrueType
    ex_prefix = "EXCLUDED: "
    ex_body = " · ".join(EXCLUDED_ITEMS)
    f_ep = get_font("sans_bold", 10)
    epw, _ = measure_text(draw, ex_prefix, f_ep)
    f_eb, _, _, _ = fit(draw, ex_body, "sans_bold", 10, 9, (x1 - x0) - 18 - epw, 15)
    draw_text_aligned(draw, (x0 + 8, y0 + 25, x0 + 8 + epw + 4, y0 + 42), ex_prefix, f_ep, CRIMSON, align="left")
    draw_text_aligned(draw, (x0 + 8 + epw, y0 + 25, x1 - 8, y0 + 42), ex_body, f_eb, INK_BODY, align="left")

    # Row 3 (y=995..1017): Hairline divider + vertically centered TAGS + status pills + credit
    draw.line((x0 + 7, y0 + 45, x1 - 7, y0 + 45), fill="#E4C6C3", width=1)
    row3_box_y0, row3_box_y1 = y0 + 47, y1 - 3
    row3_cy = (row3_box_y0 + row3_box_y1) / 2.0
    cur_x = x0 + 8
    f_lg_lbl = get_font("sans_bold", 10)
    tb_lbl = draw_text_aligned(draw, (cur_x, row3_box_y0, cur_x + 50, row3_box_y1), "TAGS:", f_lg_lbl, INK_DARK, align="left")
    cur_x = tb_lbl[2] + 6

    legend_defs = [
        ("CONFIRMED", "Multi-wire verified"),
        ("ONGOING", "Active/developing"),
        ("REPORTED", "Single/official wire"),
        ("CLAIM", "Unverified assertion"),
    ]
    f_desc = get_font("sans_cond_bold", 10)
    for st, desc in legend_defs:
        f_p = get_font("sans_bold", 8)
        pw = measure_text(draw, st, f_p)[0] + 8
        p_box = draw_status_pill(draw, cur_x + pw, row3_cy, st, font_size=8, height=14)
        cur_x = p_box[2] + 4
        db = draw_text_aligned(draw, (cur_x, row3_box_y0, cur_x + 160, row3_box_y1), desc, f_desc, INK_BODY, align="left")
        cur_x = db[2] + 10

    credit = "v5opt · 34 Stories · 1024×1024 Pure Python/Pillow"
    f_cr, _, _, _ = fit(draw, credit, "sans_cond_bold", 10, 8, x1 - 8 - cur_x, 14)
    draw_text_aligned(draw, (cur_x + 4, row3_box_y0, x1 - 8, row3_box_y1), credit, f_cr, INK_MUTED, align="right")


# ---------------------------------------------------------------------------
# 7. Main Pipeline & Deterministic Export
# ---------------------------------------------------------------------------

def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build() -> None:
    region_counts = validate_dataset(STORIES)
    kpis = extract_verified_kpis(STORIES)

    img = Image.new("RGB", (CANVAS_W, CANVAS_H), BG_PAPER)
    draw = ImageDraw.Draw(img)
    tracker = CollisionTracker(CANVAS_W, CANVAS_H)

    draw_band1_topbar(draw, len(STORIES), len(region_counts), tracker)
    draw_band2_masthead(draw, tracker)
    draw_band3_kpi_strip(draw, kpis, tracker)
    draw_band4_utc_timeline(draw, tracker)
    draw_band5_region_bar(draw, region_counts, tracker)
    draw_band6_cards(draw, STORIES[:9], tracker)
    displaced = draw_band7a_map_and_briefs(draw, STORIES[9:25], tracker)
    draw_band7b_supplemental_briefs(draw, STORIES[25:34], tracker)
    draw_band8_date_check(draw, tracker)

    # Run hard collision verification across every tracked group
    checked_pairs = tracker.assert_no_collisions()

    # Deterministic PNG save (no timestamp chunks, max lossless compression)
    img.save(ENTRY_PATH, format="PNG", optimize=True, compress_level=9)
    size_bytes = ENTRY_PATH.stat().st_size
    assert img.size == (CANVAS_W, CANVAS_H), f"Bad image size: {img.size}"
    assert size_bytes <= MAX_BYTES, f"entry.png too large: {size_bytes} > {MAX_BYTES}"

    # 300x300 crisp preview for thumbnail legibility inspection
    preview = img.resize((300, 300), Image.Resampling.LANCZOS)
    preview.save(PREVIEW_PATH, format="PNG", optimize=True, compress_level=9)

    digest = md5_file(ENTRY_PATH)
    print(f"OK | stories={len(STORIES)} | regions={dict((r, region_counts[r]) for r in REGION_ORDER)}")
    print(f"OK | kpis={[k[0] for k in kpis]}")
    print(f"OK | collision_boxes={tracker.total_registered} | checked_pairs={checked_pairs} | map_leaders={displaced}")
    print(f"OK | entry.png: {img.size[0]}x{img.size[1]}, {size_bytes:,} bytes (<= {MAX_BYTES:,}), md5={digest}")
    print(f"OK | preview-300.png: {preview.size[0]}x{preview.size[1]}, {PREVIEW_PATH.stat().st_size:,} bytes")


if __name__ == "__main__":
    build()
