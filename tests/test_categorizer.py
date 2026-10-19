import pytest

from services.categorizer import categorize_transaction


@pytest.mark.parametrize("label,amount,expected", [
    ("CB CAFE DE FLORE", 8.0, ("Sorties & Loisirs", "Restaurants & Sorties")),
    ("CB PAIEMENT LYDIA", 15.0, ("Autre", "Dépenses courantes")),
    ("CB PRIMEUR DU MARCHE", 12.0, ("Alimentation", "Courses & Supermarché")),
    ("CB BUREAU VALLEE", 9.0, ("Autre", "Dépenses courantes")),
    ("CB SALLE ENTRAINEMENT", 30.0, ("Autre", "Dépenses courantes")),
    ("CB BARBER SHOP", 20.0, ("Autre", "Dépenses courantes")),
    ("CB UBER EATS PARIS", 24.5, ("Sorties & Loisirs", "Livraison de repas")),
    ("CB UBER TRIP", 14.0, ("Transports", "Mobilité & Transports")),
    ("PRLV SEPA EDF CLIENT 04928174", 84.2, ("Logement & Charges", "Électricité & Gaz")),
    ("VIR SEPA SALAIRE THALES SA APPRENTISSAGE", -1350.0, ("Revenus & Aides", "Rémunération / Salaire")),
    ("VIR CAF APL", -180.0, ("Revenus & Aides", "Aides Publiques (CAF / APL)")),
])
def test_categorizer(label, amount, expected):
    assert categorize_transaction(label, amount) == expected


def test_debit_is_never_income():
    assert categorize_transaction("CB SALAIRE DU CAFE", 10.0)[0] != "Revenus & Aides"


def test_csv_categories_take_priority(backend):
    spotify = next(t for t in backend.transactions if "SPOTIFY" in t.merchant)
    assert (spotify.category, spotify.subcategory) == ("Abonnements & Services", "Streaming & Musique")
