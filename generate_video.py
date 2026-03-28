#!/usr/bin/env python3
"""
禅園 四月紫紺コース前菜 ― 季節感のあるSNS動画生成スクリプト
Instagram Reels / Stories 向け 1080x1920 (9:16) MP4
"""

import os
import math
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── 設定 ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "posts", "2026-04-seasonal-menu", "images")
OUTPUT_MP4 = os.path.join(BASE_DIR, "posts", "2026-04-seasonal-menu", "shikon-zensai-reel.mp4")
FRAME_DIR = "/tmp/zenen_video_frames"
os.makedirs(FRAME_DIR, exist_ok=True)

# 動画設定
W, H = 1080, 1920  # 9:16 縦型
FPS = 30
TOTAL_SECONDS = 15
TOTAL_FRAMES = FPS * TOTAL_SECONDS

# フォント
FONT_PATH = "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"

# カラーパレット（紫紺コースに合わせた深い和の色調）
BG_COLOR = (28, 18, 12)        # 漆黒に近い深茶
ACCENT_COLOR = (61, 43, 86)    # 紫紺
TEXT_COLOR = (240, 235, 225)    # 温かみのある白
SUB_TEXT_COLOR = (180, 168, 150)  # 薄墨色
GOLD_COLOR = (195, 170, 120)   # 金


def ease_in_out(t):
    """スムーズなイージング"""
    return t * t * (3 - 2 * t)


def create_gradient_bg(w, h, top_color, bottom_color):
    """縦グラデーション背景"""
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        ratio = y / h
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def draw_centered_text(draw, text, y, font, fill, w=W):
    """中央揃えテキスト描画"""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (w - tw) // 2
    draw.text((x, y), text, font=font, fill=fill)


def draw_text_with_shadow(draw, text, y, font, fill, shadow_color=(0,0,0,80), w=W):
    """影付き中央揃えテキスト"""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (w - tw) // 2
    # 影
    for dx, dy in [(2, 2), (1, 1)]:
        draw.text((x + dx, y + dy), text, font=font, fill=shadow_color[:3])
    draw.text((x, y), text, font=font, fill=fill)


def draw_vertical_text(draw, text, x, y, font, fill, spacing=8):
    """縦書きテキスト"""
    for i, ch in enumerate(text):
        # 句読点の位置調整
        offset_x = 0
        if ch in "、。":
            offset_x = int(font.size * 0.5)
        bbox = draw.textbbox((0, 0), ch, font=font)
        ch_w = bbox[2] - bbox[0]
        ch_h = bbox[3] - bbox[1]
        cx = x - ch_w // 2 + offset_x
        draw.text((cx, y + i * (ch_h + spacing)), ch, font=font, fill=fill)


def load_photo(name):
    """写真読み込み"""
    path = os.path.join(IMG_DIR, name)
    if os.path.exists(path):
        return Image.open(path).convert("RGB")
    return None


def crop_center_square(img):
    """中央正方形クロップ"""
    w, h = img.size
    s = min(w, h)
    left = (w - s) // 2
    top = (h - s) // 2
    return img.crop((left, top, left + s, top + s))


def ken_burns(img, target_w, target_h, progress, zoom_start=1.0, zoom_end=1.15, pan_x=0, pan_y=0):
    """Ken Burns エフェクト（ゆっくりズーム＋パン）"""
    t = ease_in_out(progress)
    zoom = zoom_start + (zoom_end - zoom_start) * t

    # ズーム適用
    iw, ih = img.size
    new_w = int(iw * zoom)
    new_h = int(ih * zoom)
    resized = img.resize((new_w, new_h), Image.LANCZOS)

    # パン適用
    cx = new_w // 2 + int(pan_x * t)
    cy = new_h // 2 + int(pan_y * t)

    left = cx - target_w // 2
    top = cy - target_h // 2
    left = max(0, min(left, new_w - target_w))
    top = max(0, min(top, new_h - target_h))

    return resized.crop((left, top, left + target_w, top + target_h))


