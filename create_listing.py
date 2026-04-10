#!/usr/bin/env python3
"""
Real Estate Listing Template Generator
=======================================
Generates a clean 1440x1440 real-estate social media post.

Layout:
  ┌──────────────────────────────────────────┐
  │ [Property Type]          [Agency block]  │  top bar
  │                                          │
  │          (property photo area)           │
  │                                          │
  ├──────────────────────────────────────────┤
  │  $Price                                  │  bottom info band
  │  Property Title                          │
  │  🛏 4  🚿 3  📐 320 m²                  │
  │  📍 Location                             │
  └──────────────────────────────────────────┘

Usage:
  # Via command-line flags:
  python real_estate_template.py \\
      --price "$4,500,000 MXN" \\
      --title "Casa Moderna en Polanco" \\
      --location "Polanco, CDMX" \\
      --rooms 4 --baths 3 --area 320 \\
      --property-type "Casa en Venta" \\
      --agency "Prestige Real Estate" \\
      --agent "María López" \\
      --phone "+52 55 1234 5678" \\
      --photo property.jpg \\
      --output listing.png

  # Via XML file:
  python real_estate_template.py --xml listing_data.xml --output listing.png

  # Generate a sample XML template:
  python real_estate_template.py --sample-xml > my_listing.xml
"""

import argparse
import math
import os
import sys
import xml.etree.ElementTree as ET

import cairo
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Constants — change these to adjust the overall layout
# ---------------------------------------------------------------------------
CANVAS = 1080                  # Final output image size (pixels)
SUPERSAMPLE = 2                # Render at 2x then downscale for smooth edges
S = SUPERSAMPLE                # Shorthand multiplier
W = H = CANVAS * S             # Internal working size (2880x2880)

# Colours — change these to rebrand the template
DEEP_BLUE  = (0x0C / 255, 0x1B / 255, 0x33 / 255)   # main dark background
MID_BLUE   = (0x14 / 255, 0x28 / 255, 0x4A / 255)   # unused, available for accents
GOLD       = (0xC8 / 255, 0x96 / 255, 0x3E / 255)   # gold gradient dark stop
LIGHT_GOLD = (0xE2 / 255, 0xB8 / 255, 0x63 / 255)   # gold gradient bright stop
WHITE      = (1.0, 1.0, 1.0)

# Font file paths — update if using different fonts
FONT_BOLD   = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
FONT_MEDIUM = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"
FONT_LIGHT  = "/usr/share/fonts/truetype/google-fonts/Poppins-Light.ttf"
FONT_EMOJI  = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

# Layout — overall bar heights and margins
TOP_BAR_H    = 130 * S         # (unused — no full-width top bar, kept for reference)
BOTTOM_BAR_H = 290 * S         # ← height of the bottom navy bar (increase for more room)
MARGIN       = 55 * S          # ← left/right margin for all text content


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def rounded_rect(ctx, x, y, w, h, r):
    if r <= 0:
        ctx.rectangle(x, y, w, h)
        return
    ctx.new_path()
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.line_to(x + w - r, y)
    ctx.arc(x + w - r, y + r, r, 1.5 * math.pi, 2 * math.pi)
    ctx.line_to(x + w, y + h - r)
    ctx.arc(x + w - r, y + h - r, r, 0, 0.5 * math.pi)
    ctx.line_to(x + r, y + h)
    ctx.arc(x + r, y + h - r, r, 0.5 * math.pi, math.pi)
    ctx.close_path()


def gold_gradient(ctx, x0, y0, x1, y1):
    pat = cairo.LinearGradient(x0, y0, x1, y1)
    pat.add_color_stop_rgb(0.0, *GOLD)
    pat.add_color_stop_rgb(0.5, *LIGHT_GOLD)
    pat.add_color_stop_rgb(1.0, *GOLD)
    return pat


