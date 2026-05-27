from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.blender.pipeline import generate_house
from backend.toon.parser import parse_toon
from backend.toon.planner import prompt_to_toon


def main() -> None:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default="Modern 3 bedroom villa with flat roof")
    parser.add_argument("--toon")
    parser.add_argument("--output", default="exports/house.glb")
    args = parser.parse_args(argv)

    toon = Path(args.toon).read_text() if args.toon else prompt_to_toon(args.prompt)
    scene = parse_toon(toon)
    output = generate_house(scene, args.output)
    print(output)


if __name__ == "__main__":
    main()
