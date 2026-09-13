#!/usr/bin/env python3
"""Génère des images et une vidéo provisoires pour tester le prototype.

Les noms suivent la convention Ren'Py : « lena sourire.png » définit l'image
« lena sourire ». Les fichiers existants sont écrasés.

Usage : python3 tools/generer_placeholders.py
"""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "game" / "images"
VIDEOS = ROOT / "game" / "videos"
SCREEN = (1920, 1080)


def font(size):
    return ImageFont.load_default(size=size)


def background(name, top, bottom, rectangles):
    image = Image.new("RGB", SCREEN)
    draw = ImageDraw.Draw(image)
    for y in range(SCREEN[1]):
        t = y / (SCREEN[1] - 1)
        color = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
        draw.line([(0, y), (SCREEN[0], y)], fill=color)
    for box, color in rectangles:
        draw.rectangle(box, fill=color)
    draw.text((60, 50), name, font=font(48), fill=(255, 255, 255))
    image.save(IMAGES / f"{name}.png")


def character(name, color):
    image = Image.new("RGBA", (620, 940), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse([200, 40, 420, 290], fill=color)
    draw.rounded_rectangle([90, 310, 530, 1200], radius=190, fill=color)
    draw.text((310, 620), name, font=font(44), fill=(255, 255, 255), anchor="mm")
    image.save(IMAGES / f"{name}.png")


def video(name, seconds=4):
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"testsrc2=size=1280x720:rate=30:duration={seconds}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
            "-c:v", "libvpx-vp9", "-b:v", "1M", "-c:a", "libopus", "-shortest",
            str(VIDEOS / f"{name}.webm"),
        ],
        check=True,
    )


def main():
    IMAGES.mkdir(parents=True, exist_ok=True)
    VIDEOS.mkdir(parents=True, exist_ok=True)

    street_windows = [((x, 380 + (x * 7) % 300, x + 70, 480 + (x * 7) % 300), (230, 190, 90)) for x in range(120, 1800, 210)]
    background("rue_nuit", (8, 12, 30), (40, 45, 75), street_windows)
    background("appartement_soir", (70, 45, 40), (150, 100, 70),
               [((1150, 160, 1700, 620), (40, 55, 95)), ((0, 820, 1920, 1080), (60, 38, 30))])

    character("lena sourire", (190, 150, 250, 255))
    character("lena rougit", (235, 140, 185, 255))
    character("lena serieuse", (125, 110, 190, 255))

    video("lena_scene_01")
    print(f"Images : {IMAGES}\nVidéos : {VIDEOS}\nPensez à lancer tools/convertir_videos.py pour Godot.")


if __name__ == "__main__":
    main()
