#!/usr/bin/env python3
"""
The World in One Day — Sunday 22 November 2026 (v5opt)
Editorial broadsheet card-grid renderer implementing /root/makefun/ni/v5opt/SPEC.md & BRIEF.md.
Pure Python + Pillow (zero external images, zero generative models, zero network calls).
Canvas: 1024x1024 native 1:1 px, <= 1,048,576 bytes (1 MiB), byte-deterministic.
"""

from __future__ import annotations

import hashlib
import math
import os
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Canvas & Gate Constants (1024x1024 native, <= 1 MiB hard cap)
# ---------------------------------------------------------------------------
CANVAS_W = 1024
CANVAS_H = 1024
MAX_PNG_BYTES = 1024 * 1024  # 1,048,576 bytes (1 MiB) hard gate limit

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_MAIN = os.path.join(SCRIPT_DIR, "entry.png")
OUT_PREVIEW = os.path.join(SCRIPT_DIR, "preview-300.png")

# ---------------------------------------------------------------------------
# Fonts (TeX Gyre Termes editorial serif + TeX Gyre Heros crisp sans)
# ---------------------------------------------------------------------------
FONT_SERIF_BOLD = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-bold.otf"
FONT_SERIF_REG = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-regular.otf"
FONT_SERIF_ITAL = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-italic.otf"
FONT_SERIF_BI = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-bolditalic.otf"
FONT_SANS_BOLD = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheros-bold.otf"
FONT_SANS_REG = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheros-regular.otf"
FONT_SANS_ITAL = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheros-italic.otf"
FONT_SANS_CN_BOLD = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheroscn-bold.otf"
FONT_SANS_CN_REG = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheroscn-regular.otf"

_FONT_CACHE: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}


def load_font(path: str, size_px: int) -> ImageFont.FreeTypeFont:
    key = (path, int(size_px))
    f = _FONT_CACHE.get(key)
    if f is None:
        f = ImageFont.truetype(path, int(size_px))
        _FONT_CACHE[key] = f
    return f


# ---------------------------------------------------------------------------
# Editorial Newsprint Palette (Calibrated to Top-3 Archival Print Look)
# ---------------------------------------------------------------------------
BG_PAPER = (246, 242, 233)       # Warm archival newsprint
CARD_BG = (255, 254, 250)        # Crisp warm-white card face
CARD_BORDER = (196, 188, 173)    # Hairline print frame
SEC_HDR_BG = (237, 231, 219)     # Airy cream header strip for lower sections
ILLUS_BG = (244, 239, 229)       # Soft vignette ground
SCORE_BG = (239, 233, 220)       # Subtle KPI strip tint
NAVY_BAR = (16, 29, 61)          # Deep broadsheet navy (#101d3d)
UTC_BAR = (22, 37, 71)           # Dark slate-navy UTC strip
UTC_GOLD = (240, 196, 86)        # Warm editorial gold for UTC stamps
INK_BLACK = (20, 22, 28)         # Rich archival ink
INK_DARK = (40, 42, 48)          # Body ink
INK_MUTED = (76, 79, 86)         # Sharper source / secondary metadata
RULE_LIGHT = (206, 198, 184)
RULE_DARK = (24, 24, 28)
CRIMSON = (164, 34, 40)          # Archival editorial crimson
DATECHECK_BG = (253, 244, 239)   # Subtle blush tint for DATE CHECK box
WHITE = (255, 255, 255)
OCEAN_BG = (221, 233, 240)
OCEAN_GRID = (196, 213, 223)

# 7 Geographic + Global Regions (every region >= 3 stories)
REGION_ORDER = [
    "EUROPE",
    "MIDDLE EAST",
    "ASIA-PACIFIC",
    "AMERICAS",
    "AFRICA",
    "OCEANIA",
    "WORLD",
]

REGION_SHORT: Dict[str, str] = {
    "EUROPE": "EUROPE",
    "MIDDLE EAST": "MID EAST",
    "ASIA-PACIFIC": "ASIA-PAC",
    "AMERICAS": "AMERICAS",
    "AFRICA": "AFRICA",
    "OCEANIA": "OCEANIA",
    "WORLD": "WORLD",
}

REGION_COLORS: Dict[str, Tuple[int, int, int]] = {
    "EUROPE": (29, 68, 118),        # Deep navy-cobalt
    "MIDDLE EAST": (158, 38, 42),   # Brick crimson
    "ASIA-PACIFIC": (24, 104, 72),  # Forest emerald
    "AMERICAS": (102, 54, 126),     # Editorial plum
    "AFRICA": (190, 92, 22),        # Terracotta ochre
    "OCEANIA": (20, 114, 122),      # Pacific teal
    "WORLD": (72, 82, 96),          # Archival slate
}

STATUS_COLORS: Dict[str, Tuple[int, int, int]] = {
    "CONFIRMED": (27, 108, 62),     # Green
    "ONGOING": (28, 92, 146),       # Steel blue
    "REPORTED": (182, 104, 0),      # Amber
    "CLAIM": (176, 30, 38),         # Crimson
}


def tint(rgb: Tuple[int, int, int], factor: float = 0.65) -> Tuple[int, int, int]:
    """Blend rgb toward warm white by factor (0=original, 1=white)."""
    return (
        int(round(rgb[0] + (250 - rgb[0]) * factor)),
        int(round(rgb[1] + (248 - rgb[1]) * factor)),
        int(round(rgb[2] + (243 - rgb[2]) * factor)),
    )


# ---------------------------------------------------------------------------
# Verified Sunday 22 November 2026 Dataset (34 Stories, 7 Regions >= 3 each)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Story:
    num: int
    region: str
    domain: str
    title: str
    source: str
    status: str
    topic_or_city: str
    lede: str = ""
    lon: Optional[float] = None
    lat: Optional[float] = None
    kpi_metrics: Tuple[Tuple[str, str], ...] = ()


