#!/usr/bin/env python3
"""
Offline evaluation helper for face matching decisions (no camera).

Use this to sanity-check threshold and margin on saved embeddings or synthetic scores.

Example:
  python scripts/evaluate_recognition.py --demo

For a real benchmark, export probe/gallery embeddings to NumPy and implement
your own load_* functions reading your labeled dataset.
"""

from __future__ import annotations

import argparse
from typing import List, Tuple


def decide(
    best: float,
    second: float,
    threshold: float,
    margin: float,
    num_students: int,
) -> Tuple[str, bool]:
    if best < threshold:
        return "low_confidence", False
    if num_students > 1 and (best - second) < margin:
        return "ambiguous", False
    return "accept", True


def run_demo(threshold: float, margin: float) -> None:
    print(f"Threshold={threshold}, margin={margin}\n")
    cases: List[Tuple[str, float, float, int]] = [
        ("clear winner", 0.72, 0.35, 5),
        ("below threshold", 0.42, 0.10, 3),
        ("ambiguous", 0.65, 0.62, 4),
        ("single student", 0.55, 0.0, 1),
    ]
    for name, b, s, n in cases:
        label, ok = decide(b, s, threshold, margin, n)
        print(f"  {name}: best={b:.2f} second={s:.2f} students={n} -> {label} accept={ok}")


def main() -> None:
    p = argparse.ArgumentParser(description="Evaluate threshold/margin decisions (offline demo).")
    p.add_argument("--demo", action="store_true", help="Run built-in numeric examples")
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--margin", type=float, default=0.08)
    args = p.parse_args()
    if args.demo:
        run_demo(args.threshold, args.margin)
    else:
        print("Use --demo to see example decisions, or import decide() from this script in your notebook.")


if __name__ == "__main__":
    main()
