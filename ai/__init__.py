"""
Package IA : Coach patrimonial et conseiller budgétaire.
Expose la façade unifiée BankingAIAdvisor pour une rétro-compatibilité totale.
"""

from typing import Dict, List, Optional, Any
from models import UserProfile
from ai.hf_client import HFClient
from ai.context_builder import load_public_aids_reference
from ai.audit_service import stream_financial_audit
from ai.chat_service import ask_advisor


class BankingAIAdvisor:
    """Façade unifiée pour les services d'intelligence artificielle."""

    def __init__(self, hf_token: Optional[str] = None):
        self.client_manager = HFClient(token=hf_token)
        self.aids_reference: Dict[str, List[Dict]] = load_public_aids_reference()

    @property
    def hf_token(self) -> Optional[str]:
        return self.client_manager.hf_token

    @property
    def default_model(self) -> str:
        return self.client_manager.default_model

    @property
    def init_error(self) -> Optional[str]:
        return self.client_manager.init_error

    @property
    def last_execution_time(self) -> float:
        return self.client_manager.last_execution_time

    @property
    def client(self):
        return self.client_manager.client

    def set_token(self, token: Optional[str] = None):
        self.client_manager.set_token(token)

    def is_hf_configured(self) -> bool:
        return self.client_manager.is_configured()

    def stream_financial_audit(
        self,
        profile: UserProfile,
        budget_data: Dict,
        categories: Dict[str, float],
        subcategories: Dict[str, Dict[str, float]],
        peers_benchmark: Dict[str, Dict],
        extra_context: Optional[Dict] = None
    ):
        return stream_financial_audit(
            hf_client=self.client_manager,
            profile=profile,
            budget_data=budget_data,
            categories=categories,
            subcategories=subcategories,
            peers_benchmark=peers_benchmark,
            aids_reference=self.aids_reference,
            extra_context=extra_context
        )

    def ask_advisor(self, question: str, profile: UserProfile, budget_summary: str = "") -> str:
        return ask_advisor(
            hf_client=self.client_manager,
            question=question,
            profile=profile,
            budget_summary=budget_summary,
            aids_reference=self.aids_reference
        )


__all__ = ["BankingAIAdvisor", "HFClient"]
