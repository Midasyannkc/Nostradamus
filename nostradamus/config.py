import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTITIONS = 4
HORIZON_DAYS = 180           # a borrower is "at risk" when a notice of sale is posted within this many days (90 was tried first, see docs)
START = "2025-01"            # first simulated month
MONTHS = 22                  # 12 history months for training, 10 live months streamed (ends October 2026)
TRAIN_MONTHS = 12
ALLOWED_LATENESS_DAYS = 45
COOLDOWN_DAYS = 60            # no repeat alert for a borrower inside this window unless days past due rises 30 or more
MAX_FORWARD_JUMP_DAYS = 62     # a jump of two months or more ahead of the watermark is not a plausible gap in a live feed: quarantine
