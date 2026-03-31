#!/usr/bin/env python3
"""
禅園 四月紫紺コース前菜 ― 季節感のあるSNS動画生成スクリプト
Instagram Reels / Stories 向け 1080x1920 (9:16) MP4

v2: テキストの滑らかなフェード + 写真全面表示
"""

import os
import math
import random
import subprocess
import shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

# ── 設定 ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "posts", "2026-04-seasonal-menu", "images")
OUTPUT_MP4 = os.path.join(BASE_DIR, "posts", "2026-04-seasonal-menu", "shikon-zensai-reel.mp4")
FRAME_DIR = "/tmp/zenen_video_frames"

W, H = 1080, 1920
FPS = 30
TOTAL_SECONDS = 20
TOTAL_FRAMES = FPS * TOTAL_SECONDS

FONT_PATH = "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"

# 明朝体フォント（店名・キャッチコピー等に使用）
FONT_MINCHO = "/usr/share/fonts/truetype/shippori/ShipporiMinchoB1-Medium.ttf"
FONT_MINCHO_SEMIBOLD = "/usr/share/fonts/truetype/shippori/ShipporiMinchoB1-SemiBold.ttf"
FONT_MINCHO_BOLD = "/usr/share/fonts/truetype/shippori/ShipporiMinchoB1-Bold.ttf"

# カラー
TEXT_COLOR = (240, 235, 225)
SUB_TEXT_COLOR = (180, 168, 150)
GOLD_COLOR = (195, 170, 120)


# ── ユーティリティ ──

def ease_in_out(t):
    """滑らかなイージング（5次）"""
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (t * 6 - 15) + 10)


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def load_photo(name):
    path = os.path.join(IMG_DIR, name)
    if os.path.exists(path):
        return Image.open(path).convert("RGB")
    return None


