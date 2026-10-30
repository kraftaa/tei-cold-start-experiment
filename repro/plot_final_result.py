#!/usr/bin/env python3
"""Render the final AMD64 cold-start result as SVG and PNG."""

from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
SVG_OUTPUT = ASSETS / "tei-cold-start-amd64.svg"
PNG_OUTPUT = ASSETS / "tei-cold-start-amd64.png"

LABELS = [
    ("Patched TEI 1.8", "baseline"),
    ("Candidate", "default warmup"),
    ("Candidate", "64-token warmup"),
    ("Candidate", "zero warmup"),
]
VALUES = [7.993, 7.616, 2.410, 2.104]
COLORS = ["#737373", "#A3A3A3", "#2563EB", "#16A34A"]

WIDTH = 1200
HEIGHT = 675
PLOT_LEFT = 90
PLOT_RIGHT = 1160
PLOT_TOP = 135
PLOT_BOTTOM = 520
MAX_SECONDS = 9.0
BAR_X = [145, 405, 665, 925]
BAR_WIDTH = 170


def y_for(value: float) -> float:
    return PLOT_BOTTOM - value / MAX_SECONDS * (PLOT_BOTTOM - PLOT_TOP)


def text(x: float, y: float, value: str, **attrs: object) -> str:
    properties = {"x": x, "y": y, **attrs}
    rendered = " ".join(f'{name.replace("_", "-")}="{setting}"' for name, setting in properties.items())
    return f"<text {rendered}>{value}</text>"


def build_svg() -> str:
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="1200" height="675" fill="#FFFFFF"/>',
        '<g font-family="Arial, Helvetica, sans-serif">',
        text(70, 53, "TEI cold start: time to first correct embedding", fill="#171717", font_size=30, font_weight=700),
        text(70, 88, "20 fresh-process trials per configuration · native AMD64 · 80/80 trials passed the correctness suite", fill="#525252", font_size=17),
    ]

    for tick in (0, 2, 4, 6, 8):
        y = y_for(tick)
        elements.append(f'<line x1="{PLOT_LEFT}" y1="{y:.1f}" x2="{PLOT_RIGHT}" y2="{y:.1f}" stroke="#E5E5E5" stroke-width="1"/>')
        elements.append(text(74, y + 5, str(tick), fill="#525252", font_size=15, text_anchor="end"))

    elements.extend([
        f'<line x1="{PLOT_LEFT}" y1="{PLOT_BOTTOM}" x2="{PLOT_RIGHT}" y2="{PLOT_BOTTOM}" stroke="#A3A3A3" stroke-width="1.5"/>',
        text(27, 350, "Seconds", fill="#262626", font_size=16, transform="rotate(-90 27 350)", text_anchor="middle"),
    ])

    for x, value, color, labels in zip(BAR_X, VALUES, COLORS, LABELS):
        top = y_for(value)
        height = PLOT_BOTTOM - top
        center = x + BAR_WIDTH / 2
        elements.append(f'<rect x="{x}" y="{top:.1f}" width="{BAR_WIDTH}" height="{height:.1f}" fill="{color}"/>')
        elements.append(text(center, top - 12, f"{value:.3f}s", fill="#171717", font_size=18, font_weight=700, text_anchor="middle"))
        elements.append(text(center, 553, labels[0], fill="#262626", font_size=16, text_anchor="middle"))
        elements.append(text(center, 576, labels[1], fill="#262626", font_size=16, text_anchor="middle"))

    default_center = BAR_X[1] + BAR_WIDTH / 2
    zero_center = BAR_X[3] + BAR_WIDTH / 2
    bracket_y = 128
    elements.extend([
        f'<path d="M {default_center} {bracket_y + 10} V {bracket_y} H {zero_center} V {bracket_y + 10}" fill="none" stroke="#404040" stroke-width="1.5"/>',
        text((default_center + zero_center) / 2, bracket_y - 9, "−72.37%", fill="#171717", font_size=19, font_weight=700, text_anchor="middle"),
        text(70, 642, "Same candidate binary for default, 64-token, and zero-warmup arms. Cached model. GitHub-hosted AMD EPYC 7763 runner. Production-container validation remains.", fill="#737373", font_size=13),
        "</g>",
        "</svg>",
    ])
    return "\n".join(elements) + "\n"


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    SVG_OUTPUT.write_text(build_svg(), encoding="utf-8")
    converter = shutil.which("rsvg-convert")
    if converter is None:
        raise SystemExit("rsvg-convert is required to create the PNG")
    subprocess.run(
        [converter, "--width", str(WIDTH), "--height", str(HEIGHT), "--output", str(PNG_OUTPUT), str(SVG_OUTPUT)],
        check=True,
    )
    print(PNG_OUTPUT)


if __name__ == "__main__":
    main()
