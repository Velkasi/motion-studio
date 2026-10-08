#!/usr/bin/env python3
"""Side-by-side sheet of the three films: one row per film, the same 6 instants in every row.

Usage: python3 comparatif.py <film1.mp4> <film2.mp4> <film3.mp4> --out <projet>/comparatif.jpg [--height 360]
Instants: 10, 25, 40, 55, 70 and 90 % of the shortest film. Every cell is fitted (letterboxed) in the frame of the
first film scaled to --height, so films of different shapes still line up.
"""
import argparse
import subprocess
import sys

FRACTIONS = (0.10, 0.25, 0.40, 0.55, 0.70, 0.90)


def probe(path, entries):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", entries, "-of",
                          "default=nw=1:nk=1", path], capture_output=True, text=True, check=True).stdout.split()
    return out


def main():
    ap = argparse.ArgumentParser(description="Side-by-side sheet of the three films.")
    ap.add_argument("films", nargs=3)
    ap.add_argument("--out", required=True)
    ap.add_argument("--height", type=int, default=360)
    a = ap.parse_args()

    durations = []
    for f in a.films:
        d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1",
                            f], capture_output=True, text=True, check=True).stdout.strip()
        durations.append(float(d))
    w0, h0 = (int(x) for x in probe(a.films[0], "stream=width,height"))
    h = a.height - a.height % 2
    w = int(round(w0 * h / h0 / 2)) * 2
    shortest = min(durations)

    args, chains, k = [], [], 0
    for film in a.films:
        for frac in FRACTIONS:
            args += ["-ss", f"{shortest * frac:.3f}", "-i", film]
            chains.append(f"[{k}:v]trim=end_frame=1,scale={w}:{h}:force_original_aspect_ratio=decrease,"
                          f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1[c{k}]")
            k += 1
    rows = []
    for r in range(3):
        cells = "".join(f"[c{r * 6 + i}]" for i in range(6))
        chains.append(f"{cells}hstack=inputs=6[r{r}]")
        rows.append(f"[r{r}]")
    chains.append("".join(rows) + "vstack=inputs=3[out]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", ";".join(chains), "-map", "[out]",
                    "-frames:v", "1", "-q:v", "3", a.out], check=True)
    print(f"written: {a.out} ({6 * w}x{3 * h}, instants at "
          + ", ".join(f"{shortest * f:.2f}" for f in FRACTIONS) + " s)")


if __name__ == "__main__":
    sys.exit(main())
