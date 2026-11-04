"""INC-6: features for month M may use only what was known by the end of month M."""
from nostradamus.state import State, features
from tests.helpers import B, pay

STATIC = {"ltv": .8, "dti": .35}


def _state(*events):
    s = State()
    for e in events:
        s.apply(e)
    return s


def test_later_months_do_not_change_the_features_of_an_earlier_month():
    early = [pay("E1", "2025-02-10T10:00:00+00:00", dpd=0), pay("E2", "2025-03-10T10:00:00+00:00", dpd=30)]
    later = [pay("E3", "2025-04-10T10:00:00+00:00", dpd=60), pay("E4", "2025-05-10T10:00:00+00:00", dpd=90)]
    as_of_march = features(_state(*early).b[B], 2, STATIC)
    with_future = features(_state(*early, *later).b[B], 2, STATIC)
    assert with_future == as_of_march