def draw_decorative_line(draw, y, w, color, length=120, thickness=1):
    """装飾線"""
    cx = w // 2
    draw.line([(cx - length // 2, y), (cx + length // 2, y)], fill=color, width=thickness)


def draw_sakura_petal(draw, cx, cy, size, color, alpha_factor=1.0):
    """簡易桜花びら"""
    r = int(color[0])
    g = int(color[1])
    b = int(color[2])
    c = (r, g, b)
    # 花びらを楕円で表現
    draw.ellipse([cx - size, cy - size // 3, cx + size, cy + size // 3], fill=c)
    draw.ellipse([cx - size // 3, cy - size, cx + size // 3, cy + size], fill=c)


# ── メイン動画生成 ──
def generate_frames():
    print("写真を読み込み中...")
    photo1 = load_photo("shikon-zensai.jpg")
    photo2 = load_photo("shikon-zensai-02.jpg")

    if not photo1 or not photo2:
        print("ERROR: 画像が見つかりません")
        return

    # 写真の準備 - 正方形にクロップしてリサイズ
    photo1_sq = crop_center_square(photo1).resize((W, W), Image.LANCZOS)
    photo2_sq = crop_center_square(photo2).resize((W, W), Image.LANCZOS)

    # フォント準備
    font_title = ImageFont.truetype(FONT_PATH, 52)
    font_sub = ImageFont.truetype(FONT_PATH, 32)
    font_small = ImageFont.truetype(FONT_PATH, 26)
    font_tag = ImageFont.truetype(FONT_PATH, 22)
    font_large = ImageFont.truetype(FONT_PATH, 64)
    font_vert = ImageFont.truetype(FONT_PATH, 36)

    # 桜花びらのパラメータ（ランダム風に固定値で）
    import random
    random.seed(42)
    petals = []
    for _ in range(15):
        petals.append({
            "x": random.randint(0, W),
            "y_start": random.randint(-300, -50),
            "speed": random.uniform(0.8, 2.0),
            "sway": random.uniform(20, 60),
            "sway_speed": random.uniform(0.5, 1.5),
            "size": random.randint(4, 10),
            "alpha": random.uniform(0.3, 0.8),
        })

    print(f"フレーム生成中... ({TOTAL_FRAMES}フレーム)")

    for frame_idx in range(TOTAL_FRAMES):
        t_global = frame_idx / TOTAL_FRAMES  # 0.0 ~ 1.0
        t_sec = frame_idx / FPS

        # ── シーン構成 ──
        # 0.0 - 0.15: オープニング（タイトル + フェードイン）
        # 0.15 - 0.50: 写真1 Ken Burns + テキスト
        # 0.50 - 0.55: トランジション
        # 0.55 - 0.85: 写真2 Ken Burns + テキスト
        # 0.85 - 1.0: エンディング

        frame = Image.new("RGB", (W, H), BG_COLOR)
        draw = ImageDraw.Draw(frame)

        # ── シーン1: オープニング ──
        if t_global < 0.18:
            scene_t = t_global / 0.18
            fade = ease_in_out(min(scene_t * 2, 1.0))

            # 深い背景グラデーション
            frame = create_gradient_bg(W, H, (15, 10, 8), (35, 25, 18))
            draw = ImageDraw.Draw(frame)

            # 桜花びら
            for p in petals:
                py = p["y_start"] + t_sec * p["speed"] * 200
                px = p["x"] + math.sin(t_sec * p["sway_speed"]) * p["sway"]
                py_mod = py % (H + 300) - 150
                petal_color = (230, 180, 190)
                if 0 < py_mod < H:
                    draw_sakura_petal(draw, int(px), int(py_mod), p["size"], petal_color)

            # テキストフェードイン
            alpha_val = int(255 * fade)
            text_color_f = (TEXT_COLOR[0], TEXT_COLOR[1], TEXT_COLOR[2])

            if fade > 0.1:
                # 「卯月」
                draw_centered_text(draw, "― 卯月 ―", 680, font_sub, SUB_TEXT_COLOR)

                # メインタイトル（縦書き風に横書きで2行）
                draw_centered_text(draw, "移ろう季節を、", 760, font_title, text_color_f)
                draw_centered_text(draw, "一皿に込めて。", 830, font_title, text_color_f)

                # 装飾線
                draw_decorative_line(draw, 920, W, GOLD_COLOR, 100, 1)

                # サブテキスト
                if fade > 0.5:
                    draw_centered_text(draw, "禅 園", 960, font_sub, GOLD_COLOR)
                    draw_centered_text(draw, "紫紺コース ・ 前菜", 1010, font_small, SUB_TEXT_COLOR)

        # ── シーン2: 写真1 + テキスト ──
        elif t_global < 0.52:
            scene_t = (t_global - 0.18) / 0.34
            fade_in = ease_in_out(min(scene_t * 3, 1.0))
            fade_out = ease_in_out(max(0, (scene_t - 0.85) / 0.15)) if scene_t > 0.85 else 0

            frame = create_gradient_bg(W, H, (20, 14, 10), (30, 22, 16))
            draw = ImageDraw.Draw(frame)

            # 桜花びら（背景）
            for p in petals[:5]:
                py = p["y_start"] + t_sec * p["speed"] * 150
                px = p["x"] + math.sin(t_sec * p["sway_speed"]) * p["sway"]
                py_mod = py % (H + 300) - 150
                if 0 < py_mod < H:
                    draw_sakura_petal(draw, int(px), int(py_mod), p["size"], (230, 180, 190))

            # 写真1 Ken Burns
            photo_h = int(W * 0.85)
            photo_display = ken_burns(photo1_sq, W - 80, photo_h, scene_t,
                                      zoom_start=1.0, zoom_end=1.12, pan_x=30, pan_y=-20)

            # 写真の位置
            photo_y = 280
            frame.paste(photo_display, (40, photo_y))

            # 写真の上下に細い金線
            draw.line([(40, photo_y - 2), (W - 40, photo_y - 2)], fill=GOLD_COLOR, width=1)
            draw.line([(40, photo_y + photo_h + 1), (W - 40, photo_y + photo_h + 1)], fill=GOLD_COLOR, width=1)

            # 上部テキスト
            draw_centered_text(draw, "四月の旬菜", 120, font_sub, GOLD_COLOR)
            draw_decorative_line(draw, 170, W, GOLD_COLOR, 60, 1)
            draw_centered_text(draw, "紫紺コース ・ 前菜", 195, font_small, SUB_TEXT_COLOR)

            # 下部テキスト
            text_y = photo_y + photo_h + 60
            if fade_in > 0.3:
                draw_centered_text(draw, "桜が綻び、山菜が芽吹く四月。", text_y, font_small, TEXT_COLOR)
                draw_centered_text(draw, "この一瞬の「旬」を逃さず", text_y + 50, font_small, TEXT_COLOR)
                draw_centered_text(draw, "お皿の上に表現いたします。", text_y + 100, font_small, TEXT_COLOR)

            # 下部装飾
            draw_decorative_line(draw, text_y + 170, W, GOLD_COLOR, 40, 1)
            draw_centered_text(draw, "禅 園", text_y + 195, font_tag, GOLD_COLOR)

        # ── シーン3: トランジション ──
        elif t_global < 0.57:
            scene_t = (t_global - 0.52) / 0.05
            fade = ease_in_out(scene_t)

            frame = create_gradient_bg(W, H, (20, 14, 10), (30, 22, 16))
            draw = ImageDraw.Draw(frame)

            # 装飾線が伸びるアニメーション
            line_len = int(200 * fade)
            draw_decorative_line(draw, H // 2, W, GOLD_COLOR, line_len, 1)

        # ── シーン4: 写真2 + テキスト ──
        elif t_global < 0.85:
            scene_t = (t_global - 0.57) / 0.28
            fade_in = ease_in_out(min(scene_t * 3, 1.0))

            frame = create_gradient_bg(W, H, (18, 12, 10), (32, 24, 18))
            draw = ImageDraw.Draw(frame)

            # 桜花びら
            for p in petals[5:12]:
                py = p["y_start"] + t_sec * p["speed"] * 180
                px = p["x"] + math.sin(t_sec * p["sway_speed"]) * p["sway"]
                py_mod = py % (H + 300) - 150
                if 0 < py_mod < H:
                    draw_sakura_petal(draw, int(px), int(py_mod), p["size"], (230, 180, 190))

            # 写真2 Ken Burns（逆方向）
            photo_h = int(W * 0.85)
            photo_display = ken_burns(photo2_sq, W - 80, photo_h, scene_t,
                                      zoom_start=1.08, zoom_end=1.0, pan_x=-20, pan_y=15)

            photo_y = 350
            frame.paste(photo_display, (40, photo_y))
            draw.line([(40, photo_y - 2), (W - 40, photo_y - 2)], fill=GOLD_COLOR, width=1)
            draw.line([(40, photo_y + photo_h + 1), (W - 40, photo_y + photo_h + 1)], fill=GOLD_COLOR, width=1)

            # 上部：縦書き風キャッチ
            draw_centered_text(draw, "旬 を 届 け る", 140, font_sub, GOLD_COLOR)
            draw_decorative_line(draw, 195, W, GOLD_COLOR, 80, 1)
            draw_centered_text(draw, "目で愉しみ、舌で味わう", 230, font_small, SUB_TEXT_COLOR)

            # 下部テキスト
            text_y = photo_y + photo_h + 50
            if fade_in > 0.3:
                draw_centered_text(draw, "翡翠色の豆、桜葉の包み、", text_y, font_small, TEXT_COLOR)
                draw_centered_text(draw, "三色の手毬、いくらの彩り。", text_y + 45, font_small, TEXT_COLOR)
                draw_centered_text(draw, "春の息吹を丁寧に盛り込みました。", text_y + 100, font_small, TEXT_COLOR)

        # ── シーン5: エンディング ──
        else:
            scene_t = (t_global - 0.85) / 0.15
            fade_in = ease_in_out(min(scene_t * 2, 1.0))

            frame = create_gradient_bg(W, H, (12, 8, 6), (28, 20, 15))
            draw = ImageDraw.Draw(frame)

            # 桜花びら（多め）
            for p in petals:
                py = p["y_start"] + t_sec * p["speed"] * 200
                px = p["x"] + math.sin(t_sec * p["sway_speed"]) * p["sway"]
                py_mod = py % (H + 300) - 150
                if 0 < py_mod < H:
                    draw_sakura_petal(draw, int(px), int(py_mod), p["size"], (230, 180, 190))

            # メインテキスト
            cy = H // 2 - 120
            draw_decorative_line(draw, cy - 30, W, GOLD_COLOR, 60, 1)
            draw_centered_text(draw, "「いま」しか届けられない", cy + 10, font_sub, TEXT_COLOR)
            draw_centered_text(draw, "味わいを。", cy + 60, font_sub, TEXT_COLOR)
            draw_decorative_line(draw, cy + 115, W, GOLD_COLOR, 60, 1)

            # 店名
            if fade_in > 0.3:
                draw_centered_text(draw, "禅 園", cy + 180, font_large, GOLD_COLOR)
                draw_centered_text(draw, "心 斎 橋", cy + 260, font_sub, SUB_TEXT_COLOR)

            # ハッシュタグ
            if fade_in > 0.6:
                draw_centered_text(draw, "#禅園  #旬を届ける  #紫紺コース", cy + 350, font_tag, SUB_TEXT_COLOR)

        # フレーム保存
        frame_path = os.path.join(FRAME_DIR, f"frame_{frame_idx:05d}.png")
        frame.save(frame_path, "PNG")

        if frame_idx % 50 == 0:
            print(f"  {frame_idx}/{TOTAL_FRAMES} フレーム完了")

    print(f"全{TOTAL_FRAMES}フレーム生成完了")


def encode_video():
    print("MP4エンコード中...")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(FRAME_DIR, "frame_%05d.png"),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        OUTPUT_MP4
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    size_mb = os.path.getsize(OUTPUT_MP4) / (1024 * 1024)
    print(f"動画生成完了: {OUTPUT_MP4}")
    print(f"ファイルサイズ: {size_mb:.1f} MB")


if __name__ == "__main__":
    generate_frames()
    encode_video()
    # フレーム画像をクリーンアップ
    import shutil
    shutil.rmtree(FRAME_DIR, ignore_errors=True)
    print("完了!")
