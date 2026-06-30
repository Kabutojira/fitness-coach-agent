#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from fitness_state.context import PURPOSES, get_context


def main() -> None:
    parser = argparse.ArgumentParser(description="Render fitness coach context from CSV state")
    parser.add_argument("--purpose", choices=sorted(PURPOSES), default="general")
    parser.add_argument("--state-dir", default=str(Path(__file__).resolve().parents[1] / "state"))
    args = parser.parse_args()
    print(get_context(purpose=args.purpose, state_dir=args.state_dir), end="")


if __name__ == "__main__":
    main()
