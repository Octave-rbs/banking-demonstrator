"""
Moteur d'analyse budgétaire (mois glissant 30 jours et mois calendaire en cours).
"""

from datetime import timedelta
from typing import Dict, List
from models import Transaction, UserProfile


def analyze_monthly_budget(
    transactions: List[Transaction],
    profile: UserProfile,
    user_id: str
) -> Dict:
    """
    Analyse détaillée du budget :
    - Mois glissant (30 jours) : base d'analyse de fond pour le chatbot et comparaison aux pairs.
    - Mois en cours (ex: du 1er au 11) : indicateur des dépenses actuelles et reste à vivre de fin de mois.
    """
    user_txs = [tx for tx in transactions if tx.user_id == user_id and not tx.is_settlement]
    baseline_income = profile.monthly_net_income
    fixed_categories = ["Logement & Charges", "Abonnements & Services"]

    if not user_txs:
        return {
            "income": baseline_income,
            "baseline_income": baseline_income,
            "rolling_income": baseline_income,
            "rolling_spent": 0.0,
            "rolling_fixed": 0.0,
            "rolling_variable": 0.0,
            "rolling_remaining": baseline_income,
            "rolling_label": "Mois glissant (30 jours)",
            "calendar_spent": 0.0,
            "calendar_remaining": baseline_income,
            "calendar_projection": 0.0,
            "calendar_days_passed": 1,
            "calendar_total_days": 30,
            "calendar_label": "Mois en cours",
            "total_spent": 0.0,
            "fixed_expenses": 0.0,
            "variable_expenses": 0.0,
            "remaining": baseline_income,
            "projection": 0.0,
            "days_passed": 1,
            "total_days": 30,
            "ceiling": baseline_income,
            "status": "safe",
            "is_over_budget": False
        }

    max_date = max(tx.date for tx in user_txs)

    # 1. Mois glissant sur 30 jours
    rolling_start = max_date - timedelta(days=30)
    rolling_txs = [tx for tx in user_txs if rolling_start <= tx.date <= max_date]

    rolling_income_detected = sum(abs(tx.amount) for tx in rolling_txs if tx.category == "Revenus & Aides")
    rolling_income = max(rolling_income_detected, baseline_income)

    rolling_expense_txs = [tx for tx in rolling_txs if tx.category != "Revenus & Aides" and tx.amount > 0]
    rolling_fixed = sum(tx.amount for tx in rolling_expense_txs if tx.category in fixed_categories)
    rolling_variable = sum(tx.amount for tx in rolling_expense_txs if tx.category not in fixed_categories)
    rolling_total_spent = rolling_fixed + rolling_variable
    rolling_remaining = max(0.0, rolling_income - rolling_total_spent)
    rolling_label = f"Mois glissant (du {rolling_start.strftime('%d/%m')} au {max_date.strftime('%d/%m/%Y')})"

    # 2. Mois calendaire en cours
    calendar_txs = [
        tx for tx in user_txs
        if tx.date.year == max_date.year and tx.date.month == max_date.month
    ]
    calendar_expense_txs = [tx for tx in calendar_txs if tx.category != "Revenus & Aides" and tx.amount > 0]
    calendar_spent = sum(tx.amount for tx in calendar_expense_txs)
    calendar_remaining = max(0.0, baseline_income - calendar_spent)
    calendar_days_passed = max_date.day
    calendar_total_days = 30

    calendar_fixed = sum(tx.amount for tx in calendar_expense_txs if tx.category in fixed_categories)
    calendar_variable = sum(tx.amount for tx in calendar_expense_txs if tx.category not in fixed_categories)
    daily_rate = calendar_variable / max(1, calendar_days_passed)
    calendar_projection = calendar_fixed + (daily_rate * calendar_total_days)
    calendar_label = max_date.strftime("%B %Y").capitalize()

    calendar_days_remaining = max(1, calendar_total_days - calendar_days_passed)
    calendar_daily_allowance = max(0.0, calendar_remaining / calendar_days_remaining)

    # Diagnostic d'équilibre
    is_over_budget = (
        (rolling_total_spent > rolling_income) or
        (calendar_projection > baseline_income * 1.05) or
        (calendar_spent / baseline_income > (calendar_days_passed / calendar_total_days) * 1.35)
    )
    status = "danger" if is_over_budget else ("warning" if (calendar_spent / baseline_income > 0.8) else "safe")

    return {
        "income": rolling_income,
        "baseline_income": baseline_income,
        "rolling_income": rolling_income,
        "rolling_spent": rolling_total_spent,
        "rolling_fixed": rolling_fixed,
        "rolling_variable": rolling_variable,
        "rolling_remaining": rolling_remaining,
        "rolling_label": rolling_label,
        "rolling_period_days": 30,
        "calendar_spent": calendar_spent,
        "calendar_remaining": calendar_remaining,
        "calendar_projection": calendar_projection,
        "calendar_days_passed": calendar_days_passed,
        "calendar_total_days": calendar_total_days,
        "calendar_days_remaining": calendar_days_remaining,
        "calendar_daily_allowance": calendar_daily_allowance,
        "calendar_label": calendar_label,
        "current_month_label": calendar_label,
        "total_spent": rolling_total_spent,
        "fixed_expenses": rolling_fixed,
        "variable_expenses": rolling_variable,
        "remaining": calendar_remaining,
        "projection": calendar_projection,
        "days_passed": calendar_days_passed,
        "total_days": calendar_total_days,
        "ceiling": baseline_income,
        "status": status,
        "is_over_budget": is_over_budget
    }
