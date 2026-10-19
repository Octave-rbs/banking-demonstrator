import os
import sys
from datetime import date

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from services import BankBackend  # noqa: E402
from services.repository import demo_date_offset  # noqa: E402


@pytest.fixture
def backend(monkeypatch):
    """Backend chargé avec les deux CSV de démo, recalés pour finir le 18/10/2026."""
    # L'appli lit ses fichiers en chemins relatifs à la racine du projet
    monkeypatch.chdir(ROOT)
    db = BankBackend()
    offset = demo_date_offset(date(2026, 10, 18))
    for filename, uid in [("operations_60j_paul.csv", "u1"), ("operations_60j_emma.csv", "u2")]:
        with open(os.path.join("data", filename), "rb") as f:
            db.process_transaction_file(f, uid, "csv", date_offset=offset)
    return db


@pytest.fixture
def empty_backend(monkeypatch):
    monkeypatch.chdir(ROOT)
    return BankBackend()
