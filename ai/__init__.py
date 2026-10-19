"""
Package IA : Coach patrimonial et conseiller budgétaire agentique.
Expose la façade unifiée BankingAIAdvisor pour orchestrer les modules spécialisés.
"""

from typing import Dict, List, Optional, Any, Generator, Tuple
from models import UserProfile
from services import BankBackend
from ai.hf_client import HFClient
from ai.agent_runner import run_agentic_audit
from ai.chat_service import ask_advisor_agentic
from ai.tools import AUDIT_TOOLS_SPECS, execute_tool, OFFICIAL_AID_URLS


class BankingAIAdvisor:
    """Façade unifiée pour les services d'intelligence artificielle et d'agentique."""

    def __init__(self, hf_token: Optional[str] = None):
        self.client_manager = HFClient(token=hf_token)

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

    def stream_financial_audit(self, db: BankBackend, user_id: str) -> Generator[Dict[str, Any], None, None]:
        """Lance l'audit et restitue ses événements (rapport final ou erreur)."""
        yield from run_agentic_audit(self.client_manager, db, user_id)

    def ask_advisor_agentic(
        self,
        question: str,
        profile: UserProfile,
        db: BankBackend,
        user_id: str,
        budget_summary: str = ""
    ) -> Tuple[str, List[Dict[str, Any]], List[str]]:
        """Mode agentique conversationnel retournant texte, cartes d'actions et étapes."""
        return ask_advisor_agentic(
            hf_client=self.client_manager,
            question=question,
            profile=profile,
            db=db,
            user_id=user_id,
            budget_summary=budget_summary
        )


__all__ = ["BankingAIAdvisor", "HFClient", "AUDIT_TOOLS_SPECS", "execute_tool", "OFFICIAL_AID_URLS"]
