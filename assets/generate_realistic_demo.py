#!/usr/bin/env python3
"""
Generate realistic side-by-side macOS Terminal recording.
Resolution: 1280x720 (720p 16:9).
Duration: 10.0 seconds (100 frames @ 10 fps).
Aesthetic: Authentic macOS Terminal.app / zsh interface. No AI slop.
"""

import os
import subprocess
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1280, 720
TOTAL_FRAMES = 100  # 10.0 seconds @ 10 fps
FPS = 10

# Authentic macOS dark terminal colors
BG_DESKTOP = (18, 20, 24)        # Deep macOS dark desktop background
TERM_BG = (24, 25, 27)           # Terminal window background
TITLEBAR_BG = (38, 39, 42)       # Titlebar background
TITLEBAR_BORDER = (55, 56, 60)   # Titlebar bottom border
BORDER_COLOR = (45, 46, 50)      # Terminal window border
TEXT_TITLE = (170, 172, 178)     # Window title text

# Terminal text colors (Monaco / Menlo palette)
TEXT_WHITE = (235, 237, 240)
TEXT_DIM = (130, 135, 142)
TEXT_PROMPT = (100, 180, 120)     # Greenish prompt symbol or user
TEXT_PATH = (90, 150, 240)       # Blueish path
TEXT_CMD = (245, 245, 245)
TEXT_WARN = (235, 160, 60)
TEXT_ERR = (240, 80, 80)
TEXT_SUCCESS = (80, 200, 120)
TEXT_KEY = (100, 180, 245)
TEXT_STR = (150, 220, 140)
TEXT_VAL = (220, 170, 110)

# Fonts
font_mono = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 13, index=0)
font_mono_bold = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 13, index=1)
font_title = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 12, index=0)

