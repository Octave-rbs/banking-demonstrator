"""
Calcul instantané (< 5ms) du Score de Santé Budgétaire (/100) sur 3 piliers.
"""

from typing import Dict, Any
from models import UserProfile


def calculate_health_score(
    profile: UserProfile,
    budget: Dict,
    categories: Dict[str, float],
    peers: Dict[str, Dict]
) -> Dict[str, Any]:
    """
    Calcule instantanément le Score de Santé Budgétaire (/100) et les 3 piliers :
    1. Équilibre & Trésorerie (40 pts)
    2. Structure Budgétaire / Règle 50-30-20 (30 pts)
    3. Positionnement vs Pairs (30 pts)
    """
    rolling_income = budget.get("rolling_income", profile.monthly_net_income) or profile.monthly_net_income or 1200.0
    rolling_spent = budget.get("rolling_spent", 0.0)
    rolling_fixed = budget.get("rolling_fixed", 0.0)
    rolling_remaining = budget.get("rolling_remaining", 0.0)
    is_over_budget = budget.get("is_over_budget", False)

    # --- Pilier 1 : Équilibre & Trésorerie (40 pts) ---
    expense_ratio = (rolling_spent / rolling_income) if rolling_income > 0 else 1.0
    if is_over_budget or rolling_spent > rolling_income:
        deficit = max(0.0, rolling_spent - rolling_income)
        deficit_str = f"déficit de {deficit:.0f} € sur 30j" if deficit > 0 else "dépenses supérieures aux rentrées"
        p1_score = max(5, int(30 / expense_ratio))
        p1_verdict = f"Budget sous tension : {deficit_str}"
        p1_status = "warning"
    elif expense_ratio <= 0.75:
        p1_score = 40
        p1_verdict = f"Trésorerie excellente : {rolling_remaining:.0f} € de marge d'épargne"
        p1_status = "safe"
    elif expense_ratio <= 0.90:
        p1_score = 35
        p1_verdict = f"Budget équilibré : {rolling_remaining:.0f} € de reste à vivre"
        p1_status = "safe"
    elif expense_ratio <= 1.0:
        p1_score = 30
        p1_verdict = f"Marge étroite : {rolling_remaining:.0f} € disponibles"
        p1_status = "warning"
    else:
        p1_score = 30
        p1_verdict = "Équilibre fragile : budget presque intégralement consommé"
        p1_status = "warning"

    # --- Pilier 2 : Structure Budgétaire / Règle 50-30-20 (30 pts) ---
    fixed_ratio = (rolling_fixed / rolling_income) if rolling_income > 0 else 0.5
    if fixed_ratio <= 0.50:
        p2_score = 30
        p2_verdict = f"Charges fixes sous contrôle ({fixed_ratio * 100:.0f}% des revenus)"
        p2_status = "safe"
    elif fixed_ratio <= 0.60:
        p2_score = 23
        p2_verdict = f"Charges fixes modérées ({fixed_ratio * 100:.0f}% des revenus)"
        p2_status = "safe"
    elif fixed_ratio <= 0.70:
        p2_score = 15
        p2_verdict = f"Poids important des fixes ({fixed_ratio * 100:.0f}% des revenus)"
        p2_status = "warning"
    else:
        p2_score = 8
        p2_verdict = f"Charges fixes prépondérantes ({fixed_ratio * 100:.0f}% des revenus)"
        p2_status = "danger"

    # --- Pilier 3 : Positionnement vs Pairs (30 pts) ---
    critical_count = 0
    moderate_count = 0
    max_gap_cat = None
    max_gap_val = 0.0

    for cat, spent in categories.items():
        if cat in peers:
            avg = peers[cat].get("avg", 0.0)
            p90 = peers[cat].get("top_10_depensiers", avg * 1.5)
            gap = spent - avg
            if gap > max_gap_val:
                max_gap_val = gap
                max_gap_cat = cat
            if spent >= p90 or gap >= 100.0:
                critical_count += 1
            elif gap >= 25.0:
                moderate_count += 1

    p3_score = max(5, 30 - (critical_count * 10) - (moderate_count * 4))
    if critical_count == 0 and moderate_count == 0:
        p3_verdict = "Dépenses conformes ou plus sobres que la moyenne des pairs"
        p3_status = "safe"
    elif critical_count == 0:
        p3_verdict = f"{moderate_count} poste(s) légèrement au-dessus de la moyenne"
        p3_status = "warning"
    else:
        gap_info = f" (notamment {max_gap_cat} : +{max_gap_val:.0f} €)" if max_gap_cat else ""
        p3_verdict = f"Écart notable avec les pairs{gap_info}"
        p3_status = "danger"

    total_score = min(100, max(0, p1_score + p2_score + p3_score))
    if total_score >= 80:
        overall_status = "Excellente santé"
        color = "#2E8B57"
        badge = "🟢 Excellente santé"
        summary = "Vos finances sont saines et pérennes avec une bonne capacité d'épargne."
    elif total_score >= 60:
        overall_status = "Situation équilibrée"
        color = "#D97706"
        badge = "🟡 Situation équilibrée"
        summary = "Trésorerie globalement stable avec des marges d'optimisation identifiées."
    else:
        overall_status = "Vigilance requise"
        color = "#DC2626"
        badge = "🔴 Vigilance requise"
        summary = "Budget sous tension : des arbitrages rapides sont recommandés."

    return {
        "total_score": total_score,
        "status": overall_status,
        "badge": badge,
        "color": color,
        "summary": summary,
        "pillars": {
            "treasury": {
                "title": "Équilibre Trésorerie",
                "score": p1_score,
                "max_score": 40,
                "verdict": p1_verdict,
                "status": p1_status,
                "ratio": round(p1_score / 40, 2)
            },
            "structure": {
                "title": "Structure 50/30/20",
                "score": p2_score,
                "max_score": 30,
                "verdict": p2_verdict,
                "status": p2_status,
                "ratio": round(p2_score / 30, 2)
            },
            "peers": {
                "title": "Maîtrise vs Pairs",
                "score": p3_score,
                "max_score": 30,
                "verdict": p3_verdict,
                "status": p3_status,
                "ratio": round(p3_score / 30, 2)
            }
        }
    }
