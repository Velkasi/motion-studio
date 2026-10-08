#!/usr/bin/env python3
"""Every word cue of STORYBOARD.md lands on its word of minutage.json: never after, at most 2 frames before.

Reads the sequence headers `## Frame <n> : <title> · <in> → <out>` and their `Word cues: mot@<local s> ...` lines
(local times, from the start of the sequence). A cue may contain a space (`salle ?@3.15`, `19 %@3.71`).
Cues are matched in order to the words of minutage.json (same letters, looking a few words ahead).
Usage: python3 check-cues.py <film_dir>   (reads <film_dir>/STORYBOARD.md and <film_dir>/minutage.json)
Exit 0: every cue on time. Exit 1: late, early or unknown cues (listed).
"""
import json
import os
import re
import sys
import unicodedata

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

HEAD = re.compile(r"^##\s+Frame\s+(\d+)\s*:.*·\s*([0-9]+(?:\.[0-9]+)?)\s*→\s*([0-9]+(?:\.[0-9]+)?)")
CUE = re.compile(r"([^@\s](?:[^@]*?[^@\s])??)@(\d+(?:\.\d+)?)(?=\s|$)")   # shortest word first: « à@2.80 »
LOOKAHEAD = 4        # always look this many words ahead; further only while the word is inside the sequence
EPS = 0.005


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if c.isalnum() and not unicodedata.combining(c))


def parse_storyboard(text):
    """[(frame number, frame start, [(word, local time), ...], frame end), ...]"""
    frames = []
    for line in text.splitlines():
        m = HEAD.match(line)
        if m:
            frames.append((int(m.group(1)), float(m.group(2)), [], float(m.group(3))))
            continue
        if line.startswith("Word cues:") and frames:
            frames[-1][2].extend((w, float(t)) for w, t in CUE.findall(line[len("Word cues:"):]))
    return frames


def check(storyboard_text, minutage, fps=None):
    fps = fps or minutage.get("fps", 30)
    words = minutage["words"]
    early = 2 / fps
    errors, ptr = [], 0
    for frame, start, cues, end in parse_storyboard(storyboard_text):
        for word, local in cues:
            key = norm(word)
            if not key:
                continue
            found, k = None, ptr
            while k < len(words) and (k - ptr <= LOOKAHEAD or words[k]["start"] <= end + 0.5):
                if norm(words[k]["w"]) == key:
                    found = k
                    break
                k += 1
            if found is None:
                errors.append(f"frame {frame}: cue « {word} »@{local:.2f} has no matching word in minutage.json "
                              f"(next word: « {words[ptr]['w'] if ptr < len(words) else '-'} »)")
                continue
            ptr = found + 1
            at, w_start = start + local, words[found]["start"]
            if at > w_start + EPS:
                errors.append(f"frame {frame}: « {word} » en retard de {at - w_start:.3f} s "
                              f"(repère {at:.2f}, mot {w_start:.2f}) : mettre @{w_start - start:.2f}")
            elif at < w_start - early - EPS:
                errors.append(f"frame {frame}: « {word} » trop tôt de {w_start - at:.3f} s "
                              f"(repère {at:.2f}, mot {w_start:.2f}) : mettre @{w_start - start:.2f}")
    return errors


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: check-cues.py <film_dir>")
    d = sys.argv[1]
    with open(os.path.join(d, "STORYBOARD.md"), encoding="utf-8") as f:
        text = f.read()
    with open(os.path.join(d, "minutage.json"), encoding="utf-8") as f:
        minutage = json.load(f)
    errors = check(text, minutage)
    n = sum(len(f[2]) for f in parse_storyboard(text))
    for e in errors:
        print(e)
    print(f"{n} cues, {len(errors)} error(s)")
    sys.exit(1 if errors or n == 0 else 0)


if __name__ == "__main__":
    main()
