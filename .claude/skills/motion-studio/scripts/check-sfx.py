#!/usr/bin/env python3
"""Sound effects of one film: no sound more than twice, every file found, every event inside the film.

Reads <film_dir>/assets/audio/sfx-events.json ([["name", seconds, volume], ...], the format of build-audio.sh).
A name resolves to <film_dir>/assets/audio/sfx/<name>.(mp3|wav) first (sounds generated for this film), then to the
library .claude/skills/media-use/audio/assets/sfx/. The duration comes from <film_dir>/minutage.json (or --duration).
Usage: python3 check-sfx.py <film_dir> [--max 2] [--duration S]
Exit 0: ok. Exit 1: errors (listed).
"""
import argparse
import collections
import json
import os
import sys

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
LIBRARY = os.path.join(ROOT, ".claude", "skills", "media-use", "audio", "assets", "sfx")
EXTS = (".mp3", ".wav")


def find(name, dirs):
    for d in dirs:
        for ext in EXTS:
            p = os.path.join(d, name + ext)
            if os.path.isfile(p):
                return p
    return None


def well_formed(e):
    return (isinstance(e, (list, tuple)) and len(e) == 3 and isinstance(e[0], str)
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in e[1:]))


def check(events, duration, dirs, maximum=2):
    errors = [f"format : {e!r} n'est pas [\"nom\", secondes, gain]" for e in events if not well_formed(e)]
    events = [e for e in events if well_formed(e)]
    counts = collections.Counter(e[0] for e in events)
    for name, n in sorted(counts.items()):
        if n > maximum:
            times = ", ".join(f"{e[1]:.2f}" for e in events if e[0] == name)
            errors.append(f"« {name} » utilisé {n} fois (max {maximum}) : {times}")
        if find(name, dirs) is None:
            errors.append(f"« {name} » introuvable (ni assets/audio/sfx/ du film, ni la bibliothèque)")
    for e in events:
        if not 0 <= float(e[1]) < duration:
            errors.append(f"« {e[0] } » à {float(e[1]):g} s, hors du film (0 à {duration:g} s)")
    return errors


def main():
    ap = argparse.ArgumentParser(description="Sound effects check of one film.")
    ap.add_argument("film_dir")
    ap.add_argument("--max", type=int, default=2)
    ap.add_argument("--duration", type=float)
    a = ap.parse_args()
    with open(os.path.join(a.film_dir, "assets", "audio", "sfx-events.json"), encoding="utf-8") as f:
        events = json.load(f)
    duration = a.duration
    if duration is None:
        with open(os.path.join(a.film_dir, "minutage.json"), encoding="utf-8") as f:
            duration = json.load(f)["duration"]
    errors = check(events, duration, [os.path.join(a.film_dir, "assets", "audio", "sfx"), LIBRARY], a.max)
    for e in errors:
        print(e)
    print(f"{len(events)} events, {len(set(e[0] for e in events))} distinct sounds, {len(errors)} error(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
