"""
Utilitaires de période d'analyse partagés par les services et les outils IA.
"""

from datetime import datetime, timedelta
from typing import List, Tuple
from models import Transaction


def personal_transactions(transactions: List[Transaction], user_id: str) -> List[Transaction]:
    """Opérations de l'utilisateur, hors virements de règlement entre membres."""
    return [tx for tx in transactions if tx.user_id == user_id and not tx.is_settlement]


def rolling_window_bounds(transactions: List[Transaction], window_days: int = 30) -> Tuple[datetime, datetime]:
    """
    Bornes (début, fin) de la fenêtre glissante qui se termine à la dernière opération.
    Le début est calé sur minuit pour qu'une opération saisie en cours de journée
    ne fasse pas sortir tout le premier jour de la fenêtre.
    """
    end = max((tx.date for tx in transactions), default=datetime.now())
    start = (end - timedelta(days=window_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, end
