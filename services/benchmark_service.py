"""
Gestion des données de benchmark statistique des pairs et ventilation des dépenses.
"""

import os
import json
from datetime import timedelta
from typing import Dict, List, Optional, Tuple
from models import Transaction


def load_peers_benchmark(filepath: Optional[str] = None) -> Dict[str, Dict]:
    """Charge les benchmarks statistiques des pairs depuis le fichier JSON externe."""
    json_path = filepath or os.path.join("data", "benchmark_peers.json")

    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data:
                    return data
        except Exception as e:
            print(f"[BenchmarkService] Erreur de lecture JSON {json_path}: {e}")

    # Données de secours par défaut
    return {
        "Logement & Charges": {
            "top_10_economes": 450.0, "top_30_economes": 580.0, "moyenne": 750.0,
            "top_30_depensiers": 850.0, "top_10_depensiers": 980.0,
            "benchmark_title": "Colocation / Studio IDF", "unit": "€/mois",
            "comment_eco": "Loyer et charges très bien maîtrisés en colocation.",
            "comment_avg": "Loyer conforme au coût moyen étudiant en Île-de-France.",
            "comment_high": "Part de loyer élevée par rapport aux étudiants parisiens."
        },
        "Alimentation": {
            "top_10_economes": 160.0, "top_30_economes": 220.0, "moyenne": 280.0,
            "top_30_depensiers": 350.0, "top_10_depensiers": 450.0,
            "benchmark_title": "Courses & Supermarché", "unit": "€/mois",
            "comment_eco": "Budget alimentaire très rigoureux (cuisine maison, hard-discount).",
            "comment_avg": "Panier alimentaire conforme à la moyenne étudiante.",
            "comment_high": "Dépenses alimentaires élevées (achats d'appoint fréquents)."
        },
        "Sorties & Loisirs": {
            "top_10_economes": 50.0, "top_30_economes": 100.0, "moyenne": 160.0,
            "top_30_depensiers": 230.0, "top_10_depensiers": 320.0,
            "benchmark_title": "Bars, Restos & Livraisons", "unit": "€/mois",
            "comment_eco": "Dépenses de loisirs très modérées.",
            "comment_avg": "Niveau de sorties conforme à la moyenne étudiante.",
            "comment_high": "Poste au-dessus de la majorité des pairs (commandes repas & shopping)."
        },
        "Transports": {
            "top_10_economes": 20.0, "top_30_economes": 35.0, "moyenne": 42.0,
            "top_30_depensiers": 65.0, "top_10_depensiers": 95.0,
            "benchmark_title": "Navigo & Mobilité", "unit": "€/mois",
            "comment_eco": "Usage exclusif des mobilités douces ou vélo.",
            "comment_avg": "Navigo avec prise en charge employeur 50%.",
            "comment_high": "Nombreux trajets VTC / taxis en complément des transports."
        },
        "Abonnements & Services": {
            "top_10_economes": 15.0, "top_30_economes": 25.0, "moyenne": 35.0,
            "top_30_depensiers": 55.0, "top_10_depensiers": 80.0,
            "benchmark_title": "Forfaits & Abonnements", "unit": "€/mois",
            "comment_eco": "Abonnements réduits au strict nécessaire.",
            "comment_avg": "Forfait mobile et un service de streaming musical.",
            "comment_high": "Cumul important d'abonnements numériques et audiovisuels."
        },
        "Autre": {
            "top_10_economes": 20.0, "top_30_economes": 40.0, "moyenne": 60.0,
            "top_30_depensiers": 90.0, "top_10_depensiers": 140.0,
            "benchmark_title": "Dépenses diverses & Imprévus", "unit": "€/mois",
            "comment_eco": "Imprévus quasi nuls.",
            "comment_avg": "Dépenses diverses courantes sous contrôle.",
            "comment_high": "Volume important de dépenses imprévues ou shopping."
        }
    }


