#!/usr/bin/env python3
"""Distance check of the three styles chosen for one script: the three films must look like three different films.

Reads <projet>/STYLES.json:
  {"styles": [{"famille": "<id of patterns/STYLE-FAMILIES.md>", "concept": "<one sentence>",
               "axes": {"rendu": ..., "monde": ..., "palette": ..., "typo": ..., "camera": ..., "mouvement": ...}}, x3]}
Prints the distance matrix (number of axes on which two styles differ, out of 6).
Exit 0: every pair differs on at least --min axes (default 5). Exit 1: a pair is too close. Exit 2: invalid file.
Usage: python3 style-distance.py <projet>/STYLES.json [--min 5]
"""
import argparse
import itertools
import json
import sys

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

AXIS_ORDER = ["rendu", "monde", "palette", "typo", "camera", "mouvement"]
AXES = {
    "rendu": {"vectoriel-plat", "papier-physique", "photo-composite", "3d-simulee", "typographique", "trace-main",
              "lumiere"},
    "monde": {"clair-plat", "clair-profond", "sombre-plat", "sombre-profond"},
    "palette": {"mono-accent", "duo", "pastel", "sature-pop", "naturelle", "nuit-neon"},
    "typo": {"grotesque", "serif-editorial", "display-condensee", "manuscrite", "mono", "ronde"},
    "camera": {"travelling-continu", "coupes-franches", "plan-fixe-pop", "zooms-profondeur", "panoramique-plan"},
    "mouvement": {"ressort-net", "glisse-douce", "image-par-image", "impact-rapide", "organique"},
}


def validate(data):
    styles = data.get("styles") if isinstance(data, dict) else None
    if not isinstance(styles, list) or len(styles) != 3:
        raise ValueError("STYLES.json: exactly 3 styles expected under \"styles\"")
    names = []
    for k, st in enumerate(styles, 1):
        if not st.get("famille") or not st.get("concept"):
            raise ValueError(f"style {k}: \"famille\" and \"concept\" are required")
        axes = st.get("axes") or {}
        for axis in AXIS_ORDER:
            if axes.get(axis) not in AXES[axis]:
                raise ValueError(f"style {k} ({st['famille']}): {axis} = {axes.get(axis)!r}, expected one of "
                                 + ", ".join(sorted(AXES[axis])))
        names.append(st["famille"])
    if len(set(names)) != 3:
        raise ValueError("STYLES.json: the 3 styles must come from 3 different families")
    return styles


def distance(a, b):
    return sum(a["axes"][axis] != b["axes"][axis] for axis in AXIS_ORDER)


def check(data, minimum=5):
    """Errors for the pairs closer than `minimum` axes; raises ValueError on an invalid file."""
    styles = validate(data)
    errors = []
    for a, b in itertools.combinations(styles, 2):
        d = distance(a, b)
        if d < minimum:
            same = [axis for axis in AXIS_ORDER if a["axes"][axis] == b["axes"][axis]]
            errors.append(f"{a['famille']} / {b['famille']}: {d}/6 axes apart (< {minimum}), same "
                          + ", ".join(same))
    return errors


def main():
    ap = argparse.ArgumentParser(description="Distance check of the three styles of STYLES.json.")
    ap.add_argument("styles")
    ap.add_argument("--min", type=int, default=5)
    a = ap.parse_args()
    try:
        with open(a.styles, encoding="utf-8") as f:
            data = json.load(f)
        errors = check(data, a.min)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"style-distance: {e}", file=sys.stderr)
        sys.exit(2)
    styles = data["styles"]
    width = max(len(s["famille"]) for s in styles)
    print(" " * width + "  " + "  ".join(f"{k + 1:>2}" for k in range(3)))
    for k, a_style in enumerate(styles):
        print(f"{a_style['famille']:<{width}}  " + "  ".join(f"{distance(a_style, b):>2}" for b in styles))
    for e in errors:
        print("TOO CLOSE: " + e)
    print("ok: 3 distinct films" if not errors else "fail: change the family closest to the others")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
