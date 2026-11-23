#!/usr/bin/env python3
"""Make the shopper project folder for a new user: data/ with its README.md.

    python3 setup_project.py --project <folder>

The README is a copy of data-readme.md in the profile skill's folder; it also
marks the folder as the shopper project folder. Nothing that already exists is
changed. Prints the data folder and whether the README was created.
"""

import argparse
import json
import pathlib
import shutil

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent


def main(argv=None):
    parser = argparse.ArgumentParser(description="Make the shopper project folder for a new user.")
    parser.add_argument("--project", required=True)
    args = parser.parse_args(argv)
    data = pathlib.Path(args.project).expanduser().resolve() / "data"
    data.mkdir(parents=True, exist_ok=True)
    readme = data / "README.md"
    created = not readme.exists()
    if created:
        shutil.copyfile(SKILL_DIR / "data-readme.md", readme)
    print(json.dumps({"data": str(data), "created": created}, ensure_ascii=False))


if __name__ == "__main__":
    main()
