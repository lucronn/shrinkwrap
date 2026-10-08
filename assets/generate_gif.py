from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1000, 500
TOTAL_FRAMES = 26

BG_COLOR = (13, 17, 23)
TERM_BG = (22, 27, 34)
HEADER_BG = (33, 38, 45)
BORDER_COLOR = (48, 54, 61)
TEXT_WHITE = (201, 209, 217)
TEXT_DIM = (139, 148, 158)
TEXT_PROMPT = (88, 166, 255)
TEXT_CMD = (240, 136, 62)
TEXT_GREEN = (63, 185, 80)
TEXT_RED = (248, 81, 73)
TEXT_KEY = (121, 192, 255)
TEXT_VAL = (165, 214, 255)

try:
    font = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", 11)
    font_bold = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", 11)
    font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 15)
except Exception:
    font = font_bold = font_title = ImageFont.load_default()

def truncate_text(text: str, max_chars: int = 38) -> str:
    return text[:max_chars] if len(text) > max_chars else text

def create_terminal_window(width, height, title, render_content_fn, frame_idx):
    # Base terminal window canvas
    win = Image.new("RGB", (width, height), color=TERM_BG)
    draw = ImageDraw.Draw(win)

    # Header bar
    draw.rectangle([0, 0, width, 28], fill=HEADER_BG, outline=BORDER_COLOR, width=1)
    # Window dots
    draw.ellipse([10, 9, 18, 17], fill=(255, 95, 86))
    draw.ellipse([24, 9, 32, 17], fill=(255, 189, 46))
    draw.ellipse([38, 9, 46, 17], fill=(39, 201, 63))
    draw.text((55, 6), truncate_text(title, 34), fill=TEXT_DIM, font=font)

    # Inner body sub-canvas for strictly clipped content
    body_w = width - 16
    body_h = height - 36
    body = Image.new("RGB", (body_w, body_h), color=TERM_BG)
    b_draw = ImageDraw.Draw(body)

    # Render inner content onto body
    render_content_fn(b_draw, body_w, body_h, frame_idx)

    # Strictly crop body to ensure no pixel bleed
    body_cropped = body.crop((0, 0, body_w, body_h))

    # Paste body onto terminal window
    win.paste(body_cropped, (8, 30))
    draw.rectangle([0, 0, width - 1, height - 1], outline=BORDER_COLOR, width=1)
    return win

def render_left_content(draw, w, h, frame_idx):
    y = 5
    draw.text((5, y), "user@agent:~$ ", fill=TEXT_PROMPT, font=font)
    cmd = "mcp-query postgres --limit 500"
    typed_len = min(len(cmd), frame_idx * 3)
    draw.text((95, y), truncate_text(cmd[:typed_len], 30), fill=TEXT_CMD, font=font)

    if frame_idx > 5:
        y += 20
        draw.text((5, y), truncate_text("[RAW PAYLOAD FLOODING CONTEXT]", 36), fill=TEXT_RED, font=font_bold)
        y += 18
        draw.text((5, y), "[", fill=TEXT_WHITE, font=font)

        scroll_offset = (frame_idx - 5) * 4
        for i in range(11):
            idx = i + scroll_offset
            y += 16
            line = f'  {{ "id": {idx:03d}, "usr": "u_{idx%50}", "amt": {14.99+idx*2.5:.2f} }},'
            draw.text((5, y), truncate_text(line, 38), fill=TEXT_DIM, font=font)

        y += 22
        draw.rectangle([5, y, w - 5, y + 26], fill=(50, 20, 20), outline=TEXT_RED)
        draw.text((10, y + 5), truncate_text("❌ CONTEXT: 28,743 TOKENS", 34), fill=TEXT_RED, font=font_bold)

def render_right_content(draw, w, h, frame_idx):
    y = 5
    draw.text((5, y), "user@agent:~$ ", fill=TEXT_PROMPT, font=font)
    cmd = "mcp-query postgres --limit 500"
    typed_len = min(len(cmd), frame_idx * 3)
    draw.text((95, y), truncate_text(cmd[:typed_len], 30), fill=TEXT_CMD, font=font)

    if frame_idx > 5:
        y += 20
        draw.text((5, y), truncate_text("[COMPACTED PAYLOAD - 99.38% SAVED]", 36), fill=TEXT_GREEN, font=font_bold)
        y += 18

        json_lines = [
            ('{', TEXT_WHITE),
            ('  "_shrinkwrap_summary": true,', TEXT_KEY),
            ('  "type": "array",', TEXT_KEY),
            ('  "item_count": 500,', TEXT_KEY),
            ('  "schema_keys": ["id", "usr", "amt"],', TEXT_KEY),
            ('  "sample_items": [', TEXT_KEY),
            ('    { "id": 0, "usr": "u_0", "amt": 14.99 }', TEXT_DIM),
            ('  ],', TEXT_KEY),
            ('  "ref_handle": "sw-ref:128239de1eb2"', TEXT_VAL),
            ('}', TEXT_WHITE)
        ]
        for line, col in json_lines:
            draw.text((5, y), truncate_text(line, 38), fill=col, font=font)
            y += 16

        y += 14
        draw.rectangle([5, y, w - 5, y + 26], fill=(20, 45, 25), outline=TEXT_GREEN)
        draw.text((10, y + 5), truncate_text("✅ CONTEXT: 178 TOKENS (Lossless)", 34), fill=TEXT_GREEN, font=font_bold)

frames = []
w_win = 450
h_win = 420

for frame_idx in range(TOTAL_FRAMES):
    img = Image.new("RGB", (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((WIDTH // 2 - 140, 14), "ShrinkWrap Live Execution Comparison", fill=TEXT_PROMPT, font=font_title)

    # Render left & right windows with strict truncation & sub-canvas cropping
    win_left = create_terminal_window(w_win, h_win, "BEFORE: 28,743 Tokens (Raw Payload)", render_left_content, frame_idx)
    win_right = create_terminal_window(w_win, h_win, "AFTER: 178 Tokens (99.38% Saved)", render_right_content, frame_idx)

    # Paste left window at x=30, right window at x=520 (90px margin between windows)
    img.paste(win_left, (30, 45))
    img.paste(win_right, (520, 45))

    frames.append(img)

frames[0].save(
    "/Users/dull/code/synthetic_openfoam_pipeline-main/shrinkwrap/assets/terminal_demo.gif",
    save_all=True,
    append_images=frames[1:],
    optimize=True,
    duration=90,
    loop=0
)
print("Strictly truncated & cropped GIF generated: assets/terminal_demo.gif")
