"""INC-9: the model must not score where a borrower lives. ZIP-level risk is a proxy that can encode redlining."""
from nostradamus.state import FEATURES, State, features
from tests.helpers import B, pay

BANNED = ("area", "zip", "city", "county", "focus", "neighborhood", "tract", "plano", "frisco")


def test_no_model_feature_is_geographic():
    assert not [f for f in FEATURES if any(word in f for word in BANNED)]


def test_scores_do_not_change_when_only_the_area_changes():
    s = State()
    s.apply(pay("E1", "2025-03-10T10:00:00+00:00", dpd=30))
    low = features(s.b[B], 2, {"ltv": .8, "dti": .35, "area_risk": 0.0, "zip": "75034"})
    high = features(s.b[B], 2, {"ltv": .8, "dti": .35, "area_risk": 0.9, "zip": "75216"})
    assert low == high
    assert len(low) == len(FEATURES)
