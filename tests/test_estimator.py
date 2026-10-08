import pytest

from sba_survival.estimator import cumulative_incidence


def test_competing_event_reduces_later_chargeoff_risk():
    result = cumulative_incidence([1, 1, 2, 3], [1, 2, 0, 1], (1.0, 3.0))
    assert result[1.0]["chargeoff_cif"] == pytest.approx(0.25)
    assert result[1.0]["paid_in_full_cif"] == pytest.approx(0.25)
    assert result[3.0]["chargeoff_cif"] == pytest.approx(0.75)


def test_invalid_event_code_is_rejected():
    with pytest.raises(ValueError):
        cumulative_incidence([1], [3], (1.0,))
