import io

import pytest

from services.shared_expenses import split_equally, is_split_balanced


def test_split_equally_gives_remaining_cent_to_payer():
    shares = split_equally(10.0, ["u1", "u2", "u3"], payer_id="u2")
    assert shares == {"u1": 3.33, "u2": 3.34, "u3": 3.33}
    assert sum(shares.values()) == pytest.approx(10.0)


def test_split_equally_falls_back_to_first_participant():
    shares = split_equally(10.0, ["u1", "u2", "u3"], payer_id="u9")
    assert shares["u1"] == 3.34


@pytest.mark.parametrize("split,expected", [
    ({"u1": 5.0, "u2": 5.0}, True),
    ({"u1": 5.0, "u2": 4.0}, False),
    ({"u1": 3.34, "u2": 3.33, "u3": 3.33}, True),
])
def test_is_split_balanced(split, expected):
    assert is_split_balanced(10.0, split) is expected


def test_balances_sum_to_zero_after_equal_split(empty_backend):
    empty_backend.add_direct_expense("Tapas", 10.0, "u1", {}, group_id="voyage_barcelone")
    balances = empty_backend.calculate_balances("voyage_barcelone")
    assert sum(balances.values()) == pytest.approx(0.0)


def test_adding_member_does_not_change_past_balances(empty_backend):
    empty_backend.add_direct_expense("Tapas", 40.0, "u1", {}, group_id="voyage_barcelone")
    before = empty_backend.calculate_balances("voyage_barcelone")
    empty_backend.add_member_to_group("u3", "voyage_barcelone")
    after = empty_backend.calculate_balances("voyage_barcelone")
    assert after.pop("u3") == 0.0
    assert after == before


def test_csv_import_freezes_split(empty_backend):
    csv = "merchant,amount,method,date,shared_account_id\nAIRBNB,90,carte,2026-09-01,voyage_barcelone\n"
    empty_backend.process_transaction_file(io.StringIO(csv), "u1", "csv")
    assert empty_backend.transactions[-1].split_details == {"u1": 30.0, "u2": 30.0, "u5": 30.0}


def test_optimize_transfers_settles_everything(empty_backend):
    empty_backend.add_direct_expense("Airbnb", 90.0, "u1", {}, group_id="voyage_barcelone")
    empty_backend.add_direct_expense("Tapas", 30.0, "u2", {}, group_id="voyage_barcelone")
    balances = empty_backend.calculate_balances("voyage_barcelone")
    for _, _, amount, debtor, creditor in empty_backend.optimize_transfers(balances):
        balances[debtor] += amount
        balances[creditor] -= amount
    assert all(abs(b) < 0.01 for b in balances.values())
