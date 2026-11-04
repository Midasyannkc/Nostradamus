import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTITIONS = 4
HORIZON_DAYS = 90            # a borrower is "at risk" when a notice of sale is posted within this many days
START = "2025-01"            # first simulated month
MONTHS = 20                  # 12 history months for training, 8 live months streamed
TRAIN_MONTHS = 12
ALLOWED_LATENESS_DAYS = 45
COOLDOWN_DAYS = 60            # no repeat alert for a borrower inside this window unless days past due rises 30 or more