STORIES: List[Story] = [
    # -----------------------------------------------------------------------
    # TIER 1: 9 Main Illustrated Cards (3x3 Grid, #1-#9)
    #         Row 1 (#1-#3): Lead cards (128px tall, 21px headlines)
    #         Rows 2-3 (#4-#9): Feature cards (119px tall, 19px headlines)
    # -----------------------------------------------------------------------
    Story(
        1, "WORLD", "Climate",
        "COP31 collapses in Antalya without a deal",
        "Reuters, AFP, BBC", "CONFIRMED", "CLIMATE SUMMIT",
        "Nearly 200 nations deadlock past 03:00 UTC over fossil fuels and a $120bn floor.",
        kpi_metrics=(("$120bn", "COP31 FINANCE FLOOR"),),
    ),
    Story(
        2, "EUROPE", "Military",
        "Russia fires 186 drones; 161 downed",
        "Ukr. Air Force, BBC", "CONFIRMED", "UKRAINE WAR",
        "Overnight wave of 72 jet UAVs batters Dymer flats and triggers grid blackouts.",
        kpi_metrics=(("186", "DRONES AT UKRAINE"), ("161", "DRONES DOWNED")),
    ),
    Story(
        3, "AFRICA", "Military",
        "Russian warship Merkury sinks in Benghazi",
        "Reuters, Al Jazeera", "CONFIRMED", "MARITIME STRIKE",
        "Corvette capsizes after suspected sea-drone strike in Libya; Maltese ship hit.",
    ),
    Story(
        4, "MIDDLE EAST", "Military",
        "Bahrain: Iran strike hurts 2; IRGC claims hit",
        "MEE, Times of Israel", "CLAIM", "GULF CRISIS",
        "Manama cites industrial fire near Sitra; Iran alleges US Patriot radar struck.",
    ),
    Story(
        5, "ASIA-PACIFIC", "Politics",
        "Hong Kong polls hit 98.8% with 856 hopefuls",
        "info.gov.hk, China Daily", "CONFIRMED", "ELECTIONS",
        "Election Committee fills 723 seats as 5,640 electors vote 01:00–10:00 UTC.",
        kpi_metrics=(("856", "HK POLL CANDIDATES"),),
    ),
    Story(
        6, "WORLD", "Tech",
        "BepiColombo reaches Mercury after 8 yrs",
        "BBC, ESA", "CONFIRMED", "DEEP SPACE",
        "European-Japanese spacecraft enters orbit to map the planet's crust and field.",
    ),
    Story(
        7, "AMERICAS", "Politics",
        "Mexico arrests FBI Most Wanted cartel chief",
        "BBC, Reuters", "CONFIRMED", "SECURITY",
        "Special forces seize Sinaloa boss Fausto Meza Flores after an intense shootout.",
    ),
    Story(
        8, "OCEANIA", "Sports",
        "India posts record 720/9; NZ holds draw",
        "ESPN, Jamaica Observer", "CONFIRMED", "CRICKET",
        "Visitors shatter New Zealand's Test record before hosts bat 120 overs to draw.",
        kpi_metrics=(("720/9", "INDIA TEST RECORD"),),
    ),
    Story(
        9, "ASIA-PACIFIC", "Disaster",
        "Indonesia plant fire kills 3; 36 still missing",
        "AFP, BBC, France 24", "ONGOING", "DISASTER",
        "Rescuers comb gutted Banten confectionery plant while four injured recover.",
    ),

    # -----------------------------------------------------------------------
    # TIER 2: 16 Two-Column Dispatches Beside World Map (#10-#25)
    #         Items #10-#23 (14 stories) are pinned on the Left World Map!
    # -----------------------------------------------------------------------
    Story(
        10, "EUROPE", "Politics",
        "Fico refuses EU €45bn loan to Ukraine",
        "Reuters, Kyiv Post", "CONFIRMED", "BRATISLAVA",
        lon=17.1, lat=48.1,
    ),
    Story(
        11, "MIDDLE EAST", "Military",
        "Gaza toll hits 74,742; Hamas seeks talks",
        "WAFA, Anadolu", "ONGOING", "GAZA",
        lon=34.5, lat=31.5,
        kpi_metrics=(("74,742", "GAZA DEATH TOLL"),),
    ),
    Story(
        12, "AMERICAS", "Sports",
        "Wembanyama posts historic 50-pt, 19-reb win",
        "CBS, KSAT", "CONFIRMED", "SAN ANTONIO",
        lon=-98.5, lat=29.4,
    ),
    Story(
        13, "AMERICAS", "Disaster",
        "Brazil storm kills 5, hurts 250+ in south",
        "AFP", "CONFIRMED", "TUPANCIRETÃ",
        lon=-53.8, lat=-29.1,
    ),
    Story(
        14, "ASIA-PACIFIC", "Tech",
        "S. Korea ed chief quits over AI exam chaos",
        "AFP, BBC", "CONFIRMED", "SEOUL",
        lon=127.0, lat=37.6,
    ),
    Story(
        15, "AFRICA", "Military",
        "RSF drones hit Khartoum homes & UN, 4 dead",
        "Al Jazeera", "REPORTED", "KHARTOUM",
        lon=32.5, lat=15.6,
    ),
    Story(
        16, "AFRICA", "Disaster",
        "Nigeria mourners' boat capsizes, 24 dead",
        "AllAfrica", "CONFIRMED", "BAYELSA",
        lon=6.1, lat=4.8,
    ),
    Story(
        17, "AFRICA", "Politics",
        "Kenya's Ruto & DRC's Tshisekedi restore ties",
        "Pan African Visions", "CONFIRMED", "OYO, CONGO",
        lon=15.9, lat=-1.2,
    ),
    Story(
        18, "OCEANIA", "Politics",
        "Albanese backs Bowen after COP31 uproar",
        "Guardian AU", "CONFIRMED", "CANBERRA",
        lon=149.1, lat=-35.3,
    ),
    Story(
        19, "OCEANIA", "Climate",
        "Pope urges aid as drought grips 22 PNG zones",
        "Crux, CathNews", "ONGOING", "PORT MORESBY",
        lon=147.2, lat=-9.4,
    ),
    Story(
        20, "EUROPE", "Sports",
        "Alcaraz beats Zverev for 1st ATP Finals title",
        "Reuters, Guardian", "CONFIRMED", "TURIN",
        lon=7.7, lat=45.1,
    ),
    Story(
        21, "EUROPE", "Disaster",
        "12,000 evacuated at UK arena over gas scare",
        "BBC, SBS", "REPORTED", "MANCHESTER",
        lon=-2.2, lat=53.5,
    ),
    Story(
        22, "ASIA-PACIFIC", "Culture",
        "Japan marks Shuri Castle hall rebuild in Naha",
        "Wash. Post, JT", "CONFIRMED", "OKINAWA",
        lon=127.7, lat=26.2,
    ),
    Story(
        23, "MIDDLE EAST", "Politics",
        "Lebanon marks 83rd Independence Day",
        "NPR, L'Orient", "ONGOING", "BEIRUT",
        lon=35.5, lat=33.9,
    ),
    Story(
        24, "EUROPE", "Sports",
        "Márquez clinches 8th MotoGP crown",
        "AP", "CONFIRMED", "PORTIMÃO",
    ),
    Story(
        25, "AMERICAS", "Sports",
        "Verstappen wins Las Vegas GP over McLarens",
        "Guardian, National", "CONFIRMED", "LAS VEGAS",
    ),

    # -----------------------------------------------------------------------
    # TIER 3: 9 Full-Width Three-Column Wire Briefs (#26-#34)
    # -----------------------------------------------------------------------
    Story(
        26, "EUROPE", "Military",
        "Russia-bound ship towed after Gulf of Finland hit",
        "BBC, Finnish DF", "REPORTED", "GULF OF FINLAND",
    ),
    Story(
        27, "EUROPE", "Sports",
        "Liverpool routs Man Utd 4-0 in Pochettino debut",
        "Guardian, BBC", "CONFIRMED", "LIVERPOOL",
    ),
    Story(
        28, "MIDDLE EAST", "Military",
        "Saudi coalition intercepts Houthi missiles & UAVs",
        "Anadolu, ISW", "REPORTED", "RIYADH",
    ),
    Story(
        29, "MIDDLE EAST", "Politics",
        "Israeli rivals slam West Bank settler arson raids",
        "Guardian", "ONGOING", "WEST BANK",
    ),
    Story(
        30, "AMERICAS", "Economy",
        "Software fault delays 1,000+ Delta flights",
        "AP, The Hindu", "CONFIRMED", "ATLANTA",
    ),
    Story(
        31, "AMERICAS", "Military",
        "US Army to detonate Iowa munitions despite court",
        "BBC", "CONFIRMED", "IOWA",
    ),
    Story(
        32, "ASIA-PACIFIC", "Economy",
        "Bangladesh garment clashes; 95 BGB platoons sent",
        "Business Standard", "ONGOING", "GAZIPUR",
    ),
    Story(
        33, "ASIA-PACIFIC", "Tech",
        "Pakistan's first astronaut departs for Tiangong",
        "APP, Arab News", "CONFIRMED", "ISLAMABAD",
    ),
    Story(
        34, "WORLD", "Economy",
        "WTO flags record $1.5tn export & $5.4tn import curbs",
        "WTO, SunStar", "CONFIRMED", "GENEVA",
    ),
]

# Chronological 22 Nov 2026 UTC Timeline (8 equal-width slots, crisp 2-word labels)
UTC_TIMELINE: List[Tuple[str, str]] = [
    ("01:00", "HK polls open"),
    ("01:25", "Cartel arrest"),
    ("03:00", "COP31 closes"),
    ("04:00", "Vegas GP"),
    ("09:20", "SK chief quits"),
    ("10:44", "At Mercury"),
    ("14:05", "Banten fire"),
    ("20:43", "Alcaraz wins"),
]


def extract_kpi_strip(stories: Sequence[Story]) -> List[Tuple[str, str, int]]:
    """
    Programmatically derive the 6 big-number KPI cells directly from STORIES,
    asserting every displayed figure literally appears in its source story text.
    """
    kpis: List[Tuple[str, str, int]] = []
    desired_order = [2, 1, 11, 5, 8]
    story_by_num = {s.num: s for s in stories}
    for snum in desired_order:
        st = story_by_num[snum]
        corpus = f"{st.title} {st.lede}"
        for val, lbl in st.kpi_metrics:
            if val not in corpus:
                raise RuntimeError(
                    f"KPI value {val!r} not found verbatim in Story #{st.num}: {corpus!r}"
                )
            kpis.append((val, lbl, st.num))
    if len(kpis) != 6:
        raise RuntimeError(f"Expected exactly 6 KPI items extracted from STORIES, got {len(kpis)}")
    return kpis


# ---------------------------------------------------------------------------
# Strict Fit & Collision Detection Engine (Mandatory Hard Constraints)
# ---------------------------------------------------------------------------
_MEASURE_IMG = Image.new("RGB", (16, 16))
_MEASURE_DRAW = ImageDraw.Draw(_MEASURE_IMG)


def _text_width(text: str, font: ImageFont.FreeTypeFont) -> int:
    if not text:
        return 0
    bb = _MEASURE_DRAW.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