# ---------------------------------------------------------------------------
# Main cairo drawing
# ---------------------------------------------------------------------------
def draw_template(ctx, data, photo_surface=None):

    # ── 1. Background ─────────────────────────────────────────────────
    # If a property photo was provided, scale it to cover the full canvas.
    # Otherwise, draw a subtle dark gradient as a placeholder.
    if photo_surface:
        pw = photo_surface.get_width()
        ph = photo_surface.get_height()
        scale = max(W / pw, H / ph)
        ctx.save()
        ctx.scale(scale, scale)
        ctx.set_source_surface(photo_surface,
                               (W / scale - pw) / 2,
                               (H / scale - ph) / 2)
        ctx.paint()
        ctx.restore()
    else:
        bg = cairo.LinearGradient(0, 0, W, H)
        bg.add_color_stop_rgb(0.0, 0.25, 0.30, 0.35)
        bg.add_color_stop_rgb(1.0, 0.15, 0.18, 0.22)
        ctx.set_source(bg)
        ctx.paint()

    # ==================================================================
    # BOTTOM BAR — dark navy band at the bottom of the image.
    # Change BOTTOM_BAR_H (line ~73) to make it taller/shorter.
    # ==================================================================
    bottom_y = H - BOTTOM_BAR_H                       # top edge of the bar
    ctx.set_source_rgba(*DEEP_BLUE, 0.88)              # 88% opacity navy
    ctx.rectangle(0, bottom_y, W, BOTTOM_BAR_H)
    ctx.fill()

    # ==================================================================
    # GOLD DIVIDER LINE — sits between the photo and the bottom bar.
    #
    # ┌─────────────────────────────┐
    # │         photo area          │
    # ├═══ gold line (5px thick) ═══┤  ← gold_line_y
    # │       bottom navy bar       │  ← bottom_y
    # └─────────────────────────────┘
    #
    # To move the line UP:   decrease gold_line_y (e.g. bottom_y - 10*S)
    # To move the line DOWN: increase gold_line_y (e.g. bottom_y + 5*S)
    # To make it thicker:    increase gold_line_h
    # ==================================================================
    gold_line_h = 5 * S                                # thickness of the line
    gold_line_y = bottom_y - gold_line_h               # flush: line ends where bar begins
    ctx.set_source(gold_gradient(ctx, 0, gold_line_y, W, gold_line_y))
    ctx.rectangle(0, gold_line_y, W, gold_line_h + 2 * S)  # +2*S overlap into bar to avoid gap
    ctx.fill()

    # ==================================================================
    # TOP-LEFT PILL — "Property type" label (e.g. "Casa en Venta").
    # Floats over the photo with a gold background.
    #
    # To change font size: edit PILL_FONT_SIZE below.
    # To change pill padding: edit pill_pad_x / pill_pad_y.
    # To move it: edit pill_top_y (vertical) and pill_x (horizontal).
    # To change corner roundness: edit the last arg of rounded_rect().
    # ==================================================================
    PILL_FONT_SIZE = 44 * S            # ← CHANGE THIS to resize the pill text
    pill_top_y = 36 * S                # distance from top of image
    pill_pad_x = 28 * S               # horizontal padding inside pill
    pill_pad_y = 18 * S               # vertical padding inside pill

    prop_type = data.get("property_type", "")
    if prop_type:
        ctx.select_font_face("Poppins", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(PILL_FONT_SIZE)
        te = ctx.text_extents(prop_type)
        pill_w = te.width + pill_pad_x * 2
        pill_h = te.height + pill_pad_y * 2
        pill_x = MARGIN
        pill_y = pill_top_y

        # Gold gradient background
        ctx.set_source(gold_gradient(ctx, pill_x, pill_y, pill_x + pill_w, pill_y))
        rounded_rect(ctx, pill_x, pill_y, pill_w, pill_h, 12 * S)
        ctx.fill()

        # Dark text on the pill
        ctx.set_source_rgb(*DEEP_BLUE)
        text_y = pill_y + pill_pad_y + te.height  # baseline = top + padding + ascent
        ctx.move_to(pill_x + pill_pad_x, text_y)
        ctx.show_text(prop_type)

    # ==================================================================
    # TOP-RIGHT AGENCY BLOCK — agency name, agent, phone.
    # Floats over the photo with a dark translucent background.
    #
    # To change font sizes: edit the three sizes in the list below.
    # To change spacing between lines: edit AGENCY_LINE_GAP.
    # To change internal padding: edit AGENCY_PAD.
    # To change background opacity: edit the 0.70 in set_source_rgba().
    # ==================================================================
    AGENCY_FONT_SIZES = [30 * S, 26 * S, 26 * S]  # ← agency, agent, phone sizes
    AGENCY_LINE_GAP = 42 * S                        # vertical gap between lines
    AGENCY_PAD = 30 * S                             # internal padding
    AGENCY_EMOJI_W = 40 * S                         # space reserved before agent/phone text for emoji
    AGENCY_EMOJI_H = 32 * S                         # rendered height of emoji in agency block

    agency_name = data.get("agency", "")
    agent_name  = data.get("agent", "")
    phone       = data.get("phone", "")

    right_edge = W - MARGIN
    lines_info = []
    for txt, weight, size, emoji_key in [
        (agency_name, cairo.FONT_WEIGHT_BOLD,   AGENCY_FONT_SIZES[0], None),
        (agent_name,  cairo.FONT_WEIGHT_NORMAL, AGENCY_FONT_SIZES[1], "_agency_agent_emoji_pos"),
        (phone,       cairo.FONT_WEIGHT_NORMAL, AGENCY_FONT_SIZES[2], "_agency_phone_emoji_pos"),
    ]:
        if not txt:
            continue
        ctx.select_font_face("Poppins", cairo.FONT_SLANT_NORMAL, weight)
        ctx.set_font_size(size)
        te = ctx.text_extents(txt)
        lines_info.append((txt, weight, size, te, emoji_key))

    if lines_info:
        max_w = max(
            (li[3].width + (AGENCY_EMOJI_W if li[4] else 0))
            for li in lines_info
        )
        block_w = max_w + AGENCY_PAD * 2
        block_h = len(lines_info) * AGENCY_LINE_GAP + AGENCY_PAD
        block_x = right_edge - block_w
        block_y = pill_top_y

        # Dark translucent background
        ctx.set_source_rgba(0.04, 0.08, 0.16, 0.70)    # ← change 0.70 for opacity
        rounded_rect(ctx, block_x, block_y, block_w, block_h, 12 * S)
        ctx.fill()

        # Gold left accent bar
        ctx.set_source(gold_gradient(ctx, block_x, block_y, block_x, block_y + block_h))
        ctx.rectangle(block_x, block_y + 8 * S, 4 * S, block_h - 16 * S)
        ctx.fill()

        # Draw each line of text
        ty = block_y + AGENCY_PAD + lines_info[0][3].height  # first baseline
        for txt, weight, size, te, emoji_key in lines_info:
            ctx.select_font_face("Poppins", cairo.FONT_SLANT_NORMAL, weight)
            ctx.set_font_size(size)
            ctx.set_source_rgb(*WHITE)
            x_off = AGENCY_EMOJI_W if emoji_key else 0
            ctx.move_to(block_x + AGENCY_PAD + x_off, ty)
            ctx.show_text(txt)
            if emoji_key:
                # Store top-left position for the Pillow emoji pass
                ex = int(block_x + AGENCY_PAD)
                ey = int(ty + te.y_bearing + te.height / 2 - AGENCY_EMOJI_H / 2)
                data[emoji_key] = (ex, ey)
            ty += AGENCY_LINE_GAP

    # ==================================================================
    # BOTTOM BAR TEXT — Price, Title, Features, Location.
    #
    # Cairo's move_to sets the TEXT BASELINE (bottom of letters).
    # So we measure text height and add it to get the correct baseline.
    #
    # To change font sizes: edit PRICE_FONT_SIZE, TITLE_FONT_SIZE, etc.
    # To change vertical spacing between lines: edit the += values.
    # To change left margin: edit bx (or the global MARGIN constant).
    # ==================================================================
    PRICE_FONT_SIZE = 62 * S           # ← price text size
    TITLE_FONT_SIZE = 36 * S           # ← title text size
    PRICE_TITLE_GAP = 18 * S           # ← gap between price and title
    TITLE_FEATURES_GAP = 20 * S        # ← gap between title and features line
    FEATURES_LOCATION_GAP = 14 * S     # ← gap between features and location

    bx = MARGIN                        # left margin for all bottom text
    by = bottom_y + 24 * S             # start below the top edge of the bar

    # ── Price (gold gradient) ──
    price = data.get("price", "")
    if price:
        ctx.select_font_face("Poppins", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(PRICE_FONT_SIZE)
        te = ctx.text_extents(price)
        by += te.height                # move to baseline (Cairo draws from baseline)
        ctx.set_source(gold_gradient(ctx, bx, by - te.height, bx + te.width, by))
        ctx.move_to(bx, by)
        ctx.show_text(price)
        by += PRICE_TITLE_GAP

    # ── Title (white) ──
    title = data.get("title", "")
    if title:
        ctx.select_font_face("Poppins", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(TITLE_FONT_SIZE)
        te = ctx.text_extents(title)
        by += te.height
        ctx.set_source_rgb(*WHITE)
        ctx.move_to(bx, by)
        ctx.show_text(title)
        by += TITLE_FEATURES_GAP

    # ── Features line (emojis — drawn by Pillow later) ──
    data["_features_y"] = by           # Pillow reads this to place the emoji line
    by += 42 * S                       # reserve space for emoji line height

    # ── Location (drawn by Pillow later) ──
    by += FEATURES_LOCATION_GAP
    data["_location_y"] = by


# ---------------------------------------------------------------------------
# Pillow emoji pass — draws features line and location with color emojis.
# Cairo can't render color emoji fonts, so we use Pillow for these lines.
# ---------------------------------------------------------------------------
def draw_features_pil(pil_img, data):
    """
    Draws the features line (rooms, baths, area) and location with emojis.

    To change font sizes: edit FEATURES_FONT_SIZE and LOCATION_FONT_SIZE.
    To change emoji size: edit EMOJI_DISPLAY_H.
    To change separator dot size: edit the ellipse radius below.
    """
    draw = ImageDraw.Draw(pil_img)

    # ==================================================================
    # FEATURES & LOCATION FONT SIZES (Pillow / emoji section)
    # ==================================================================
    FEATURES_FONT_SIZE = 28 * S    # ← text next to emojis (e.g. "4 Hab")
    LOCATION_FONT_SIZE = 24 * S    # ← location text (e.g. "Polanco, CDMX")
    EMOJI_DISPLAY_H    = 32 * S    # ← rendered emoji height in pixels

    try:
        font_feat = ImageFont.truetype(FONT_MEDIUM, FEATURES_FONT_SIZE)
    except OSError:
        font_feat = ImageFont.load_default()
    try:
        font_loc = ImageFont.truetype(FONT_LIGHT, LOCATION_FONT_SIZE)
    except OSError:
        font_loc = font_feat
    try:
        font_emoji = ImageFont.truetype(FONT_EMOJI, 109)  # native emoji size
    except OSError:
        font_emoji = None

    emoji_h = EMOJI_DISPLAY_H
    x_start = MARGIN
    gold_pil = (0xC8, 0x96, 0x3E)
    white_pil = (255, 255, 255)

    def _paste_emoji(emoji_ch, x, y, height=None):
        h = height if height is not None else emoji_h
        if not font_emoji:
            draw.text((x, y), emoji_ch, font=font_feat, fill="white")
            bb = font_feat.getbbox(emoji_ch)
            return (bb[2] - bb[0]) + 2 * S
        tmp = Image.new("RGBA", (150, 150), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((5, 5), emoji_ch, font=font_emoji, embedded_color=True)
        bbox = tmp.getbbox()
        if not bbox:
            return 0
        crop = tmp.crop(bbox)
        ratio = h / crop.height
        new_w = int(crop.width * ratio)
        crop = crop.resize((new_w, h), Image.LANCZOS)
        pil_img.paste(crop, (int(x), int(y)), crop)
        return new_w + 4 * S

    # Features line
    feat_y = int(data.get("_features_y", H - 150 * S))
    rooms = data.get("rooms", 0)
    baths = data.get("baths", 0)
    area  = data.get("area", 0)

    items = []
    if rooms:
        items.append(("\U0001F6CF\uFE0F", f" {rooms} Hab"))
    if baths:
        items.append(("\U0001F6BF", f" {baths} Baños"))
    if area:
        area_s = f"{int(area)}" if isinstance(area, int) or float(area) == int(float(area)) else f"{area}"
        items.append(("\U0001F4D0", f" {area_s} m\u00B2"))

    x = x_start
    for i, (emoji_ch, label) in enumerate(items):
        ew = _paste_emoji(emoji_ch, x, feat_y)
        x += ew
        draw.text((x, feat_y - 2 * S), label, font=font_feat, fill=white_pil)
        tb = font_feat.getbbox(label)
        x += (tb[2] - tb[0])
        if i < len(items) - 1:
            x += 14 * S
            dot_y = feat_y + emoji_h // 2
            draw.ellipse([x, dot_y - 3*S, x + 6*S, dot_y + 3*S], fill=gold_pil)
            x += 20 * S

    # Location line
    loc_y = int(data.get("_location_y", H - 100 * S))
    location = data.get("location", "")
    if location:
        x = x_start
        ew = _paste_emoji("\U0001F4CD", x, loc_y)
        x += ew + 6 * S                             # ← gap between pin and location text
        draw.text((x, loc_y - 2 * S), location, font=font_loc, fill=(255, 255, 255, 200))

    # Agency block emojis — rendered by Pillow since Cairo can't handle color emoji
    # Both use the same explicit height so they appear visually equal regardless of glyph density.
    AGENCY_EMOJI_DISPLAY_H = 24 * S
    # Woman in suit, light skin tone (👩🏻‍💼) before agent name
    agent_emoji_pos = data.get("_agency_agent_emoji_pos")
    if agent_emoji_pos:
        _paste_emoji("\U0001F469\U0001F3FB\u200D\U0001F4BC", agent_emoji_pos[0], agent_emoji_pos[1],
                     height=AGENCY_EMOJI_DISPLAY_H)

    # Red telephone (☎) before phone number
    phone_emoji_pos = data.get("_agency_phone_emoji_pos")
    if phone_emoji_pos:
        _paste_emoji("\U0000260E", phone_emoji_pos[0], phone_emoji_pos[1],
                     height=AGENCY_EMOJI_DISPLAY_H)

    return pil_img


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def generate_listing(data, output_path="listing.png"):
    photo_surface = None
    photo_path = data.get("photo")
    if photo_path and os.path.isfile(photo_path):
        pil_photo = Image.open(photo_path).convert("RGBA")
        photo_surface, _buf = _pil_to_cairo(pil_photo)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surface)
    ctx.set_antialias(cairo.ANTIALIAS_BEST)
    draw_template(ctx, data, photo_surface)

    buf = surface.get_data()
    pil_img = Image.frombuffer("RGBA", (W, H), bytes(buf), "raw", "BGRA", 0, 1)
    pil_img = draw_features_pil(pil_img, data)
    pil_img = pil_img.resize((CANVAS, CANVAS), Image.LANCZOS)
    pil_img.save(output_path, "PNG", optimize=True)
    print(f"[OK] Listing saved to: {output_path}")
    return output_path


def _pil_to_cairo(pil_img):
    w, h = pil_img.size
    data = bytearray(w * h * 4)
    try:
        import numpy as np
        arr = np.array(pil_img)
        r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]
        af = a.astype(np.float32) / 255.0
        out = np.zeros((h, w, 4), dtype=np.uint8)
        out[:,:,0] = (b * af).astype(np.uint8)
        out[:,:,1] = (g * af).astype(np.uint8)
        out[:,:,2] = (r * af).astype(np.uint8)
        out[:,:,3] = a
        data = bytearray(out.tobytes())
    except ImportError:
        pixels = pil_img.load()
        for y in range(h):
            for x in range(w):
                rv, gv, bv, av = pixels[x, y]
                af = av / 255.0
                idx = (y * w + x) * 4
                data[idx+0] = int(bv * af)
                data[idx+1] = int(gv * af)
                data[idx+2] = int(rv * af)
                data[idx+3] = av
    surface = cairo.ImageSurface.create_for_data(
        data, cairo.FORMAT_ARGB32, w, h, w * 4
    )
    return surface, data


# ---------------------------------------------------------------------------
# XML
# ---------------------------------------------------------------------------
SAMPLE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<listing>
    <!-- Property information -->
    <price>$4,500,000 MXN</price>
    <title>Casa Moderna en Polanco</title>
    <location>Polanco, CDMX</location>
    <rooms>4</rooms>
    <baths>3</baths>
    <area>320</area>
    <property_type>Casa en Venta</property_type>

    <!-- Agent / Agency information -->
    <agency>Prestige Real Estate</agency>
    <agent>María López</agent>
    <phone>+52 55 1234 5678</phone>

    <!-- Optional: path to property photo (leave empty for placeholder) -->
    <photo></photo>
</listing>
"""


def parse_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    data = {}
    for field in ["price", "title", "location", "rooms", "baths",
                   "area", "address", "agency", "agent", "phone", "photo",
                   "property_type"]:
        elem = root.find(field)
        if elem is not None and elem.text and elem.text.strip():
            val = elem.text.strip()
            if field in ("rooms", "baths", "area"):
                try:
                    val = int(val)
                except ValueError:
                    try:
                        val = float(val)
                    except ValueError:
                        pass
            data[field] = val
    return data


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Real Estate Listing Template Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--xml", type=str, help="Path to XML data file")
    parser.add_argument("--sample-xml", action="store_true",
                        help="Print a sample XML template to stdout and exit")

    parser.add_argument("--price", type=str, help="Property price")
    parser.add_argument("--title", type=str, help="Property title")
    parser.add_argument("--location", type=str, help="General location")
    parser.add_argument("--rooms", type=int, help="Number of rooms")
    parser.add_argument("--baths", type=int, help="Number of bathrooms")
    parser.add_argument("--area", type=float, help="Area in m²")
    parser.add_argument("--address", type=str, help="Full address")
    parser.add_argument("--agency", type=str, help="Agency name")
    parser.add_argument("--agent", type=str, help="Agent name")
    parser.add_argument("--phone", type=str, help="Agent phone number")
    parser.add_argument("--photo", type=str, help="Path to property photo")
    parser.add_argument("--property-type", type=str, dest="property_type",
                        help="Property type label (e.g. 'Casa en Venta')")

    parser.add_argument("--output", "-o", type=str, default="listing.png",
                        help="Output PNG file path (default: listing.png)")

    args = parser.parse_args()

    if args.sample_xml:
        print(SAMPLE_XML)
        sys.exit(0)

    if args.xml:
        if not os.path.isfile(args.xml):
            print(f"Error: XML file not found: {args.xml}", file=sys.stderr)
            sys.exit(1)
        data = parse_xml(args.xml)
        print(f"[INFO] Loaded data from XML: {args.xml}")
    else:
        data = {}
        for field in ["price", "title", "location", "rooms", "baths",
                       "area", "address", "agency", "agent", "phone", "photo",
                       "property_type"]:
            val = getattr(args, field, None)
            if val is not None:
                data[field] = val

    if not data:
        print("Error: No data provided. Use --xml <file> or --price/--title/... flags.")
        print("       Run with --sample-xml to see the XML format.")
        print("       Run with -h for full help.")
        sys.exit(1)

    generate_listing(data, args.output)


if __name__ == "__main__":
    main()
