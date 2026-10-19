"""
Moteur de catégorisation des opérations bancaires par règles.

Les CSV de démonstration portent déjà leurs colonnes category/subcategory :
ces règles ne servent que de secours pour les fichiers importés qui n'en ont pas.
"""

import re
from typing import List, Tuple

# Convention de signe : amount < 0 = crédit (revenu), amount > 0 = débit (dépense).
# Règles ordonnées : (catégorie, sous-catégorie, mots-clés). Les mots-clés sont comparés
# en mots entiers, pour éviter que « café » ne devienne « caf » ou « primeur » « prime ».
INCOME_RULES: List[Tuple[str, str, List[str]]] = [
    ("Revenus & Aides", "Aides Publiques (CAF / APL)", ["caf", "apl"]),
    ("Revenus & Aides", "Rémunération / Salaire", ["salaire", "paie", "alternance"]),
    ("Revenus & Aides", "Bourses d'études", ["bourse"]),
    ("Revenus & Aides", "Remboursements & Notes de frais", ["remboursement", "remb"]),
]

EXPENSE_RULES: List[Tuple[str, str, List[str]]] = [
    ("Logement & Charges", "Loyer", ["loyer", "immobilier"]),
    ("Logement & Charges", "Électricité & Gaz", ["edf", "engie", "electricite", "électricité"]),
    ("Logement & Charges", "Charges & Assurance", ["veolia", "eau de paris", "assurance habitation"]),
    ("Abonnements & Services", "Box Internet & Télécoms", ["internet", "freebox", "free telecom", "orange", "bouygues", "sfr"]),
    ("Abonnements & Services", "Streaming & Musique", ["spotify", "netflix", "deezer", "amazon prime", "prime video", "disney", "chatgpt", "icloud"]),
    ("Alimentation", "Boulangerie & Pause Déjeuner", ["boulangerie", "paul", "brioche doree", "landemaine"]),
    ("Alimentation", "Courses & Supermarché", ["carrefour", "monoprix", "franprix", "lidl", "auchan", "leclerc", "biocoop", "naturalia", "intermarche", "intermarché", "primeur"]),
    ("Sorties & Loisirs", "Livraison de repas", ["deliveroo", "uber eats"]),
    ("Sorties & Loisirs", "Restaurants & Sorties", ["restaurant", "bar", "pub", "bistrot", "brasserie", "cafe", "café"]),
    ("Sorties & Loisirs", "Culture & Électronique", ["cinéma", "cinema", "ugc", "pathe", "pathé", "fnac"]),
    ("Sorties & Loisirs", "Shopping & Mode", ["zara", "apm monaco", "decathlon", "sephora"]),
    ("Transports", "Mobilité & Transports", ["ratp", "navigo", "sncf", "uber", "bolt", "velib", "lime", "dott"]),
    ("Autre", "Santé & Pharmacie", ["pharmacie", "doctolib", "medecin", "médecin", "dentiste"]),
]


def _matches(keywords: List[str], text: str) -> bool:
    return any(re.search(rf"\b{re.escape(kw)}\b", text) for kw in keywords)


def categorize_transaction(merchant: str, amount: float) -> Tuple[str, str]:
    """
    Détermine la catégorie et sous-catégorie d'une opération à partir du libellé et du montant.
    Le sens du montant passe en premier : un débit n'est jamais classé en revenu.
    Retourne (catégorie, sous_catégorie).
    """
    m_lower = merchant.lower()

    if amount < 0:
        for cat, subcat, keywords in INCOME_RULES:
            if _matches(keywords, m_lower):
                return cat, subcat
        return "Revenus & Aides", "Virements reçus"

    for cat, subcat, keywords in EXPENSE_RULES:
        if _matches(keywords, m_lower):
            return cat, subcat

    return "Autre", "Dépenses courantes"
