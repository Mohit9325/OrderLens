import os
import math
from PIL import Image, ImageDraw, ImageFont

def generate_high_res_assets():
    os.makedirs("assets", exist_ok=True)

    # 1. High-Res Logo: 1200 x 300 px (Rendered at 50px height for ultra-crisp resolution)
    logo_w, logo_h = 1200, 300
    logo_img = Image.new("RGBA", (logo_w, logo_h), (255, 255, 255, 0))
    draw = ImageDraw.Draw(logo_img)

    # Hexagonal Tech Icon (Scaled 3x)
    cx, cy, r = 140, 150, 105
    points = []
    for i in range(6):
        angle_deg = 60 * i - 30
        angle_rad = math.radians(angle_deg)
        x = cx + r * math.cos(angle_rad)
        y = cy + r * math.sin(angle_rad)
        points.append((x, y))

    draw.polygon(points, fill="#0F172A", outline="#B91C1C", width=8)

    inner_points = []
    for i in range(6):
        angle_deg = 60 * i - 30
        angle_rad = math.radians(angle_deg)
        x = cx + (r * 0.55) * math.cos(angle_rad)
        y = cy + (r * 0.55) * math.sin(angle_rad)
        inner_points.append((x, y))
    draw.polygon(inner_points, fill="#B91C1C")

    draw.line([(cx, cy - r), (cx, cy + r)], fill="#EF4444", width=5)
    draw.line([(cx - r * 0.866, cy), (cx + r * 0.866, cy)], fill="#EF4444", width=5)
    draw.ellipse([(cx - 15, cy - 15), (cx + 15, cy + 15)], fill="#FFFFFF")

    # High-Res Typography
    try:
        font_main = ImageFont.truetype("arialbd.ttf", 72)
        font_sub = ImageFont.truetype("arial.ttf", 26)
    except:
        try:
            font_main = ImageFont.truetype("arial.ttf", 72)
            font_sub = ImageFont.truetype("arial.ttf", 26)
        except:
            font_main = ImageFont.load_default()
            font_sub = ImageFont.load_default()

    draw.text((290, 70), "AI TURING", fill="#0F172A", font=font_main)
    draw.text((660, 70), "TECHNOLOGIES", fill="#B91C1C", font=font_main)
    draw.text((295, 168), "AUTONOMOUS ENTERPRISE PROCUREMENT", fill="#64748B", font=font_sub)

    for p in ["assets/logo.png", "assets/aituring_logo.png", "logo.png"]:
        logo_img.save(p, "PNG")

    # 2. High-Res Stamp & Signature: 900 x 420 px
    stamp_w, stamp_h = 900, 420
    stamp_img = Image.new("RGBA", (stamp_w, stamp_h), (255, 255, 255, 0))
    s_draw = ImageDraw.Draw(stamp_img)

    # Circular Corporate Seal Stamp
    seal_cx, seal_cy, seal_r = 190, 210, 160
    s_draw.ellipse(
        [(seal_cx - seal_r, seal_cy - seal_r), (seal_cx + seal_r, seal_cy + seal_r)],
        outline="#991B1B",
        width=8
    )
    s_draw.ellipse(
        [(seal_cx - seal_r + 14, seal_cy - seal_r + 14), (seal_cx + seal_r - 14, seal_cy + seal_r - 14)],
        outline="#DC2626",
        width=3
    )

    try:
        font_seal_top = ImageFont.truetype("arialbd.ttf", 22)
        font_seal_center = ImageFont.truetype("arialbd.ttf", 26)
        font_sig = ImageFont.truetype("arialbd.ttf", 52)
        font_label = ImageFont.truetype("arialbd.ttf", 22)
    except:
        font_seal_top = ImageFont.load_default()
        font_seal_center = ImageFont.load_default()
        font_sig = ImageFont.load_default()
        font_label = ImageFont.load_default()

    s_draw.text((85, 110), "AITURING TECH", fill="#991B1B", font=font_seal_top)
    s_draw.text((80, 195), "★ VERIFIED ★", fill="#B91C1C", font=font_seal_center)
    s_draw.text((105, 280), "PVT LTD", fill="#991B1B", font=font_seal_top)

    # Digital Signature Line Script
    sig_start_x = 400
    s_draw.line([(sig_start_x, 175), (sig_start_x + 60, 120), (sig_start_x + 105, 195), 
                 (sig_start_x + 160, 110), (sig_start_x + 225, 185), (sig_start_x + 290, 130),
                 (sig_start_x + 370, 160)], fill="#1E293B", width=7)
    
    s_draw.line([(sig_start_x + 50, 210), (sig_start_x + 390, 195)], fill="#B91C1C", width=5)
    s_draw.text((sig_start_x + 15, 60), "A. Turing", fill="#0F172A", font=font_sig)

    # Verification Tag
    s_draw.rectangle([(sig_start_x + 25, 250), (sig_start_x + 430, 310)], fill="#FEF2F2", outline="#F87171", width=3)
    s_draw.text((sig_start_x + 40, 265), "DIGITALLY SIGNED & SEALED", fill="#991B1B", font=font_label)

    for p in ["assets/stamp.png", "assets/aituring_stamp_signature.png", "stamp.png"]:
        stamp_img.save(p, "PNG")

    print("Ultra high-resolution assets generated successfully!")

if __name__ == "__main__":
    generate_high_res_assets()