def get_category_breakdown(
    transactions: List[Transaction],
    user_id: str,
    peers_benchmark_data: Dict[str, Dict],
    window_days: int = 30
) -> Tuple[Dict[str, float], Dict[str, Dict], Dict[str, Dict[str, float]]]:
    """
    Calcule la ventilation des dépenses par catégorie et sous-catégorie sur les 30 derniers jours,
    et fournit la comparaison statistique avec les pairs.
    """
    user_txs = [tx for tx in transactions if tx.user_id == user_id and not tx.is_settlement]
    if not user_txs:
        return {}, {}, {}

    max_date = max(tx.date for tx in user_txs)
    start_date = max_date - timedelta(days=window_days)

    recent_txs = [
        tx for tx in user_txs
        if start_date <= tx.date <= max_date and tx.category != "Revenus & Aides" and tx.amount > 0
    ]

    categories: Dict[str, float] = {}
    subcategories: Dict[str, Dict[str, float]] = {}

    for tx in recent_txs:
        cat = tx.category
        subcat = tx.subcategory
        categories[cat] = categories.get(cat, 0.0) + tx.amount
        if cat not in subcategories:
            subcategories[cat] = {}
        subcategories[cat][subcat] = subcategories.get(subcat, 0.0) + tx.amount

    peers_result: Dict[str, Dict] = {}
    all_cats = list(dict.fromkeys(list(peers_benchmark_data.keys()) + list(categories.keys())))

    for cat in all_cats:
        spent = categories.get(cat, 0.0)
        b = peers_benchmark_data.get(cat, {
            "top_10_economes": 30.0,
            "top_30_economes": 50.0,
            "moyenne": 80.0,
            "top_30_depensiers": 120.0,
            "top_10_depensiers": 180.0,
            "benchmark_title": cat,
            "unit": "€/mois",
            "comment_eco": "Dépenses bien maîtrisées.",
            "comment_avg": "Dépenses dans la moyenne.",
            "comment_high": "Dépenses élevées."
        })

        avg = float(b.get("moyenne", 100.0))
        p10 = float(b.get("top_10_economes", avg * 0.5))
        p30 = float(b.get("top_30_economes", avg * 0.75))
        p70 = float(b.get("top_30_depensiers", avg * 1.35))
        p90 = float(b.get("top_10_depensiers", avg * 1.8))

        if spent <= p10:
            tier = "top_10_eco"
            status = "Top 10% plus économe 🏆"
            relative_position = "Vous faites partie du top 10% des plus économes (vous dépensez moins que 90% de vos pairs)"
            color = "#1B5E20"
            tier_idx = 1
            comment = b.get("comment_eco", "Gestion des dépenses remarquablement économe.")
        elif spent <= p30:
            tier = "top_30_eco"
            status = "Top 30% économe 🟢"
            relative_position = "Vous faites partie du top 30% des plus économes (vous dépensez moins que 70% de vos pairs)"
            color = "#2E8B57"
            tier_idx = 2
            comment = b.get("comment_eco", "Dépenses bien maîtrisées en-dessous de la moyenne.")
        elif spent <= p70:
            tier = "moyenne"
            status = "Dans la moyenne 👍"
            relative_position = "Vous vous situez dans la moyenne de vos pairs"
            color = "#F39C12"
            tier_idx = 3
            comment = b.get("comment_avg", "Dépenses conformes au panier moyen des pairs.")
        elif spent <= p90:
            tier = "top_30_dep"
            status = "Top 30% moins économe ⚠️"
            relative_position = "Vous dépensez plus que 70% de vos pairs (top 30% des moins économes)"
            color = "#E67E22"
            tier_idx = 4
            comment = b.get("comment_high", "Dépenses supérieures à la majorité des pairs.")
        else:
            tier = "top_10_dep"
            status = "Top 10% moins économe 🚨"
            relative_position = "Vous dépensez plus que 90% de vos pairs (top 10% des moins économes)"
            color = "#D9534F"
            tier_idx = 5
            comment = b.get("comment_high", "Poste de dépense très élevé parmi les 10% les plus dépensiers.")

        delta = spent - avg
        ratio = spent / avg if avg > 0 else 1.0

        peers_result[cat] = {
            "avg": avg,
            "moyenne": avg,
            "top_10_economes": p10,
            "top_30_economes": p30,
            "top_30_depensiers": p70,
            "top_10_depensiers": p90,
            "benchmark_title": b.get("benchmark_title", cat),
            "unit": b.get("unit", "€/mois"),
            "color": color,
            "status": status,
            "relative_position": relative_position,
            "tier": tier,
            "tier_idx": tier_idx,
            "delta": delta,
            "ratio": ratio,
            "comment": comment
        }

    return categories, peers_result, subcategories
