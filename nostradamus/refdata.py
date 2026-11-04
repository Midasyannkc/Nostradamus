"""Loaders for the real reference files under data/real."""
import json
import os

import pandas as pd

from .config import ROOT


def _p(name):
    return os.path.join(ROOT, "data", "real", name)


def zip_areas() -> pd.DataFrame:
    return pd.read_csv(_p("zip_areas.csv"), dtype={"zip": str})


def statute() -> dict:
    return json.load(open(_p("texas_foreclosure_rules.json")))


def dallas_notice_files() -> pd.DataFrame:
    return pd.read_csv(_p("dallas_county_notice_files.csv"))


def attom_texas() -> pd.DataFrame:
    return pd.read_csv(_p("attom_texas_2026.csv"))