def draw_window_frame(draw, x, y, w, h, title):
    # Shadow
    for i in range(4):
        draw.rounded_rectangle([x - i, y - i, x + w + i, y + h + i], radius=8, outline=(10, 11, 13))
    
    # Base window
    draw.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=TERM_BG, outline=BORDER_COLOR, width=1)
    
    # Titlebar
    draw.rounded_rectangle([x, y, x + w, y + 32], radius=8, fill=TITLEBAR_BG)
    draw.rectangle([x, y + 24, x + w, y + 32], fill=TITLEBAR_BG) # Square off bottom corners of titlebar
    draw.line([x, y + 32, x + w, y + 32], fill=TITLEBAR_BORDER, width=1)
    
    # Traffic light buttons
    draw.ellipse([x + 12, y + 10, x + 24, y + 22], fill=(255, 95, 87), outline=(224, 73, 66))
    draw.ellipse([x + 32, y + 10, x + 44, y + 22], fill=(255, 189, 46), outline=(222, 161, 35))
    draw.ellipse([x + 52, y + 10, x + 64, y + 22], fill=(39, 201, 63), outline=(32, 174, 52))
    
    # Centered Title
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text((x + (w - tw) // 2, y + 9), title, fill=TEXT_TITLE, font=font_title)

def render_frame(frame_idx):
    img = Image.new("RGB", (WIDTH, HEIGHT), color=BG_DESKTOP)
    draw = ImageDraw.Draw(img)

    w_win = 585
    h_win = 650
    y_win = 35
    x_left = 35
    x_right = 660

    # Draw both windows
    draw_window_frame(draw, x_left, y_win, w_win, h_win, "dull@phobosair: ~/code/shrinkwrap — zsh — 80×24")
    draw_window_frame(draw, x_right, y_win, w_win, h_win, "dull@phobosair: ~/code/shrinkwrap — zsh — 80×24")

    # Command typing logic
    target_cmd = "mcp query-postgres --limit 500"
    typed_len = min(len(target_cmd), int(frame_idx * 1.5))
    cur_cmd = target_cmd[:typed_len]
    show_cursor = (frame_idx // 3) % 2 == 0

    # ---------------- LEFT TERMINAL (RAW / NO SHRINKWRAP) ----------------
    lx = x_left + 16
    ly = y_win + 46
    
    draw.text((lx, ly), "dull@phobosair", fill=TEXT_PROMPT, font=font_mono_bold)
    draw.text((lx + 115, ly), "shrinkwrap %", fill=TEXT_PATH, font=font_mono_bold)
    draw.text((lx + 230, ly), cur_cmd, fill=TEXT_CMD, font=font_mono)
    if frame_idx < 22 and show_cursor:
        draw.text((lx + 230 + len(cur_cmd)*8, ly), "█", fill=TEXT_DIM, font=font_mono)

    if frame_idx >= 22:
        ly += 22
        draw.text((lx, ly), "[", fill=TEXT_WHITE, font=font_mono)
        
        # Stream raw JSON rows
        scroll = max(0, int((frame_idx - 22) * 5))
        for r in range(16):
            row_id = r + scroll
            ly += 18
            row_text = f'  {{"id": {row_id}, "user": "usr_{row_id:03d}", "amt": {14.50+row_id*1.2:.2f}, "status": "ok"}},'
            draw.text((lx, ly), row_text, fill=TEXT_DIM, font=font_mono)
        
        ly += 20
        draw.text((lx, ly), "  ... 484 more raw JSON records ...", fill=TEXT_WARN, font=font_mono)
        ly += 18
        draw.text((lx, ly), "]", fill=TEXT_WHITE, font=font_mono)
        
        if frame_idx >= 40:
            ly += 26
            draw.text((lx, ly), "[context-monitor] +28,743 tokens ingested into model window", fill=TEXT_ERR, font=font_mono_bold)
            ly += 18
            draw.text((lx, ly), "[codex-error] 5-hour rate limit exhausted (100% -> 0% in 4m 12s)", fill=TEXT_ERR, font=font_mono_bold)
            ly += 24
            draw.text((lx, ly), "dull@phobosair", fill=TEXT_PROMPT, font=font_mono_bold)
            draw.text((lx + 115, ly), "shrinkwrap %", fill=TEXT_PATH, font=font_mono_bold)
            if show_cursor:
                draw.text((lx + 230, ly), "█", fill=TEXT_WHITE, font=font_mono)

    # ---------------- RIGHT TERMINAL (SHRINKWRAP PROXY) ----------------
    rx = x_right + 16
    ry = y_win + 46

    draw.text((rx, ry), "dull@phobosair", fill=TEXT_PROMPT, font=font_mono_bold)
    draw.text((rx + 115, ry), "shrinkwrap %", fill=TEXT_PATH, font=font_mono_bold)
    draw.text((rx + 230, ry), cur_cmd, fill=TEXT_CMD, font=font_mono)
    if frame_idx < 22 and show_cursor:
        draw.text((rx + 230 + len(cur_cmd)*8, ry), "█", fill=TEXT_DIM, font=font_mono)

    if frame_idx >= 22:
        ry += 22
        draw.text((rx, ry), "[shrinkwrap] stdio proxy intercepted tool response (28,743 -> 178 tokens)", fill=TEXT_SUCCESS, font=font_mono_bold)
        
        compact_lines = [
            ('{', TEXT_WHITE),
            ('  "_shrinkwrap_summary": true,', TEXT_KEY),
            ('  "type": "array",', TEXT_KEY),
            ('  "item_count": 500,', TEXT_KEY),
            ('  "schema_keys": ["id", "user", "amt", "status"],', TEXT_KEY),
            ('  "sample": [{"id": 0, "user": "usr_000", "amt": 14.50, "status": "ok"}],', TEXT_DIM),
            ('  "ref_handle": "sw-ref:a8f2c019d4b2"', TEXT_VAL),
            ('}', TEXT_WHITE)
        ]
        for line, col in compact_lines:
            ry += 18
            draw.text((rx, ry), line, fill=col, font=font_mono)

        if frame_idx >= 38:
            ry += 24
            cmd2 = "shrinkwrap session"
            typed2 = min(len(cmd2), int((frame_idx - 38) * 2))
            draw.text((rx, ry), "dull@phobosair", fill=TEXT_PROMPT, font=font_mono_bold)
            draw.text((rx + 115, ry), "shrinkwrap %", fill=TEXT_PATH, font=font_mono_bold)
            draw.text((rx + 230, ry), cmd2[:typed2], fill=TEXT_CMD, font=font_mono)

            if frame_idx >= 50:
                report_lines = [
                    ("ShrinkWrap Session Token Summary", TEXT_WHITE, True),
                    ("================================", TEXT_DIM, False),
                    ("Tool Invocations:   1", TEXT_WHITE, False),
                    ("Original Tokens:    28,743", TEXT_DIM, False),
                    ("Compacted Tokens:   178", TEXT_DIM, False),
                    ("Tokens Saved:       28,565 (99.38% reduction)", TEXT_SUCCESS, True),
                    ("Est. USD Saved:     $0.0857 USD", TEXT_SUCCESS, False),
                ]
                for r_text, r_col, r_bold in report_lines:
                    ry += 18
                    f = font_mono_bold if r_bold else font_mono
                    draw.text((rx, ry), r_text, fill=r_col, font=f)

                ry += 24
                draw.text((rx, ry), "dull@phobosair", fill=TEXT_PROMPT, font=font_mono_bold)
                draw.text((rx + 115, ry), "shrinkwrap %", fill=TEXT_PATH, font=font_mono_bold)
                if show_cursor:
                    draw.text((rx + 230, ry), "█", fill=TEXT_WHITE, font=font_mono)

    return img

def main():
    print("Rendering 100 realistic frames...")
    frames_dir = "/tmp/shrinkwrap_frames"
    os.makedirs(frames_dir, exist_ok=True)

    frames = []
    for f in range(TOTAL_FRAMES):
        img = render_frame(f)
        frame_path = f"{frames_dir}/frame_{f:03d}.png"
        img.save(frame_path)
        frames.append(img)

    print("Encoding terminal_demo.gif (10 seconds, 10 fps)...")
    gif_path = "/Users/dull/code/synthetic_openfoam_pipeline-main/shrinkwrap/assets/terminal_demo.gif"
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        optimize=True,
        duration=100,  # 100ms per frame = 10 fps
        loop=0
    )

    print("Encoding terminal_demo.mp4 with ffmpeg (h264)...")
    mp4_path = "/Users/dull/code/synthetic_openfoam_pipeline-main/shrinkwrap/assets/terminal_demo.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-framerate", "10",
        "-i", f"{frames_dir}/frame_%03d.png",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "faststart",
        mp4_path
    ]
    subprocess.run(cmd, check=True)
    print("Done! Both GIF and MP4 generated cleanly.")

if __name__ == "__main__":
    main()
