#!/usr/bin/env python3
"""Convertit les vidéos WebM de game/videos en Ogg Theora (.ogv) pour Godot.

Ren'Py lit les .webm ; Godot ne lit nativement que l'Ogg Theora. Les deux
fichiers coexistent : le script .rpy référence toujours le .webm et le lecteur
Godot cherche le .ogv de même nom. Les .ogv à jour ne sont pas régénérés.

Usage : python3 tools/convertir_videos.py [--force]
Requiert ffmpeg2theora (brew install ffmpeg2theora).
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIDEOS = ROOT / "game" / "videos"


def convert(source, force):
    target = source.with_suffix(".ogv")
    if not force and target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
        print(f"à jour      {target.name}")
        return
    subprocess.run(
        ["ffmpeg2theora", "--videoquality", "7", "--audioquality", "3", "-o", str(target), str(source)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"converti    {target.name}")


def main():
    if shutil.which("ffmpeg2theora") is None:
        sys.exit("ffmpeg2theora introuvable : brew install ffmpeg2theora")
    force = "--force" in sys.argv
    sources = sorted(VIDEOS.rglob("*.webm"))
    if not sources:
        print(f"Aucune vidéo .webm dans {VIDEOS}")
    for source in sources:
        convert(source, force)


if __name__ == "__main__":
    main()
