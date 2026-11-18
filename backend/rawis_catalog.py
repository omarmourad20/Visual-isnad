"""Read the bundled narrator catalog and its documented corrections."""

import csv
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def read_rawis(path):
    """Use the bundled supplement only with the bundled primary catalog."""
    paths = [path]
    if path.resolve() == (DATA_DIR / "all_rawis.csv").resolve():
        paths.append(DATA_DIR / "rawis_supplement.csv")
    for source in paths:
        with source.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                yield source, row
