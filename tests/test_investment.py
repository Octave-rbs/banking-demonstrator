import pytest

from services.investment_service import simulate_investment


def test_zero_yield_keeps_capital():
    sim = simulate_investment(200.0, 50.0, 5, 0.0, is_pea=True)
    assert sim["invested"] == pytest.approx(3200.0)
    assert sim["final_capital"] == pytest.approx(3200.0)
    assert sim["net_gain"] == 0.0


def test_pea_is_taxed_less_than_cto():
    pea = simulate_investment(200.0, 50.0, 5, 0.07, is_pea=True)
    cto = simulate_investment(200.0, 50.0, 5, 0.07, is_pea=False)
    assert pea["capital_gain"] == pytest.approx(cto["capital_gain"])
    assert pea["net_gain"] == pytest.approx(pea["capital_gain"] * (1 - 0.172))
    assert cto["net_gain"] == pytest.approx(cto["capital_gain"] * (1 - 0.30))