def fit_cover(img, target_w, target_h):
    """CSSのobject-fit: cover相当。画面全体を覆うようリサイズ＋中央クロップ"""
    iw, ih = img.size
    scale = max(target_w / iw, target_h / ih)
    new_w = int(iw * scale)
    new_h = int(ih * scale)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def ken_burns_cover(img, target_w, target_h, progress,
                    zoom_start=1.0, zoom_end=1.10, pan_x=0, pan_y=0):
    """全画面Ken Burns。まずcover fitしてからズーム＋パン"""
    t = ease_in_out(progress)
    zoom = zoom_start + (zoom_end - zoom_start) * t

    # 少し大きめにcover fitしてズーム余白を確保
    base_scale = max(zoom_start, zoom_end) * 1.05
    base = fit_cover(img, int(target_w * base_scale), int(target_h * base_scale))

    # 現在のズームでクロップサイズを計算
    crop_w = int(target_w / zoom * base_scale)
    crop_h = int(target_h / zoom * base_scale)

    bw, bh = base.size
    cx = bw // 2 + int(pan_x * t)
    cy = bh // 2 + int(pan_y * t)

    left = max(0, min(cx - crop_w // 2, bw - crop_w))
    top = max(0, min(cy - crop_h // 2, bh - crop_h))

    cropped = base.crop((left, top, left + crop_w, top + crop_h))
    return cropped.resize((target_w, target_h), Image.LANCZOS)


def create_dark_overlay(base_img, opacity=0.45):
    """写真の上に暗いオーバーレイをかける"""
    overlay = Image.new("RGB", base_img.size, (0, 0, 0))
    return Image.blend(base_img, overlay, opacity)


def create_gradient_overlay(base_img, direction="bottom", strength=0.7):
    """写真の上下にグラデーションの暗幕"""
    w, h = base_img.size
    gradient = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(gradient)

    if direction == "bottom":
        # 下半分を暗くする
        for y in range(h):
            ratio = y / h
            # 上部は透明、下に行くほど暗い
            alpha = int(255 * strength * ease_in_out(max(0, (ratio - 0.3) / 0.7)))
            draw.line([(0, y), (w, y)], fill=alpha)
    elif direction == "top_bottom":
        # 上下を暗く、中央は明るい
        for y in range(h):
            ratio = y / h
            if ratio < 0.25:
                alpha = int(255 * strength * ease_in_out(1.0 - ratio / 0.25))
            elif ratio > 0.65:
                alpha = int(255 * strength * ease_in_out((ratio - 0.65) / 0.35))
            else:
                alpha = 0
            draw.line([(0, y), (w, y)], fill=alpha)
    elif direction == "full":
        gradient = Image.new("L", (w, h), int(255 * strength))

    dark = Image.new("RGB", (w, h), (0, 0, 0))
    # gradient をマスクとしてblend
    result = base_img.copy()
    result.paste(dark, mask=gradient)
    return result


def draw_text_alpha(base, text, xy, font, color, alpha=1.0):
    """アルファ値付きテキスト描画（滑らかなフェード用）"""
    if alpha <= 0.01:
        return base

    # テキスト用の透明レイヤー
    txt_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    txt_draw = ImageDraw.Draw(txt_layer)

    # 影（ソフトシャドウ）
    shadow_color = (0, 0, 0, int(120 * alpha))
    for dx, dy in [(0, 3), (1, 2), (2, 1)]:
        txt_draw.text((xy[0] + dx, xy[1] + dy), text, font=font, fill=shadow_color)

    # 本体
    fill = (color[0], color[1], color[2], int(255 * alpha))
    txt_draw.text(xy, text, font=font, fill=fill)

    # 合成
    if base.mode != "RGBA":
        base = base.convert("RGBA")
    base = Image.alpha_composite(base, txt_layer)
    return base


def draw_centered_text_alpha(base, text, y, font, color, alpha=1.0):
    """中央揃え + アルファフェード"""
    if alpha <= 0.01:
        return base
    draw = ImageDraw.Draw(base)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2
    return draw_text_alpha(base, text, (x, y), font, color, alpha)


def draw_line_alpha(base, y, length, color, alpha=1.0, thickness=1):
    """アルファ値付き装飾線"""
    if alpha <= 0.01:
        return base
    line_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    line_draw = ImageDraw.Draw(line_layer)
    cx = W // 2
    fill = (color[0], color[1], color[2], int(255 * alpha))
    line_draw.line([(cx - length // 2, y), (cx + length // 2, y)],
                   fill=fill, width=thickness)
    if base.mode != "RGBA":
        base = base.convert("RGBA")
    return Image.alpha_composite(base, line_layer)


def draw_sakura_petals(base, petals, t_sec, alpha=1.0):
    """桜花びらをアルファ付きで描画"""
    if alpha <= 0.01:
        return base
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for p in petals:
        py = p["y_start"] + t_sec * p["speed"] * 160
        px = p["x"] + math.sin(t_sec * p["sway_speed"] + p["phase"]) * p["sway"]
        py_mod = py % (H + 400) - 200
        if 0 < py_mod < H:
            size = p["size"]
            a = int(min(p["alpha"] * 255 * alpha, 255))
            c = (235, 195, 205, a)
            # 花びらを丸くソフトに
            draw.ellipse([int(px) - size, int(py_mod) - size // 2,
                          int(px) + size, int(py_mod) + size // 2], fill=c)
    if base.mode != "RGBA":
        base = base.convert("RGBA")
    return Image.alpha_composite(base, layer)


def fade_value(t, start, end, fade_dur=0.12):
    """t が [start, end] 区間で、前後 fade_dur 分だけフェードイン/アウト"""
    if t < start or t > end:
        return 0.0
    inner = (t - start) / (end - start)  # 0..1 within the segment
    fade_in_end = fade_dur / (end - start)
    fade_out_start = 1.0 - fade_dur / (end - start)
    if inner < fade_in_end:
        return ease_in_out(inner / fade_in_end)
    elif inner > fade_out_start:
        return ease_in_out((1.0 - inner) / (1.0 - fade_out_start))
    else:
        return 1.0


# ── メイン ──

def generate_frames():
    print("写真を読み込み中...")
    photo1 = load_photo("shikon-zensai.jpg")
    photo2 = load_photo("shikon-zensai-02.jpg")
    if not photo1 or not photo2:
        print("ERROR: 画像が見つかりません")
        return

    # フォント（明朝体をメインに、情報系はゴシック）
    font_hero = ImageFont.truetype(FONT_MINCHO_SEMIBOLD, 56)      # キャッチコピー
    font_title = ImageFont.truetype(FONT_MINCHO_SEMIBOLD, 44)     # セクションタイトル
    font_sub = ImageFont.truetype(FONT_MINCHO, 30)                # サブテキスト
    font_small = ImageFont.truetype(FONT_MINCHO, 26)              # 本文
    font_large = ImageFont.truetype(FONT_MINCHO_BOLD, 68)         # 店名（大）
    font_tag = ImageFont.truetype(FONT_PATH, 22)                  # ハッシュタグ（ゴシック）
    font_info = ImageFont.truetype(FONT_PATH, 21)                 # 店舗情報（ゴシック）
    font_info_small = ImageFont.truetype(FONT_PATH, 18)           # 小さい情報（ゴシック）

    # 桜花びらパラメータ
    random.seed(42)
    petals = []
    for _ in range(18):
        petals.append({
            "x": random.randint(0, W),
            "y_start": random.randint(-600, -50),
            "speed": random.uniform(0.6, 1.5),
            "sway": random.uniform(25, 70),
            "sway_speed": random.uniform(0.4, 1.2),
            "size": random.randint(5, 12),
            "alpha": random.uniform(0.2, 0.5),
            "phase": random.uniform(0, math.pi * 2),
        })

    os.makedirs(FRAME_DIR, exist_ok=True)
    print(f"フレーム生成中... ({TOTAL_FRAMES}フレーム)")

    # ── タイムライン定義（秒） ──
    # 0.0 -  4.0 : シーン1 写真1全面 + オープニングテキスト
    # 4.0 -  5.0 : クロスフェード (写真1→写真2)
    # 5.0 - 10.0 : シーン2 写真2全面 + テキスト
    # 10.0 - 11.0: クロスフェード (写真2→暗転)
    # 11.0 - 20.0: エンディング（キャッチ + 店舗情報）

    for fi in range(TOTAL_FRAMES):
        t = fi / FPS  # 秒数

        # ── 背景: 写真のKen Burns全面表示 ──

        if t < 5.0:
            # 写真1
            p1 = ken_burns_cover(photo1, W, H, t / 5.0,
                                 zoom_start=1.0, zoom_end=1.08, pan_x=25, pan_y=-15)
            if t < 4.0:
                bg = p1
            else:
                # 4-5秒: クロスフェード
                cross_t = ease_in_out((t - 4.0) / 1.0)
                p2 = ken_burns_cover(photo2, W, H, 0.0,
                                     zoom_start=1.06, zoom_end=1.0, pan_x=-20, pan_y=15)
                bg = Image.blend(p1, p2, cross_t)
        elif t < 11.0:
            # 写真2
            progress2 = (t - 5.0) / 6.0
            bg = ken_burns_cover(photo2, W, H, progress2,
                                 zoom_start=1.06, zoom_end=1.0, pan_x=-20, pan_y=15)
        else:
            # エンディング: 写真2をゆっくり
            progress2 = (t - 5.0) / 15.0
            bg = ken_burns_cover(photo2, W, H, min(progress2, 1.0),
                                 zoom_start=1.06, zoom_end=1.0, pan_x=-20, pan_y=15)

        # ── オーバーレイ（テキストを読みやすく） ──

        if t < 4.0:
            # シーン1: 下部にグラデーション暗幕
            frame = create_gradient_overlay(bg, "bottom", 0.65)
        elif t < 5.0:
            cross_t = (t - 4.0) / 1.0
            ov1 = create_gradient_overlay(bg, "bottom", 0.65)
            ov2 = create_gradient_overlay(bg, "top_bottom", 0.55)
            frame = Image.blend(ov1, ov2, ease_in_out(cross_t))
        elif t < 10.0:
            # シーン2: 上下にグラデーション暗幕
            frame = create_gradient_overlay(bg, "top_bottom", 0.55)
        elif t < 11.0:
            cross_t = (t - 10.0) / 1.0
            ov1 = create_gradient_overlay(bg, "top_bottom", 0.55)
            ov2 = create_gradient_overlay(bg, "full", 0.7)
            frame = Image.blend(ov1, ov2, ease_in_out(cross_t))
        else:
            frame = create_gradient_overlay(bg, "full", 0.72)

        frame = frame.convert("RGBA")

        # ── 桜花びら ──
        petal_alpha = 0.7
        if t > 18.0:
            petal_alpha = 0.7 * (1.0 - ease_in_out((t - 18.0) / 2.0))
        frame = draw_sakura_petals(frame, petals, t, petal_alpha)

        # ── テキストレイヤー（全て滑らかなアルファフェード） ──

        # --- シーン1テキスト (0-4秒) ---
        # 「― 卯月 ―」 0.5〜3.5秒
        a = fade_value(t, 0.5, 3.8, fade_dur=1.0)
        frame = draw_centered_text_alpha(frame, "― 卯月 ―", H - 580, font_sub, SUB_TEXT_COLOR, a)

        # メインキャッチ 1.0〜3.8秒
        a = fade_value(t, 1.0, 4.0, fade_dur=1.2)
        frame = draw_centered_text_alpha(frame, "移ろう季節を、", H - 500, font_hero, TEXT_COLOR, a)
        frame = draw_centered_text_alpha(frame, "一皿に込めて。", H - 430, font_hero, TEXT_COLOR, a)

        # 装飾線 1.5〜3.8秒
        a = fade_value(t, 1.5, 4.0, fade_dur=1.0)
        frame = draw_line_alpha(frame, H - 360, 100, GOLD_COLOR, a)

        # 「禅園 / 卯月の懐石コース」 2.0〜3.8秒
        a = fade_value(t, 2.0, 4.0, fade_dur=1.0)
        frame = draw_centered_text_alpha(frame, "禅 園", H - 330, font_sub, GOLD_COLOR, a)
        frame = draw_centered_text_alpha(frame, "卯月の懐石コース ・ 前菜", H - 285, font_small, SUB_TEXT_COLOR, a)

        # --- シーン2テキスト (5-10秒) ---
        # 上部キャッチ
        a = fade_value(t, 5.3, 10.0, fade_dur=1.2)
        frame = draw_centered_text_alpha(frame, "四月の旬菜", 120, font_title, GOLD_COLOR, a)
        frame = draw_line_alpha(frame, 185, 80, GOLD_COLOR, a)

        # 中段テキスト（順番に出る）
        a = fade_value(t, 6.0, 10.0, fade_dur=1.2)
        frame = draw_centered_text_alpha(frame, "桜が綻び、山菜が芽吹く四月。", H - 420, font_small, TEXT_COLOR, a)

        a = fade_value(t, 6.8, 10.0, fade_dur=1.2)
        frame = draw_centered_text_alpha(frame, "この一瞬の「旬」を逃さず", H - 370, font_small, TEXT_COLOR, a)

        a = fade_value(t, 7.5, 10.0, fade_dur=1.2)
        frame = draw_centered_text_alpha(frame, "お皿の上に表現いたします。", H - 320, font_small, TEXT_COLOR, a)

        # 下部装飾
        a = fade_value(t, 8.0, 10.0, fade_dur=1.0)
        frame = draw_line_alpha(frame, H - 250, 50, GOLD_COLOR, a)
        frame = draw_centered_text_alpha(frame, "目で愉しみ、舌で味わう", H - 220, font_tag, SUB_TEXT_COLOR, a)

        # --- エンディング (11-20秒) ---

        # キャッチコピー 11.2〜14.5秒
        a = fade_value(t, 11.2, 14.5, fade_dur=1.5)
        frame = draw_line_alpha(frame, 460, 70, GOLD_COLOR, a)
        frame = draw_centered_text_alpha(frame, "「いま」しか届けられない", 490, font_sub, TEXT_COLOR, a)
        frame = draw_centered_text_alpha(frame, "味わいを。", 535, font_sub, TEXT_COLOR, a)
        frame = draw_line_alpha(frame, 590, 70, GOLD_COLOR, a)

        # 店名 12.0〜19.5秒
        a = fade_value(t, 12.0, 19.5, fade_dur=1.5)
        frame = draw_centered_text_alpha(frame, "心斎橋  禅 園", 650, font_large, GOLD_COLOR, a)

        # 装飾線（店名の下）
        a = fade_value(t, 12.5, 19.5, fade_dur=1.5)
        frame = draw_line_alpha(frame, 740, 120, GOLD_COLOR, a)

        # 住所 13.0〜19.5秒
        a = fade_value(t, 13.0, 19.5, fade_dur=1.5)
        frame = draw_centered_text_alpha(frame, "〒542-0086", 780, font_info_small, SUB_TEXT_COLOR, a)
        frame = draw_centered_text_alpha(frame, "大阪府大阪市中央区西心斎橋1-3-3", 810, font_info, SUB_TEXT_COLOR, a)
        frame = draw_centered_text_alpha(frame, "オー・エム・ホテル日航ビルB2F", 845, font_info, SUB_TEXT_COLOR, a)

        # 電話番号 13.5〜19.5秒
        a = fade_value(t, 13.5, 19.5, fade_dur=1.5)
        frame = draw_line_alpha(frame, 895, 40, GOLD_COLOR, a * 0.5)
        frame = draw_centered_text_alpha(frame, "06-6241-7027", 915, font_sub, TEXT_COLOR, a)

        # 営業時間 14.0〜19.5秒
        a = fade_value(t, 14.0, 19.5, fade_dur=1.5)
        frame = draw_line_alpha(frame, 970, 40, GOLD_COLOR, a * 0.5)
        frame = draw_centered_text_alpha(frame, "営 業 時 間", 995, font_info_small, GOLD_COLOR, a)
        frame = draw_centered_text_alpha(frame, "ランチ  11:30〜14:45（L.O.14:00）", 1030, font_info, SUB_TEXT_COLOR, a)
        frame = draw_centered_text_alpha(frame, "ディナー  17:00〜22:00（L.O.21:00）", 1065, font_info, SUB_TEXT_COLOR, a)

        # 定休日 14.5〜19.5秒
        a = fade_value(t, 14.5, 19.5, fade_dur=1.5)
        frame = draw_centered_text_alpha(frame, "定休日 : 不定休（施設に準ずる）", 1110, font_info_small, SUB_TEXT_COLOR, a)

        # ハッシュタグ 15.5〜19.0秒
        a = fade_value(t, 15.5, 19.0, fade_dur=1.2)
        frame = draw_centered_text_alpha(frame, "#禅園  #心斎橋  #旬を届ける  #懐石料理", 1200, font_tag, SUB_TEXT_COLOR, a)

        # ── フレーム保存 ──
        frame_rgb = frame.convert("RGB")
        frame_rgb.save(os.path.join(FRAME_DIR, f"frame_{fi:05d}.png"), "PNG")

        if fi % 60 == 0:
            print(f"  {fi}/{TOTAL_FRAMES} ({t:.1f}s)")

    print(f"全{TOTAL_FRAMES}フレーム生成完了")


def encode_video():
    print("MP4エンコード中...")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(FRAME_DIR, "frame_%05d.png"),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
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
    shutil.rmtree(FRAME_DIR, ignore_errors=True)
    print("完了!")
