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

    return {}


def get_category_breakdown(
    transactions: List[Transaction],
    user_id: str,
    peers_benchmark_data: Dict[str, Dict],
    window_days: int = 30
) -> Tuple[Dict[str, float], Dict[str, Dict], Dict[str, Dict[str, float]]]:
    """
    Calcule la ventilation des dépenses par catégorie et sous-catégorie sur les 30 derniers jours,
    et fournit la comparaison statistique avec les pairs (uniquement pour les catégories réelles).
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

    for cat, spent in categories.items():
        if cat not in peers_benchmark_data:
            continue

        b = peers_benchmark_data[cat]
        avg = float(b.get("moyenne", 0.0))
        p10 = float(b.get("top_10_economes", avg * 0.5))
        p30 = float(b.get("top_30_economes", avg * 0.75))
        p70 = float(b.get("top_30_depensiers", avg * 1.35))
        p90 = float(b.get("top_10_depensiers", avg * 1.8))

        if spent <= p10:
            tier = "top_10_eco"
            status = "Top 10% plus économe 🏆"
            relative_position = "Top 10% des plus économes"
            color = "#1B5E20"
            tier_idx = 1
        elif spent <= p30:
            tier = "top_30_eco"
            status = "Top 30% économe 🟢"
            relative_position = "Top 30% des plus économes"
            color = "#2E8B57"
            tier_idx = 2
        elif spent <= p70:
            tier = "moyenne"
            status = "Dans la moyenne 👍"
            relative_position = "Dans la moyenne des pairs"
            color = "#F39C12"
            tier_idx = 3
        elif spent <= p90:
            tier = "top_30_dep"
            status = "Top 30% moins économe ⚠️"
            relative_position = "Top 30% des moins économes"
            color = "#E67E22"
            tier_idx = 4
        else:
            tier = "top_10_dep"
            status = "Top 10% moins économe 🚨"
            relative_position = "Top 10% des plus dépensiers"
            color = "#D9534F"
            tier_idx = 5

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
            "ratio": ratio
        }

    return categories, peers_result, subcategories
