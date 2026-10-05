"""
Moteur de catégorisation intelligente des opérations bancaires.
"""

from typing import Tuple


def categorize_transaction(merchant: str, amount: float) -> Tuple[str, str]:
    """
    Détermine automatiquement la catégorie et sous-catégorie d'une dépense
    à partir du libellé marchand et du montant.
    Retourne (catégorie, sous_catégorie).
    """
    m_lower = merchant.lower()

    # 1. Revenus et Aides
    if amount < 0 or any(kw in m_lower for kw in [
        "salaire", "bourse", "apl", "caf", "virement parents", "remboursement", "remb", "thales", "paie"
    ]):
        if "apl" in m_lower or "caf" in m_lower:
            return "Revenus & Aides", "Aides Publiques (CAF / APL)"
        elif any(k in m_lower for k in ["salaire", "alternance", "thales", "paie"]):
            return "Revenus & Aides", "Rémunération / Salaire"
        elif "bourse" in m_lower:
            return "Revenus & Aides", "Bourses d'études"
        elif any(k in m_lower for k in ["remboursement", "remb", "xprojets"]):
            return "Revenus & Aides", "Remboursements & Notes de frais"
        else:
            return "Revenus & Aides", "Virements reçus"

    # 2. Logement & Charges
    if any(kw in m_lower for kw in [
        "loyer", "edf", "engie", "electricite", "électricité", "eau", "assurance hab", "immobilier"
    ]):
        if "loyer" in m_lower or "immobilier" in m_lower:
            return "Logement & Charges", "Loyer"
        elif any(k in m_lower for k in ["edf", "engie", "electricite"]):
            return "Logement & Charges", "Électricité & Gaz"
        else:
            return "Logement & Charges", "Charges & Assurance"

    # 3. Abonnements & Services Numériques
    if any(kw in m_lower for kw in [
        "spotify", "netflix", "internet", "freebox", "free telecom", "orange", "bouygues", "sfr",
        "apple", "prime", "chatgpt", "icloud"
    ]):
        if "internet" in m_lower or any(f in m_lower for f in ["freebox", "free telecom", "orange", "sfr", "bouygues"]):
            return "Abonnements & Services", "Box Internet & Télécoms"
        else:
            return "Abonnements & Services", "Streaming & Musique"

    # 4. Alimentation & Supermarché
    if any(kw in m_lower for kw in [
        "carrefour", "monoprix", "franprix", "lidl", "auchan", "leclerc", "boulangerie", "paul",
        "brioche", "biocoop", "landemaine", "naturalia", "intermarche", "intermarché"
    ]):
        if any(b in m_lower for b in ["boulangerie", "paul", "brioche", "landemaine"]):
            return "Alimentation", "Boulangerie & Pause Déjeuner"
        else:
            return "Alimentation", "Courses & Supermarché"

    # 5. Sorties, Loisirs & Restauration
    if any(kw in m_lower for kw in [
        "deliveroo", "uber eats", "restaurant", "triskell", "bar", "nelson", "cinéma", "cinema",
        "ugc", "pathe", "pathé", "fnac", "zara", "apm monaco", "fast food", "mcdo", "burger king",
        "bistrot", "brasserie", "decathlon", "sephora"
    ]):
        if "deliveroo" in m_lower or "uber eats" in m_lower:
            return "Sorties & Loisirs", "Livraison de repas"
        elif any(r in m_lower for r in ["restaurant", "triskell", "bar", "nelson", "bistrot", "brasserie"]):
            return "Sorties & Loisirs", "Restaurants & Sorties"
        elif any(c in m_lower for c in ["cinéma", "cinema", "ugc", "pathe", "pathé", "fnac"]):
            return "Sorties & Loisirs", "Culture & Électronique"
        elif any(s in m_lower for s in ["zara", "apm", "decathlon", "sephora"]):
            return "Sorties & Loisirs", "Shopping & Mode"
        else:
            return "Sorties & Loisirs", "Loisirs divers"

    # 6. Transports
    if any(kw in m_lower for kw in [
        "ratp", "navigo", "sncf", "train", "uber", "bolt", "velib", "lime", "dott"
    ]):
        return "Transports", "Mobilité & Transports"

    # 7. Santé & Pharmacie
    if any(kw in m_lower for kw in ["pharmacie", "doctolib", "medecin", "dentiste"]):
        return "Autre", "Santé & Pharmacie"

    return "Autre", "Dépenses courantes"
