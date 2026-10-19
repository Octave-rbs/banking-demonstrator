from datetime import datetime

import pytest


def test_demo_csv_ends_on_reference_day(backend):
    budget = backend.analyze_monthly_budget("u1")
    assert budget["rolling_label"] == "Mois glissant (du 18/09 au 18/10/2026)"
    assert budget["rolling_spent"] == pytest.approx(1468.55)


def test_rolling_window_stable_after_new_expense(backend):
    before = backend.analyze_monthly_budget("u1")["rolling_spent"]
    backend.add_direct_expense("Courses coloc", 10.0, "u1", {}, date=datetime(2026, 10, 18, 21, 30),
                               group_id="coloc_paris_01")
    after = backend.analyze_monthly_budget("u1")["rolling_spent"]
    assert after == pytest.approx(before + 10.0)


def test_subcategories_sum_to_category(backend):
    categories, _, subcategories = backend.get_category_breakdown("u1")
    assert categories
    for cat, total in categories.items():
        assert sum(subcategories[cat].values()) == pytest.approx(total)