def _wrap_words(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> List[str]:
    words = text.split()
    if not words:
        return [""]
    lines: List[str] = []
    cur = words[0]
    for w in words[1:]:
        cand = cur + " " + w
        if _text_width(cand, font) <= max_w:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def fit(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_w: int,
    max_lines: int,
    max_h: Optional[int] = None,
    line_spacing: float = 1.12,
    min_px: int = 8,
) -> Tuple[ImageFont.FreeTypeFont, List[str], int, int]:
    """
    Mandatory fit(text, font, max_w, max_lines):
    Measures bounding box; if overflowing max_w / max_lines / max_h, shrinks
    font size step by step (-1px per step, floor 8px).
    Raises ValueError if still overflowing at floor.
    """
    font_path = getattr(font, "path", None)
    if not font_path:
        raise ValueError("fit() requires a TrueType/OpenType FreeTypeFont")
    start_size = int(round(font.size))

    for size in range(start_size, min_px - 1, -1):
        cand_font = load_font(font_path, size)
        if max_lines == 1:
            lines = [text]
        else:
            lines = _wrap_words(text, cand_font, max_w)
        if len(lines) > max_lines:
            continue
        widths = [_text_width(ln, cand_font) for ln in lines]
        if any(w > max_w for w in widths):
            continue
        ascent, descent = cand_font.getmetrics()
        line_h = ascent + descent
        step = max(1, int(round(size * line_spacing)))
        if len(lines) == 1:
            bb = _MEASURE_DRAW.textbbox((0, 0), lines[0], font=cand_font)
            total_h = bb[3] - bb[1]
        else:
            last_bb = _MEASURE_DRAW.textbbox((0, 0), lines[-1], font=cand_font)
            first_bb = _MEASURE_DRAW.textbbox((0, 0), lines[0], font=cand_font)
            total_h = (len(lines) - 1) * step + (last_bb[3] - first_bb[1])
            total_h = max(total_h, (len(lines) - 1) * step + int(line_h * 0.82))
        if max_h is not None and total_h > max_h:
            continue
        return cand_font, lines, step, total_h

    raise ValueError(
        f"fit() failed: text={text!r} cannot fit in max_w={max_w}, "
        f"max_lines={max_lines}, max_h={max_h} even at min size {min_px}px"
    )


BoxRecord = Tuple[str, Tuple[int, int, int, int]]


def no_overlap(boxes: Sequence[BoxRecord]) -> int:
    """
    Mandatory pairwise AABB collision check across ALL text, illustration,
    badge, status pill, and map pin blocks. Raises RuntimeError on any overlap.
    """
    n = len(boxes)
    collisions: List[str] = []
    for i in range(n):
        name_a, (ax0, ay0, ax1, ay1) = boxes[i]
        if ax1 <= ax0 or ay1 <= ay0:
            raise RuntimeError(f"Degenerate box {name_a}: {(ax0, ay0, ax1, ay1)}")
        for j in range(i + 1, n):
            name_b, (bx0, by0, bx1, by1) = boxes[j]
            if ax0 < bx1 and ax1 > bx0 and ay0 < by1 and ay1 > by0:
                ix0, iy0 = max(ax0, bx0), max(ay0, by0)
                ix1, iy1 = min(ax1, bx1), min(ay1, by1)
                collisions.append(
                    f"{name_a} {(ax0, ay0, ax1, ay1)} <-> {name_b} {(bx0, by0, bx1, by1)} "
                    f"(overlap {(ix1 - ix0)}x{(iy1 - iy0)}px)"
                )
    if collisions:
        sample = "\n  ".join(collisions[:12])
        raise RuntimeError(f"Collision detected ({len(collisions)} pairs):\n  {sample}")
    return n * (n - 1) // 2


def draw_fitted_text(
    draw: ImageDraw.ImageDraw,
    boxes: List[BoxRecord],
    label: str,
    text: str,
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    max_w: int,
    max_lines: int,
    fill: Tuple[int, int, int],
    align: str = "left",
    valign: str = "top",
    box_h: Optional[int] = None,
    line_spacing: float = 1.12,
    min_px: int = 8,
    register: bool = True,
    font_log: Optional[List[Tuple[str, int, int, int]]] = None,
) -> Tuple[int, int, int, int]:
    """Fit text via fit(), render crisp lines, and register exact rendered bbox."""
    req_size = int(round(font.size))
    fitted_font, lines, step, _ = fit(
        text, font, max_w=max_w, max_lines=max_lines, max_h=box_h,
        line_spacing=line_spacing, min_px=min_px,
    )
    if font_log is not None:
        font_log.append((label, req_size, int(round(fitted_font.size)), len(lines)))

    rel_bboxes = [draw.textbbox((0, i * step), ln, font=fitted_font) for i, ln in enumerate(lines)]
    min_top = min(bb[1] for bb in rel_bboxes)
    max_bot = max(bb[3] for bb in rel_bboxes)
    ink_h = max_bot - min_top

    if valign == "middle" and box_h is not None:
        y_base = y + (box_h - ink_h) // 2 - min_top
    elif valign == "bottom" and box_h is not None:
        y_base = y + box_h - ink_h - min_top
    else:
        y_base = y - min_top

    x0_all, y0_all, x1_all, y1_all = 10**9, 10**9, -10**9, -10**9
    for i, ln in enumerate(lines):
        bb0 = draw.textbbox((0, 0), ln, font=fitted_font)
        lw = bb0[2] - bb0[0]
        if align == "center":
            lx = x + (max_w - lw) // 2 - bb0[0]
        elif align == "right":
            lx = x + max_w - lw - bb0[0]
        else:
            lx = x - bb0[0]
        ly = y_base + i * step
        draw.text((lx, ly), ln, font=fitted_font, fill=fill)
        actual_bb = draw.textbbox((lx, ly), ln, font=fitted_font)
        x0_all = min(x0_all, actual_bb[0])
        y0_all = min(y0_all, actual_bb[1])
        x1_all = max(x1_all, actual_bb[2])
        y1_all = max(y1_all, actual_bb[3])

    final_bb = (int(x0_all), int(y0_all), int(x1_all), int(y1_all))
    if register:
        boxes.append((label, final_bb))
    return final_bb


def draw_baseline_kpi(
    draw: ImageDraw.ImageDraw,
    boxes: List[BoxRecord],
    label: str,
    text: str,
    font: ImageFont.FreeTypeFont,
    cx: int,
    baseline_y: int,
    max_w: int,
    fill: Tuple[int, int, int],
    min_px: int = 44,
    font_log: Optional[List[Tuple[str, int, int, int]]] = None,
) -> Tuple[int, int, int, int]:
    """Render single-line KPI locked to a shared typographic baseline (anchor='ms')."""
    req_size = int(round(font.size))
    fitted_font, lines, _, _ = fit(text, font, max_w=max_w, max_lines=1, min_px=min_px)
    if font_log is not None:
        font_log.append((label, req_size, int(round(fitted_font.size)), 1))
    ln = lines[0]
    draw.text((cx, baseline_y), ln, font=fitted_font, fill=fill, anchor="ms")
    bb = draw.textbbox((cx, baseline_y), ln, font=fitted_font, anchor="ms")
    final_bb = (int(bb[0]), int(bb[1]), int(bb[2]), int(bb[3]))
    boxes.append((label, final_bb))
    return final_bb


# ---------------------------------------------------------------------------
# Bespoke Card Line-Art Illustrations (2px stroke, NO faces, 9 scenes #1-#9)
# Unified sky + horizon editorial framing across all 9 vignettes
# ---------------------------------------------------------------------------
def _draw_wave(
    draw: ImageDraw.ImageDraw,
    x0: int,
    x1: int,
    y: int,
    amp: float,
    cycles: float,
    color: Tuple[int, int, int],
    width: int,
) -> None:
    pts = []
    steps = 36
    for i in range(steps + 1):
        t = i / steps
        px = x0 + (x1 - x0) * t
        py = y + math.sin(t * cycles * 2 * math.pi) * amp
        pts.append((px, py))
    draw.line(pts, fill=color, width=width, joint="curve")


def draw_card_illustration(
    draw: ImageDraw.ImageDraw,
    story_num: int,
    rect: Tuple[int, int, int, int],
    accent: Tuple[int, int, int],
) -> None:
    """
    Clean editorial 2px line-art vignettes (zero faces) with unified sky + horizon
    colour framing so every card pops with broadsheet contrast at 300px & 1024px.
    """
    x0, y0, x1, y1 = rect
    w = x1 - x0
    h = y1 - y0
    cx = (x0 + x1) // 2
    lw = 2
    lw_thin = 1
    soft_accent = tint(accent, 0.72)
    mid_accent = tint(accent, 0.36)
    ink = INK_BLACK

    if story_num == 1:
        # COP31 Antalya: Deep slate-teal plenary sky + warm table horizon + globe & cracked treaty
        hy = y0 + int(h * 0.54)
        draw.rectangle(rect, fill=(28, 56, 68), outline=CARD_BORDER, width=1)
        draw.rectangle((x0 + 1, hy, x1 - 1, y1 - 1), fill=(224, 213, 194))
        draw.line((x0 + 1, hy, x1 - 1, hy), fill=ink, width=lw)
        # Wireframe globe rising behind summit desk
        r = 21
        gy = y0 + int(h * 0.30)
        draw.ellipse((cx - r, gy - r, cx + r, gy + r), fill=(238, 245, 246), outline=WHITE, width=lw)
        draw.ellipse((cx - r // 2, gy - r, cx + r // 2, gy + r), outline=(28, 86, 98), width=lw_thin)
        draw.line((cx, gy - r, cx, gy + r), fill=(28, 86, 98), width=lw_thin)
        draw.line((cx - r, gy, cx + r, gy), fill=(28, 86, 98), width=lw_thin)
        # Fractured Antalya Pact treaty on desk
        px0, py0, px1, py1 = cx - 21, hy + 5, cx + 21, y1 - 7
        draw.rectangle((px0, py0, px1, py1), fill=WHITE, outline=ink, width=lw)
        for frac in (0.30, 0.52, 0.74):
            ly = py0 + int((py1 - py0) * frac)
            draw.line((px0 + 5, ly, px1 - 5, ly), fill=INK_MUTED, width=lw_thin)
        draw.line([(px0 + 5, py0 + 4), (px1 - 5, py1 - 4)], fill=CRIMSON, width=lw)
        draw.line([(px1 - 5, py0 + 4), (px0 + 5, py1 - 4)], fill=CRIMSON, width=lw)

    elif story_num == 2:
        # Russia 186 drones: Deep navy night sky + gold delta UAV + lit Dymer apartment block
        draw.rectangle(rect, fill=(22, 33, 55), outline=CARD_BORDER, width=1)
        sky_light = (234, 239, 247)
        for sx, sy in [(x0 + 10, y0 + 10), (x1 - 12, y0 + 16), (cx + 16, y0 + 8)]:
            draw.ellipse((sx - 1, sy - 1, sx + 1, sy + 1), fill=UTC_GOLD)
        dy = y0 + int(h * 0.23)
        draw.polygon(
            [(cx, dy - 12), (cx + 20, dy + 7), (cx, dy + 2), (cx - 20, dy + 7)],
            fill=UTC_GOLD, outline=sky_light, width=lw,
        )
        draw.arc((x0 + 6, y0 + 14, x1 - 6, y0 + int(h * 0.62)), 200, 340, fill=CRIMSON, width=lw)
        bx0, by0, bx1, by1 = x0 + 11, y0 + int(h * 0.44), x1 - 11, y1 - 6
        draw.rectangle((bx0, by0, bx1, by1), fill=(236, 232, 222), outline=sky_light, width=lw)
        for r_i in range(4):
            for c_i in range(3):
                wx = bx0 + 5 + c_i * 13
                wy_i = by0 + 5 + r_i * 12
                fill_w = CRIMSON if (r_i == 0 and c_i == 1) else (44, 62, 92)
                draw.rectangle((wx, wy_i, wx + 8, wy_i + 8), fill=fill_w, outline=ink, width=lw_thin)

    elif story_num == 3:
        # Russian corvette Merkury ablaze & listing in Benghazi
        wy = y0 + int(h * 0.68)
        draw.rectangle(rect, fill=(226, 214, 198), outline=CARD_BORDER, width=1)
        draw.rectangle((x0 + 1, wy - 2, x1 - 1, y1 - 1), fill=(46, 94, 128))
        # Angled smoke plume cleanly inside bounds
        for sx_off, sy_off, rad in [(-9, 0.17, 10), (0, 0.27, 12), (-3, 0.39, 9)]:
            draw.ellipse(
                (cx + sx_off - rad, y0 + int(h * sy_off) - rad,
                 cx + sx_off + rad, y0 + int(h * sy_off) + rad),
                fill=(96, 92, 88), outline=ink, width=lw_thin,
            )
        # Fire on deck
        draw.polygon(
            [(cx - 10, wy - 10), (cx - 4, wy - 28), (cx + 2, wy - 15),
             (cx + 8, wy - 25), (cx + 13, wy - 10)],
            fill=CRIMSON, outline=ink, width=lw_thin,
        )
        # Crisp dark listing warship silhouette
        draw.polygon(
            [(x0 + 7, wy - 11), (x1 - 7, wy - 4),
             (x1 - 12, wy + 7), (x0 + 12, wy + 2)],
            fill=(42, 48, 58), outline=WHITE, width=lw,
        )
        draw.rectangle((cx - 11, wy - 20, cx + 6, wy - 9), fill=(68, 76, 88), outline=ink, width=lw)
        draw.line((cx - 3, wy - 20, cx - 3, wy - 31), fill=ink, width=lw)
        _draw_wave(draw, x0 + 6, x1 - 6, wy + 12, 2.5, 2.2, WHITE, lw)
        _draw_wave(draw, x0 + 8, x1 - 8, wy + 22, 2.0, 2.0, (186, 214, 232), lw_thin)

    elif story_num == 4:
        # Bahrain / IRGC claim: Dusk crimson-slate Gulf sky + desert horizon + sweeping radar
        hy = y0 + int(h * 0.78)
        draw.rectangle(rect, fill=(44, 28, 38), outline=CARD_BORDER, width=1)
        draw.rectangle((x0 + 1, hy, x1 - 1, y1 - 1), fill=(212, 186, 146))
        draw.line((x0 + 1, hy, x1 - 1, hy), fill=ink, width=lw)
        # Concentric radar sweep arcs filling upper/mid sky
        rx, ry = cx + 6, hy - 14
        for rr in (28, 40, 52):
            draw.arc((rx - rr, ry - rr, rx + rr, ry + rr), 185, 258, fill=UTC_GOLD, width=lw_thin)
        # Incoming trajectory + starburst top-left
        bx, by = x0 + 16, y0 + 22
        draw.line((x0 + 5, y0 + 10, bx, by), fill=CRIMSON, width=lw)
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            draw.line(
                (bx + math.cos(rad) * 3, by + math.sin(rad) * 3,
                 bx + math.cos(rad) * 9, by + math.sin(rad) * 9),
                fill=UTC_GOLD, width=lw_thin,
            )
        # Bold radar dish & tripod anchored on horizon
        draw.pieslice((rx - 18, ry - 18, rx + 18, ry + 18), 140, 320, fill=WHITE, outline=ink, width=lw)
        draw.line((rx, ry, rx - 10, ry - 14), fill=ink, width=lw)
        draw.ellipse((rx - 13, ry - 17, rx - 7, ry - 11), fill=CRIMSON, outline=WHITE, width=lw_thin)
        draw.line((rx, ry + 4, rx - 13, hy + 8), fill=ink, width=lw)
        draw.line((rx, ry + 4, rx + 13, hy + 8), fill=ink, width=lw)

    elif story_num == 5:
        # Hong Kong polls 98.8%: Rich emerald wash + crisp ballot box + 98.8% gauge
        hy = y0 + int(h * 0.42)
        draw.rectangle(rect, fill=(24, 78, 56), outline=CARD_BORDER, width=1)
        draw.rectangle((x0 + 1, hy, x1 - 1, y1 - 1), fill=ILLUS_BG)
        draw.line((x0 + 1, hy, x1 - 1, hy), fill=ink, width=lw_thin)
        bx0, by0, bx1, by1 = x0 + 10, y0 + int(h * 0.44), x1 - 10, y1 - 9
        # Crisp white ballot entering slot
        draw.polygon(
            [(cx - 12, y0 + 11), (cx + 14, y0 + 8), (cx + 16, by0 + 2), (cx - 10, by0 + 2)],
            fill=WHITE, outline=ink, width=lw,
        )
        draw.line([(cx - 4, y0 + 25), (cx, y0 + 31), (cx + 9, y0 + 17)], fill=accent, width=lw)
        draw.rectangle((bx0, by0, bx1, by1), fill=WHITE, outline=ink, width=lw)
        draw.rectangle((bx0 + 3, by0 + 3, bx1 - 3, by0 + 11), fill=soft_accent, outline=ink, width=lw_thin)
        draw.line((cx - 13, by0 + 7, cx + 13, by0 + 7), fill=ink, width=lw)
        bar_y0, bar_y1 = by0 + 21, by1 - 9
        draw.rectangle((bx0 + 6, bar_y0, bx1 - 6, bar_y1), fill=ILLUS_BG, outline=ink, width=lw_thin)
        fill_x1 = bx0 + 6 + int((bx1 - bx0 - 12) * 0.96)
        draw.rectangle((bx0 + 6, bar_y0, fill_x1, bar_y1), fill=accent)

    elif story_num == 6:
        # BepiColombo reaches Mercury: Deep space starfield + gold probe + cratered Mercury
        draw.rectangle(rect, fill=(20, 30, 52), outline=CARD_BORDER, width=1)
        sky_light = (234, 239, 247)
        for sx, sy in [(x0 + 10, y0 + 12), (x1 - 11, y0 + 12), (x0 + 13, y1 - 14), (x1 - 14, y1 - 12)]:
            draw.ellipse((sx - 1, sy - 1, sx + 1, sy + 1), fill=sky_light)
        draw.arc((x0 + 6, y0 + 18, x1 - 6, y1 - 16), 320, 220, fill=UTC_GOLD, width=lw_thin)
        mr = 18
        my = y0 + int(h * 0.65)
        draw.ellipse((cx - mr, my - mr, cx + mr, my + mr), fill=(184, 175, 162), outline=sky_light, width=lw)
        for dx, dy, cr in [(-6, -4, 4), (5, 3, 5), (-2, 8, 3)]:
            draw.ellipse((cx + dx - cr, my + dy - cr, cx + dx + cr, my + dy + cr), outline=(92, 86, 78), width=lw_thin)
        py = y0 + int(h * 0.26)
        draw.rectangle((cx - 22, py - 4, cx - 7, py + 4), fill=(62, 134, 198), outline=sky_light, width=lw_thin)
        draw.rectangle((cx + 7, py - 4, cx + 22, py + 4), fill=(62, 134, 198), outline=sky_light, width=lw_thin)
        draw.rectangle((cx - 7, py - 7, cx + 7, py + 7), fill=UTC_GOLD, outline=sky_light, width=lw)
        draw.line((cx, py + 7, cx, py + 15), fill=sky_light, width=lw_thin)

    elif story_num == 7:
        # Mexico cartel arrest: Dusk indigo Sierra sky + mountain ridge + federal shield + searchlight
        hy = y0 + int(h * 0.72)
        draw.rectangle(rect, fill=(46, 32, 68), outline=CARD_BORDER, width=1)
        # Searchlight cone from bottom-left
        draw.polygon([(x0 + 6, hy), (x1 - 8, y0 + 8), (x1 - 26, y0 + 8)], fill=(76, 62, 108))
        # Sierra mountain silhouette
        draw.polygon(
            [(x0 + 1, y1 - 1), (x0 + 1, hy + 4), (x0 + 18, hy - 12),
             (cx + 4, hy + 2), (x1 - 14, hy - 16), (x1 - 1, hy - 2), (x1 - 1, y1 - 1)],
            fill=(28, 22, 42), outline=WHITE, width=lw_thin,
        )
        # Bold white law-enforcement shield + crimson target lock
        sy0, sy1 = y0 + 14, hy - 6
        shield = [
            (cx, sy0), (x1 - 11, sy0 + 8), (x1 - 13, sy0 + 32),
            (cx, sy1), (x0 + 13, sy0 + 32), (x0 + 11, sy0 + 8),
        ]
        draw.polygon(shield, fill=WHITE, outline=ink, width=lw)
        scy = (sy0 + sy1) // 2
        draw.ellipse((cx - 10, scy - 10, cx + 10, scy + 10), outline=accent, width=lw)
        draw.line((cx - 14, scy, cx + 14, scy), fill=CRIMSON, width=lw)
        draw.line((cx, scy - 14, cx, scy + 14), fill=CRIMSON, width=lw)

    elif story_num == 8:
        # India 720/9 & NZ draw: Sky + lush emerald outfield + cream pitch + stumps + red ball
        sky_y = y0 + int(h * 0.36)
        pitch_y = y0 + int(h * 0.72)
        draw.rectangle(rect, fill=(192, 224, 232), outline=CARD_BORDER, width=1)
        draw.rectangle((x0 + 1, sky_y, x1 - 1, y1 - 1), fill=(48, 128, 84))
        # Perspective cream pitch strip
        draw.polygon(
            [(cx - 14, sky_y + 12), (cx + 14, sky_y + 12), (x1 - 5, y1 - 1), (x0 + 5, y1 - 1)],
            fill=(232, 220, 192), outline=ink, width=lw_thin,
        )
        # Bold 3 stumps + crimson bails
        base_y = y1 - 11
        top_y = y0 + int(h * 0.40)
        draw.line((x0 + 10, base_y, x1 - 10, base_y), fill=WHITE, width=lw)
        for sx in (cx - 11, cx, cx + 11):
            draw.line((sx, top_y, sx, base_y), fill=ink, width=lw)
        draw.line((cx - 12, top_y - 2, cx - 1, top_y - 2), fill=CRIMSON, width=lw)
        draw.line((cx + 1, top_y - 2, cx + 12, top_y - 2), fill=CRIMSON, width=lw)
        # Ball trajectory arc + cricket ball in upper sky
        draw.arc((x0 + 6, y0 + 10, x1 - 6, y0 + int(h * 0.50)), 195, 345, fill=ink, width=lw_thin)
        bx, by = cx + 13, y0 + 21
        draw.ellipse((bx - 8, by - 8, bx + 8, by + 8), fill=CRIMSON, outline=ink, width=lw)
        draw.arc((bx - 6, by - 6, bx + 6, by + 6), 30, 150, fill=WHITE, width=lw_thin)

    elif story_num == 9:
        # Indonesia plant fire: Dusk smoke sky + dark sawtooth factory + crimson blaze
        fy = y0 + int(h * 0.62)
        draw.rectangle(rect, fill=(58, 42, 40), outline=CARD_BORDER, width=1)
        # Layered billowing smoke clouds
        for sx_off, sy_off, rad in [(-11, 0.16, 11), (3, 0.24, 13), (-3, 0.36, 10)]:
            draw.ellipse(
                (cx + sx_off - rad, y0 + int(h * sy_off) - rad,
                 cx + sx_off + rad, y0 + int(h * sy_off) + rad),
                fill=(124, 114, 110), outline=(228, 222, 214), width=lw_thin,
            )
        # Bright blaze peaks
        draw.polygon(
            [(cx - 14, fy + 2), (cx - 6, fy - 24), (cx + 1, fy - 12),
             (cx + 8, fy - 22), (cx + 15, fy + 2)],
            fill=CRIMSON, outline=UTC_GOLD, width=lw_thin,
        )
        # Crisp white-outlined dark sawtooth factory
        bx0, bx1, by1 = x0 + 7, x1 - 7, y1 - 6
        draw.polygon(
            [(bx0, by1), (bx0, fy + 4), (bx0 + 16, fy - 5), (bx0 + 16, fy + 4),
             (bx0 + 32, fy - 5), (bx0 + 32, fy + 4), (bx1, fy - 5), (bx1, by1)],
            fill=(238, 232, 222), outline=ink, width=lw,
        )
        for wi in range(3):
            wx = bx0 + 6 + wi * 14
            draw.rectangle((wx, fy + 10, wx + 9, fy + 20), fill=UTC_GOLD if wi == 1 else (62, 54, 52), outline=ink, width=lw_thin)


# ---------------------------------------------------------------------------
# Vector World Map (7-Region Colored + 14 Pins #10-#23, Clean Zero-Crossing Leaders)
# ---------------------------------------------------------------------------
MAP_POLYGONS: List[Tuple[str, List[Tuple[float, float]]]] = [
    ("AMERICAS", [
        (-168, 66), (-142, 70), (-118, 69), (-95, 68), (-82, 62), (-65, 60),
        (-54, 48), (-67, 44), (-76, 35), (-81, 25), (-88, 21), (-84, 10),
        (-78, 8), (-84, 14), (-96, 16), (-106, 20), (-114, 31), (-124, 40),
        (-130, 54), (-150, 60), (-165, 58),
    ]),
    ("AMERICAS", [(-55, 60), (-42, 60), (-22, 72), (-25, 81), (-58, 78), (-64, 68)]),
    ("AMERICAS", [
        (-78, 9), (-62, 10), (-50, 1), (-35, -6), (-39, -18), (-48, -28),
        (-58, -38), (-67, -54), (-74, -52), (-73, -36), (-71, -18), (-81, -4), (-79, 4),
    ]),
    ("EUROPE", [
        (-9, 37), (-9, 43), (-2, 44), (-4, 48), (2, 51), (8, 54), (11, 58),
        (5, 61), (14, 68), (28, 71), (42, 67), (52, 60), (46, 48), (38, 45),
        (30, 46), (28, 41), (22, 37), (16, 40), (13, 45), (8, 44), (3, 42), (-5, 36),
    ]),
    ("EUROPE", [(-10, 51), (-5, 51), (1, 51), (1, 54), (-3, 58), (-7, 57), (-9, 54)]),
    ("AFRICA", [
        (-17, 15), (-13, 28), (-6, 36), (10, 37), (25, 32), (33, 31), (43, 12),
        (51, 11), (41, -2), (40, -15), (33, -26), (20, -35), (14, -22), (12, -6),
        (9, 4), (-7, 5), (-16, 11),
    ]),
    ("AFRICA", [(44, -25), (47, -25), (50, -13), (47, -13)]),
    ("MIDDLE EAST", [
        (26, 40), (36, 42), (45, 40), (54, 37), (61, 35), (61, 25), (56, 26),
        (59, 22), (52, 16), (43, 13), (39, 21), (35, 29), (36, 36), (27, 37),
    ]),
    ("ASIA-PACIFIC", [
        (52, 60), (65, 70), (105, 74), (145, 71), (174, 65), (162, 56),
        (142, 53), (135, 43), (128, 35), (122, 39), (121, 31), (118, 24),
        (109, 20), (109, 12), (103, 2), (99, 14), (91, 22), (80, 15),
        (77, 8), (68, 23), (62, 25), (61, 36), (54, 41), (48, 48),
    ]),
    ("ASIA-PACIFIC", [(130, 31), (136, 34), (142, 41), (145, 44), (140, 42), (132, 35)]),
    ("ASIA-PACIFIC", [(96, 5), (105, -6), (116, -8), (118, -3), (106, -1)]),
    ("OCEANIA", [(141, -3), (150, -6), (151, -10), (143, -9), (141, -6)]),
    ("OCEANIA", [(114, -22), (124, -14), (136, -12), (143, -11), (153, -27),
                 (150, -37), (138, -35), (122, -34), (114, -34)]),
    ("OCEANIA", [(167, -46), (173, -41), (178, -37), (174, -35), (169, -43)]),
    ("WORLD", [
        (-175, -64), (-120, -67), (-60, -63), (0, -66), (65, -65), (135, -66),
        (175, -65), (175, -78), (-175, -78),
    ]),
]

# Carefully de-crowded leader offsets (dx, dy px) for 14 pins (#10-#23) — zero crossings!
PIN_OFFSETS: Dict[int, Tuple[int, int]] = {
    10: (10, -21),   # Bratislava -> NE (short, clear)
    11: (32, 6),     # Gaza -> E over Arabian Sea (clear of #23 and #15)
    12: (-18, -14),  # San Antonio -> NW
    13: (18, 12),    # Tupanciretã -> SE
    14: (-16, -18),  # Seoul -> NW
    15: (22, 22),    # Khartoum -> SE into Indian Ocean (clear of #11)
    16: (-24, 6),    # Bayelsa -> W into Atlantic
    17: (-4, 24),    # Oyo, Congo -> S
    18: (-20, 12),   # Canberra -> SW
    19: (16, -12),   # Port Moresby -> NE
    20: (-19, 13),   # Turin -> SW into Western Med (short, zero UK crossing!)
    21: (-24, -10),  # Manchester -> WNW into Atlantic
    22: (18, 10),    # Okinawa -> SE into Pacific
    23: (18, -18),   # Beirut -> NE toward Caspian (clear of #10 and #11)
}


def draw_section_header(
    draw: ImageDraw.ImageDraw,
    boxes: List[BoxRecord],
    label: str,
    title: str,
    x0: int,
    y0: int,
    x1: int,
    h: int,
    font_log: List[Tuple[str, int, int, int]],
) -> None:
    """Airy editorial broadsheet section header (2px navy top rule + cream bar + 1px rule)."""
    draw.rectangle((x0, y0, x1, y0 + h), fill=SEC_HDR_BG)
    draw.rectangle((x0, y0, x1, y0 + 1), fill=NAVY_BAR)
    draw.line((x0, y0 + h, x1, y0 + h), fill=CARD_BORDER, width=1)
    draw_fitted_text(
        draw, boxes, label,
        title, load_font(FONT_SANS_BOLD, 10),
        x0 + 7, y0 + 1, (x1 - x0) - 14, 1, NAVY_BAR,
        align="left", valign="middle", box_h=h - 1,
        font_log=font_log,
    )


def draw_world_map(
    draw: ImageDraw.ImageDraw,
    boxes: List[BoxRecord],
    map_rect: Tuple[int, int, int, int],
    pinned_stories: Sequence[Story],
    font_log: List[Tuple[str, int, int, int]],
) -> None:
    x0, y0, x1, y1 = map_rect
    draw.rectangle(map_rect, fill=CARD_BG, outline=CARD_BORDER, width=1)

    hdr_h = 18
    p_min = min(s.num for s in pinned_stories)
    p_max = max(s.num for s in pinned_stories)
    draw_section_header(
        draw, boxes, "map_header",
        f"WHERE IT HAPPENED · {len(pinned_stories)} PINS (#{p_min}–#{p_max})",
        x0, y0, x1, hdr_h, font_log,
    )

    pad = 4
    mx0, my0 = x0 + pad, y0 + hdr_h + pad
    mx1, my1 = x1 - pad, y1 - 19
    mw = mx1 - mx0
    mh = my1 - my0

    draw.rectangle((mx0, my0, mx1, my1), fill=OCEAN_BG, outline=CARD_BORDER, width=1)

    def proj(lon: float, lat: float) -> Tuple[int, int]:
        px = mx0 + int(round((lon + 180.0) / 360.0 * mw))
        py = my0 + int(round((82.0 - lat) / 160.0 * mh))
        return (px, py)

    for lon in range(-150, 180, 30):
        draw.line((proj(lon, 82), proj(lon, -78)), fill=OCEAN_GRID, width=1)
    for lat in range(-60, 90, 30):
        draw.line((proj(-180, lat), proj(180, lat)), fill=OCEAN_GRID, width=1)

    for region, poly in MAP_POLYGONS:
        pts = [proj(lo, la) for lo, la in poly]
        base = REGION_COLORS[region]
        draw.polygon(pts, fill=tint(base, 0.44), outline=tint(base, 0.14))

    pin_sz = 17
    pin_font = load_font(FONT_SANS_BOLD, 10)
    for st in pinned_stories:
        if st.lon is None or st.lat is None:
            raise RuntimeError(f"Pinned story #{st.num} missing lon/lat")
        gx, gy = proj(st.lon, st.lat)
        ox, oy = PIN_OFFSETS[st.num]
        px = max(mx0 + 2, min(mx1 - pin_sz - 2, gx + ox - pin_sz // 2))
        py = max(my0 + 2, min(my1 - pin_sz - 2, gy + oy - pin_sz // 2))
        pcx, pcy = px + pin_sz // 2, py + pin_sz // 2
        col = REGION_COLORS[st.region]

        draw.line((gx, gy, pcx, pcy), fill=INK_BLACK, width=1)
        draw.ellipse((gx - 2, gy - 2, gx + 2, gy + 2), fill=col, outline=WHITE, width=1)

        pin_box = (px, py, px + pin_sz, py + pin_sz)
        draw.rectangle(pin_box, fill=col, outline=WHITE, width=1)
        draw_fitted_text(
            draw, boxes, f"map_pin_txt_{st.num}",
            str(st.num), pin_font,
            px, py, pin_sz, 1, WHITE,
            align="center", valign="middle", box_h=pin_sz,
            register=False, font_log=font_log,
        )
        boxes.append((f"map_pin_{st.num}", pin_box))

    # Clean, legible map footer note (no redundant 8px cramped key!)
    key_y0 = my1 + 2
    key_h = (y1 - 2) - key_y0
    draw_fitted_text(
        draw, boxes, "map_footer_note",
        "Colours match 7-region bar above · Pins #10–#23 locate dispatches at right",
        load_font(FONT_SANS_CN_BOLD, 9),
        x0 + 6, key_y0, (x1 - x0) - 12, 1, INK_MUTED,
        align="center", valign="middle", box_h=key_h,
        font_log=font_log,
    )


# ---------------------------------------------------------------------------
# Compact Brief Row Renderer (2-col and 3-col wire blocks)
# Follows r02's clean pattern: bold 11.5-12px title + sharp source; pills ONLY for non-CONFIRMED
# ---------------------------------------------------------------------------
def draw_wire_cell(
    draw: ImageDraw.ImageDraw,
    boxes: List[BoxRecord],
    st: Story,
    cell_rect: Tuple[int, int, int, int],
    title_font: ImageFont.FreeTypeFont,
    meta_font: ImageFont.FreeTypeFont,
    status_font: ImageFont.FreeTypeFont,
    num_font: ImageFont.FreeTypeFont,
    font_log: List[Tuple[str, int, int, int]],
) -> None:
    cx0, cy0, cx1, cy1 = cell_rect
    ch = cy1 - cy0
    reg_col = REGION_COLORS[st.region]

    nsz = 18
    nx0 = cx0 + 4
    ny0 = cy0 + (ch - nsz) // 2
    nbox = (nx0, ny0, nx0 + nsz, ny0 + nsz)
    draw.rectangle(nbox, fill=reg_col)
    draw_fitted_text(
        draw, boxes, f"wire_{st.num}_num_txt",
        str(st.num), num_font,
        nx0, ny0, nsz, 1, WHITE,
        align="center", valign="middle", box_h=nsz,
        register=False, font_log=font_log,
    )
    boxes.append((f"wire_{st.num}_num", nbox))

    tx0 = nx0 + nsz + 5
    tx1 = cx1 - 6
    tw = tx1 - tx0

    # Top line: Bold headline (11.5-12px condensed sans, 1 line)
    draw_fitted_text(
        draw, boxes, f"wire_{st.num}_title",
        st.title, title_font,
        tx0, cy0 + 1, tw, 1, INK_BLACK,
        align="left", valign="middle", box_h=12,
        font_log=font_log,
    )

    # Bottom line: CITY · Source + status pill ONLY for non-CONFIRMED items (eliminates green-dash noise!)
    py0 = cy0 + 13
    if st.status != "CONFIRMED":
        st_col = STATUS_COLORS[st.status]
        st_tw = _text_width(st.status, status_font)
        pw = st_tw + 7
        ph = 10
        px0 = tx1 - pw
        prect = (px0, py0, tx1, py0 + ph)
        draw.rectangle(prect, fill=st_col)
        draw_fitted_text(
            draw, boxes, f"wire_{st.num}_status_txt",
            st.status, status_font,
            px0, py0, pw, 1, WHITE,
            align="center", valign="middle", box_h=ph,
            register=False, font_log=font_log,
        )
        boxes.append((f"wire_{st.num}_status", prect))
        meta_w = (px0 - 5) - tx0
    else:
        meta_w = tw

    draw_fitted_text(
        draw, boxes, f"wire_{st.num}_src",
        f"{st.topic_or_city} · {st.source}", meta_font,
        tx0, py0, meta_w, 1, INK_MUTED,
        align="left", valign="middle", box_h=10,
        font_log=font_log,
    )


# ---------------------------------------------------------------------------
# Main Render Pipeline (Native 1024x1024 px)
# ---------------------------------------------------------------------------
def build_poster() -> Tuple[Image.Image, Dict[str, int], List[Tuple[str, str, int]], int, List[Tuple[str, int, int, int]]]:
    if not (32 <= len(STORIES) <= 38):
        raise RuntimeError(f"Expected 32-38 stories, got {len(STORIES)}")
    nums = [s.num for s in STORIES]
    if nums != list(range(1, len(STORIES) + 1)):
        raise RuntimeError("Story numbers must be contiguous 1..N")

    cards = STORIES[:9]           # 9 Main Cards (3x3)
    two_col_wire = STORIES[9:25]  # 16 Two-Column Briefs beside Map (8x2)
    pinned = [s for s in two_col_wire if s.lon is not None and s.lat is not None]
    bottom_wire = STORIES[25:]    # 9 Three-Column Wire Briefs (3x3)

    if len(cards) != 9 or len(two_col_wire) != 16 or len(bottom_wire) != 9:
        raise RuntimeError("Layout partition must be 9 cards + 16 two-col + 9 three-col")
    if not (12 <= len(pinned) <= 14):
        raise RuntimeError(f"Expected 12-14 map pins, got {len(pinned)}")

    # Dynamic 7-region count (NO hardcoding; assert every region >= 3)
    region_counts: Dict[str, int] = dict(Counter(s.region for s in STORIES))
    for reg in REGION_ORDER:
        cnt = region_counts.get(reg, 0)
        if cnt < 3:
            raise RuntimeError(f"Region {reg} has only {cnt} stories (must be >= 3)")
    if sum(region_counts.values()) != len(STORIES):
        raise RuntimeError("Region count sum mismatch")

    # Dynamic 6-cell KPI extraction (verified verbatim against STORIES text)
    kpi_items = extract_kpi_strip(STORIES)

    img = Image.new("RGB", (CANVAS_W, CANVAS_H), BG_PAPER)
    draw = ImageDraw.Draw(img)
    boxes: List[BoxRecord] = []
    font_log: List[Tuple[str, int, int, int]] = []

    MX = 12
    X0 = MX
    X1 = CANVAS_W - MX
    CW = X1 - X0  # 1000 px

    # =========================================================================
    # 1. TOP UTILITY BAR (y = 0..23, full-bleed navy, 11px bold)
    # =========================================================================
    top_h = 23
    draw.rectangle((0, 0, CANVAS_W, top_h), fill=NAVY_BAR)
    top_font = load_font(FONT_SANS_BOLD, 11)
    draw_fitted_text(
        draw, boxes, "top_left",
        "THE WORLD IN ONE DAY",
        top_font, X0, 0, 260, 1, UTC_GOLD,
        align="left", valign="middle", box_h=top_h,
        font_log=font_log,
    )
    right_banner = (
        f"{len(STORIES)} STORIES · {len(REGION_ORDER)} REGIONS · "
        "EVERY ONE DATED SUNDAY 22 NOVEMBER 2026"
    )
    draw_fitted_text(
        draw, boxes, "top_right",
        right_banner,
        top_font, X0 + 270, 0, CW - 270, 1, WHITE,
        align="right", valign="middle", box_h=top_h,
        font_log=font_log,
    )

    # =========================================================================
    # 2. GIANT DATE MASTHEAD (y = 27..101, 79px bold serif, airy top clearance)
    #    + Double-color editorial rule (3px dark + 1px crimson)
    # =========================================================================
    draw_fitted_text(
        draw, boxes, "giant_date",
        "Sunday 22 November 2026",
        load_font(FONT_SERIF_BOLD, 79),
        8, 27, CANVAS_W - 16, 1, INK_BLACK,
        align="center", valign="middle", box_h=74,
        font_log=font_log,
    )
    rule_y = 104
    draw.rectangle((X0, rule_y, X1, rule_y + 2), fill=RULE_DARK)
    draw.rectangle((X0, rule_y + 5, X1, rule_y + 5), fill=CRIMSON)

    # =========================================================================
    # 3. 6-CELL BIG-NUMBER KPI STRIP (y = 112..175, locked shared baseline, >=44px!)
    # =========================================================================
    sc_y0, sc_y1 = 112, 175
    draw.rectangle((X0, sc_y0, X1, sc_y1), fill=SCORE_BG, outline=CARD_BORDER, width=1)
    cell_w = CW / len(kpi_items)
    kpi_num_font = load_font(FONT_SERIF_BOLD, 44)
    kpi_lbl_font = load_font(FONT_SANS_CN_BOLD, 11)
    shared_baseline_y = sc_y0 + 39
    for i, (val, lbl, _snum) in enumerate(kpi_items):
        cx0 = X0 + int(round(i * cell_w))
        cx1 = X0 + int(round((i + 1) * cell_w))
        cw_i = cx1 - cx0
        if i > 0:
            draw.line((cx0, sc_y0 + 7, cx0, sc_y1 - 7), fill=CARD_BORDER, width=1)
        val_color = CRIMSON if i in (0, 2, 3) else INK_BLACK
        draw_baseline_kpi(
            draw, boxes, f"kpi_num_{i}",
            val, kpi_num_font,
            (cx0 + cx1) // 2, shared_baseline_y, cw_i - 8, val_color,
            min_px=44, font_log=font_log,
        )
        draw_fitted_text(
            draw, boxes, f"kpi_lbl_{i}",
            lbl, kpi_lbl_font,
            cx0 + 4, sc_y0 + 47, cw_i - 8, 1, INK_DARK,
            align="center", valign="middle", box_h=14,
            font_log=font_log,
        )

    # =========================================================================
    # 4. "DAY IN UTC" TIMELINE BAND (y = 179..212, 8 equal-width slots, crisp 11/10px)
    # =========================================================================
    utc_y0, utc_y1 = 179, 212
    utc_h = utc_y1 - utc_y0
    draw.rectangle((X0, utc_y0, X1, utc_y1), fill=UTC_BAR)
    hdr_w = 96
    draw.rectangle((X0, utc_y0, X0 + hdr_w, utc_y1), fill=NAVY_BAR)
    draw.line((X0 + hdr_w, utc_y0 + 4, X0 + hdr_w, utc_y1 - 4), fill=UTC_GOLD, width=1)
    draw_fitted_text(
        draw, boxes, "utc_badge",
        "DAY IN UTC",
        load_font(FONT_SANS_BOLD, 11),
        X0 + 4, utc_y0, hdr_w - 8, 1, UTC_GOLD,
        align="center", valign="middle", box_h=utc_h,
        font_log=font_log,
    )
    slot_area_x0 = X0 + hdr_w + 4
    slot_area_w = X1 - slot_area_x0
    slot_w = slot_area_w / len(UTC_TIMELINE)
    utc_t_font = load_font(FONT_SANS_BOLD, 11)
    utc_e_font = load_font(FONT_SANS_CN_BOLD, 10)
    for i, (ts, ev) in enumerate(UTC_TIMELINE):
        sx0 = slot_area_x0 + int(round(i * slot_w))
        sx1 = slot_area_x0 + int(round((i + 1) * slot_w))
        sw_i = sx1 - sx0
        if i > 0:
            draw.line((sx0, utc_y0 + 5, sx0, utc_y1 - 5), fill=(52, 72, 112), width=1)
        draw_fitted_text(
            draw, boxes, f"utc_time_{i}",
            ts, utc_t_font,
            sx0 + 2, utc_y0 + 2, sw_i - 4, 1, UTC_GOLD,
            align="center", valign="middle", box_h=14,
            font_log=font_log,
        )
        draw_fitted_text(
            draw, boxes, f"utc_ev_{i}",
            ev, utc_e_font,
            sx0 + 2, utc_y0 + 17, sw_i - 4, 1, WHITE,
            align="center", valign="middle", box_h=13,
            font_log=font_log,
        )

    # =========================================================================
    # 5. 7-COLOR REGION BAR (y = 216..239, 23px tall, 11px bold white, dynamic counts)
    # =========================================================================
    rb_y0 = 216
    rb_h = 23
    rb_y1 = rb_y0 + rb_h
    total_stories = sum(region_counts[r] for r in REGION_ORDER)
    min_seg = 98.0
    extra_pool = CW - min_seg * len(REGION_ORDER)
    seg_widths = [
        min_seg + extra_pool * (region_counts[r] / total_stories) for r in REGION_ORDER
    ]
    cur_x = X0
    rb_font = load_font(FONT_SANS_CN_BOLD, 11)
    for idx, reg in enumerate(REGION_ORDER):
        seg_w = int(round(seg_widths[idx])) if idx < len(REGION_ORDER) - 1 else (X1 - cur_x)
        draw.rectangle((cur_x, rb_y0, cur_x + seg_w, rb_y1), fill=REGION_COLORS[reg])
        if idx > 0:
            draw.line((cur_x, rb_y0, cur_x, rb_y1), fill=BG_PAPER, width=2)
        draw_fitted_text(
            draw, boxes, f"region_bar_{reg}",
            f"{reg} {region_counts[reg]}",
            rb_font,
            cur_x + 3, rb_y0, seg_w - 6, 1, WHITE,
            align="center", valign="middle", box_h=rb_h,
            font_log=font_log,
        )
        cur_x += seg_w

    # =========================================================================
    # 6. MAIN CARD GRID (9 Cards: 3 cols x 3 rows, y = 244..624)
    #    Inline 20x20 badge in meta row -> full 248px headline width (ZERO badge void!)
    #    Row 1 lead cards: 128px tall, 21px headlines; Rows 2-3: 119px tall, 19px headlines
    # =========================================================================
    grid_y0 = 244
    card_gap_x = 8
    card_gap_y = 7
    card_w = (CW - 2 * card_gap_x) // 3  # 328px
    row_heights = [128, 119, 119]        # 128+119+119+14 = 380px -> ends cleanly at y=624
    row_y0s = [
        grid_y0,
        grid_y0 + row_heights[0] + card_gap_y,
        grid_y0 + row_heights[0] + row_heights[1] + 2 * card_gap_y,
    ]

    badge_font = load_font(FONT_SANS_BOLD, 13)
    meta_font = load_font(FONT_SANS_CN_BOLD, 10)
    status_font = load_font(FONT_SANS_CN_BOLD, 9)
    lead_title_font = load_font(FONT_SERIF_BOLD, 21)
    feat_title_font = load_font(FONT_SERIF_BOLD, 19)
    lede_font = load_font(FONT_SANS_REG, 12)
    src_font = load_font(FONT_SERIF_ITAL, 10)

    for idx, st in enumerate(cards):
        col = idx % 3
        row = idx // 3
        cx0 = X0 + col * (card_w + card_gap_x)
        cy0 = row_y0s[row]
        ch = row_heights[row]
        cx1 = cx0 + card_w
        cy1 = cy0 + ch
        reg_col = REGION_COLORS[st.region]

        # Flat archival card + 3px colored top accent stripe
        draw.rectangle((cx0, cy0, cx1, cy1), fill=CARD_BG, outline=CARD_BORDER, width=1)
        draw.rectangle((cx0, cy0, cx1, cy0 + 2), fill=reg_col)

        # Right 2px Line-Art Illustration Strip (66px wide, full height)
        il_w = 66
        il_x0 = cx1 - 4 - il_w
        il_rect = (il_x0, cy0 + 5, cx1 - 4, cy1 - 4)
        draw_card_illustration(draw, st.num, il_rect, reg_col)
        boxes.append((f"card_{st.num}_illus", il_rect))

        # Full left-to-illustration text column (248px wide!)
        tx0 = cx0 + 6
        tx1 = il_x0 - 5
        tw = tx1 - tx0  # 247px

        # Meta Row (y+5..y+23): Inline 18x18 colored number badge + REGION · TOPIC + Status Pill
        b_sz = 18
        by0 = cy0 + 5
        badge_rect = (tx0, by0, tx0 + b_sz, by0 + b_sz)
        draw.rectangle(badge_rect, fill=reg_col)
        draw_fitted_text(
            draw, boxes, f"card_{st.num}_badge_txt",
            str(st.num), badge_font,
            tx0, by0, b_sz, 1, WHITE,
            align="center", valign="middle", box_h=b_sz,
            register=False, font_log=font_log,
        )
        boxes.append((f"card_{st.num}_badge", badge_rect))

        st_col = STATUS_COLORS[st.status]
        st_tw = _text_width(st.status, status_font)
        pill_w = st_tw + 8
        pill_h = 13
        pill_x0 = tx1 - pill_w
        pill_y0 = by0 + (b_sz - pill_h) // 2
        pill_rect = (pill_x0, pill_y0, tx1, pill_y0 + pill_h)
        draw.rectangle(pill_rect, fill=st_col)
        draw_fitted_text(
            draw, boxes, f"card_{st.num}_status_txt",
            st.status, status_font,
            pill_x0, pill_y0, pill_w, 1, WHITE,
            align="center", valign="middle", box_h=pill_h,
            register=False, font_log=font_log,
        )
        boxes.append((f"card_{st.num}_status", pill_rect))

        meta_x0 = tx0 + b_sz + 5
        meta_w = (pill_x0 - 4) - meta_x0
        draw_fitted_text(
            draw, boxes, f"card_{st.num}_meta",
            f"{REGION_SHORT[st.region]} · {st.topic_or_city}",
            meta_font,
            meta_x0, by0, meta_w, 1, reg_col,
            align="left", valign="middle", box_h=b_sz,
            font_log=font_log,
        )

        # Bold Serif Headline across full 247px width (21px Row 1, 19px Rows 2-3, ZERO shrink!)
        hl_y0 = cy0 + 26
        hl_h = 48 if row == 0 else 43
        cur_title_font = lead_title_font if row == 0 else feat_title_font
        draw_fitted_text(
            draw, boxes, f"card_{st.num}_title",
            st.title, cur_title_font,
            tx0, hl_y0, tw, 2, INK_BLACK,
            align="left", valign="top", box_h=hl_h, line_spacing=1.06,
            font_log=font_log,
        )

        # Lede (12px crisp sans, max 2 lines, full 247px width, ZERO shrink!)
        lede_y0 = cy0 + (78 if row == 0 else 72)
        lede_h = 30
        draw_fitted_text(
            draw, boxes, f"card_{st.num}_lede",
            st.lede, lede_font,
            tx0, lede_y0, tw, 2, INK_DARK,
            align="left", valign="top", box_h=lede_h, line_spacing=1.10,
            font_log=font_log,
        )

        # Source line (10px italic serif, crisp dark slate)
        src_y0 = cy1 - 16
        draw_fitted_text(
            draw, boxes, f"card_{st.num}_source",
            f"Source: {st.source}", src_font,
            tx0, src_y0, tw, 1, INK_MUTED,
            align="left", valign="middle", box_h=12,
            font_log=font_log,
        )

    # =========================================================================
    # 7A. LOWER SPLIT (y = 630..842, height 212px):
    #     Left World Map (432px, 14 pins) + Right 2-Col Briefs (558px, 16 items)
    # =========================================================================
    mid_y0, mid_y1 = 630, 842
    map_w = 432
    mid_gap = 10
    map_rect = (X0, mid_y0, X0 + map_w, mid_y1)
    list_x0 = X0 + map_w + mid_gap
    list_rect = (list_x0, mid_y0, X1, mid_y1)

    draw_world_map(draw, boxes, map_rect, pinned, font_log)

    draw.rectangle(list_rect, fill=CARD_BG, outline=CARD_BORDER, width=1)
    lhdr_h = 18
    draw_section_header(
        draw, boxes, "wire2_header",
        "GLOBAL DISPATCHES · ITEMS 10–25 · TWO-COLUMN WIRE",
        list_x0, mid_y0, X1, lhdr_h, font_log,
    )

    w2_body_y0 = mid_y0 + lhdr_h + 1
    w2_body_h = (mid_y1 - 1) - w2_body_y0
    n_rows_2 = 8
    w2_col_w = (X1 - list_x0) // 2
    w2_row_h = w2_body_h / n_rows_2

    wire_title_font = load_font(FONT_SANS_CN_BOLD, 12)
    wire_meta_font = load_font(FONT_SERIF_ITAL, 10)
    wire_status_font = load_font(FONT_SANS_CN_BOLD, 8)
    wire_num_font = load_font(FONT_SANS_BOLD, 10)

    mid_cx = list_x0 + w2_col_w
    draw.line((mid_cx, w2_body_y0 + 3, mid_cx, mid_y1 - 3), fill=RULE_LIGHT, width=1)

    for idx, st in enumerate(two_col_wire):
        col = idx // n_rows_2
        row = idx % n_rows_2
        rx0 = list_x0 + (0 if col == 0 else w2_col_w + 1)
        rx1 = (mid_cx - 1) if col == 0 else X1
        ry0 = w2_body_y0 + int(round(row * w2_row_h))
        ry1 = w2_body_y0 + int(round((row + 1) * w2_row_h))
        if row % 2 == 1:
            draw.rectangle((rx0 + 1, ry0, rx1 - 1, ry1), fill=(249, 246, 240))
        if row > 0:
            draw.line((rx0 + 4, ry0, rx1 - 4, ry0), fill=RULE_LIGHT, width=1)
        draw_wire_cell(
            draw, boxes, st, (rx0, ry0, rx1, ry1),
            wire_title_font, wire_meta_font, wire_status_font, wire_num_font,
            font_log,
        )

    # =========================================================================
    # 7B. FULL-WIDTH 3-COLUMN WIRE ROUNDUP (y = 848..944, height 96px, 9 items #26-#34)
    # =========================================================================
    w3_y0, w3_y1 = 848, 944
    draw.rectangle((X0, w3_y0, X1, w3_y1), fill=CARD_BG, outline=CARD_BORDER, width=1)
    w3_hdr_h = 18
    draw_section_header(
        draw, boxes, "wire3_header",
        "ALSO ON SUNDAY 22 NOVEMBER · ITEMS 26–34 · GLOBAL WIRE ROUNDUP",
        X0, w3_y0, X1, w3_hdr_h, font_log,
    )

    w3_body_y0 = w3_y0 + w3_hdr_h + 1
    w3_body_h = (w3_y1 - 1) - w3_body_y0
    n_rows_3 = 3
    w3_col_w = CW / 3.0
    w3_row_h = w3_body_h / n_rows_3

    for c in (1, 2):
        div_x = X0 + int(round(c * w3_col_w))
        draw.line((div_x, w3_body_y0 + 3, div_x, w3_y1 - 3), fill=RULE_LIGHT, width=1)

    for idx, st in enumerate(bottom_wire):
        col = idx // n_rows_3
        row = idx % n_rows_3
        rx0 = X0 + int(round(col * w3_col_w)) + (1 if col > 0 else 0)
        rx1 = X0 + int(round((col + 1) * w3_col_w)) - (1 if col < 2 else 0)
        ry0 = w3_body_y0 + int(round(row * w3_row_h))
        ry1 = w3_body_y0 + int(round((row + 1) * w3_row_h))
        if row % 2 == 1:
            draw.rectangle((rx0 + 1, ry0, rx1 - 1, ry1), fill=(249, 246, 240))
        if row > 0:
            draw.line((rx0 + 4, ry0, rx1 - 4, ry0), fill=RULE_LIGHT, width=1)
        draw_wire_cell(
            draw, boxes, st, (rx0, ry0, rx1, ry1),
            wire_title_font, wire_meta_font, wire_status_font, wire_num_font,
            font_log,
        )

    # =========================================================================
    # 8. BOTTOM "DATE CHECK — READ THIS FIRST" + TAG LEGEND (y = 950..1020, 70px)
    #    Enlarged 10px copy filling full width + crisp 9px legend chips
    # =========================================================================
    dc_y0, dc_y1 = 950, 1020
    draw.rectangle((X0, dc_y0, X1, dc_y1), fill=DATECHECK_BG, outline=CRIMSON, width=2)

    badge_w = 198
    badge_h = 17
    dc_badge_rect = (X0 + 6, dc_y0 + 4, X0 + 6 + badge_w, dc_y0 + 4 + badge_h)
    draw.rectangle(dc_badge_rect, fill=CRIMSON)
    draw_fitted_text(
        draw, boxes, "dc_badge_txt",
        "DATE CHECK — READ THIS FIRST",
        load_font(FONT_SANS_CN_BOLD, 10),
        dc_badge_rect[0], dc_badge_rect[1], badge_w, 1, WHITE,
        align="center", valign="middle", box_h=badge_h,
        register=False, font_log=font_log,
    )
    boxes.append(("dc_badge", dc_badge_rect))

    dc_cutoff = (
        "Wires read to 23:59 UTC, Sunday 22 November 2026 — every story occurred or developed on 22 Nov in at least one time zone."
    )
    draw_fitted_text(
        draw, boxes, "dc_cutoff",
        dc_cutoff,
        load_font(FONT_SANS_CN_BOLD, 10),
        dc_badge_rect[2] + 8, dc_y0 + 4, (X1 - 6) - (dc_badge_rect[2] + 8), 1, INK_BLACK,
        align="left", valign="middle", box_h=badge_h,
        font_log=font_log,
    )

    dc_excl = (
        "OMITTED ON PURPOSE (EARLIER DATES): Peru M6.7 quake (Fri 20 Nov) · Russia's 400-drone barrage (19–20 Nov; Sunday's was 186) · "
        "APEC Shenzhen summit (Thu 19 Nov) · French Senate shooting vote (Fri 20 Nov)."
    )
    draw_fitted_text(
        draw, boxes, "dc_exclusions",
        dc_excl,
        load_font(FONT_SANS_CN_REG, 10),
        X0 + 6, dc_y0 + 24, CW - 12, 1, INK_DARK,
        align="left", valign="middle", box_h=16,
        font_log=font_log,
    )

    leg_div_y = dc_y0 + 44
    draw.line((X0 + 6, leg_div_y, X1 - 6, leg_div_y), fill=CARD_BORDER, width=1)

    leg_y = leg_div_y + 3
    leg_h = 19
    cur_lx = X0 + 6
    leg_hdr_font = load_font(FONT_SANS_CN_BOLD, 10)
    leg_hdr_txt = "HOW TO READ THE TAGS:"
    leg_hdr_w = _text_width(leg_hdr_txt, leg_hdr_font) + 4
    draw_fitted_text(
        draw, boxes, "tag_legend_hdr",
        leg_hdr_txt, leg_hdr_font,
        cur_lx, leg_y, leg_hdr_w, 1, CRIMSON,
        align="left", valign="middle", box_h=leg_h,
        font_log=font_log,
    )
    cur_lx += leg_hdr_w + 5

    tag_defs = [
        ("CONFIRMED", "Official / ≥2 wires (unbadged briefs)"),
        ("ONGOING", "Active 22 Nov crisis"),
        ("REPORTED", "Single-wire report"),
        ("CLAIM", "One-party claim"),
    ]
    pill_f = load_font(FONT_SANS_CN_BOLD, 9)
    desc_f = load_font(FONT_SANS_CN_REG, 10)
    for t_name, t_desc in tag_defs:
        pw = _text_width(t_name, pill_f) + 8
        ph = 14
        py0 = leg_y + (leg_h - ph) // 2
        prect = (cur_lx, py0, cur_lx + pw, py0 + ph)
        draw.rectangle(prect, fill=STATUS_COLORS[t_name])
        draw_fitted_text(
            draw, boxes, f"legend_pill_txt_{t_name}",
            t_name, pill_f,
            cur_lx, py0, pw, 1, WHITE,
            align="center", valign="middle", box_h=ph,
            register=False, font_log=font_log,
        )
        boxes.append((f"legend_pill_{t_name}", prect))
        cur_lx += pw + 4
        dw = _text_width(t_desc, desc_f) + 2
        draw_fitted_text(
            draw, boxes, f"legend_desc_{t_name}",
            t_desc, desc_f,
            cur_lx, leg_y, dw, 1, INK_DARK,
            align="left", valign="middle", box_h=leg_h,
            font_log=font_log,
        )
        cur_lx += dw + 8

    colo_w = (X1 - 6) - cur_lx
    draw_fitted_text(
        draw, boxes, "colophon",
        "Original line-art illustrations, not photos",
        load_font(FONT_SERIF_ITAL, 10),
        cur_lx, leg_y, colo_w, 1, INK_MUTED,
        align="right", valign="middle", box_h=leg_h,
        font_log=font_log,
    )

    pairs_checked = no_overlap(boxes)
    return img, region_counts, kpi_items, pairs_checked, font_log


def file_md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    img, region_counts, kpi_items, pairs_checked, font_log = build_poster()

    if img.size != (CANVAS_W, CANVAS_H):
        raise RuntimeError(f"Expected {CANVAS_W}x{CANVAS_H}, got {img.size}")

    img.save(OUT_MAIN, format="PNG", optimize=True, compress_level=9)
    size_bytes = os.path.getsize(OUT_MAIN)
    if size_bytes > MAX_PNG_BYTES:
        raise RuntimeError(
            f"entry.png exceeds 1 MiB gate cap: {size_bytes} bytes > {MAX_PNG_BYTES}"
        )

    preview = img.resize((300, 300), Image.Resampling.LANCZOS)
    preview.save(OUT_PREVIEW, format="PNG", optimize=True, compress_level=9)

    counts_str = " · ".join(f"{r} {region_counts[r]}" for r in REGION_ORDER)
    kpi_str = " | ".join(f"{v} ({l}, #{n})" for v, l, n in kpi_items)
    shrunk = [(lbl, req, act, lns) for (lbl, req, act, lns) in font_log if act < req]
    print(f"Stories: {len(STORIES)} (9 main cards + 16 two-col briefs + 9 three-col briefs)")
    print(f"Regions: {counts_str} (sum={sum(region_counts.values())})")
    print(f"KPIs:    {kpi_str}")
    print(f"Master:  {img.size[0]}x{img.size[1]}, {size_bytes:,} bytes ({size_bytes / (1024*1024):.3f} MiB)")
    print(f"MD5:     {file_md5(OUT_MAIN)}")
    print(f"Preview: 300x300, {os.path.getsize(OUT_PREVIEW):,} bytes, md5={file_md5(OUT_PREVIEW)}")
    print(f"Overlap: 0 collisions across {pairs_checked:,} box pairs")
    if shrunk:
        print(f"Shrunk ({len(shrunk)}): " + ", ".join(f"{l}:{r}->{a}px" for l, r, a, _ in shrunk))
    else:
        print("Shrunk:  none (all text rendered at requested px)")


if __name__ == "__main__":
    main()
