"""
Package IA : Coach patrimonial et conseiller budgétaire agentique.
Expose la façade unifiée BankingAIAdvisor pour orchestrer les modules spécialisés.
"""

from typing import Dict, List, Optional, Any, Generator, Tuple
from models import UserProfile
from services import BankBackend
from ai.hf_client import HFClient
from ai.context_builder import load_public_aids_reference
from ai.audit_service import stream_agentic_audit
from ai.chat_service import ask_advisor, ask_advisor_agentic
from ai.tools import AUDIT_TOOLS_SPECS, execute_tool, OFFICIAL_AID_URLS


class BankingAIAdvisor:
    """Façade unifiée pour les services d'intelligence artificielle et d'agentique."""

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
        budget_data: Optional[Dict] = None,
        categories: Optional[Dict[str, float]] = None,
        subcategories: Optional[Dict[str, Dict[str, float]]] = None,
        peers_benchmark: Optional[Dict[str, Dict]] = None,
        extra_context: Optional[Dict] = None,
        db: Optional[BankBackend] = None,
        user_id: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Lance l'audit agentique avec appels d'outils et restitution d'événements.
        """
        target_uid = user_id or getattr(profile, "id", "u1")
        if db is not None:
            yield from stream_agentic_audit(self.client_manager, db, target_uid)
        else:
            # Si db n'est pas passé directement, on renvoie une erreur explicite
            yield {
                "type": "error",
                "message": "Erreur : BankBackend requis pour l'exécution des outils d'audit."
            }

    def ask_advisor(
        self,
        question: str,
        profile: UserProfile,
        budget_summary: str = "",
        db: Optional[BankBackend] = None,
        user_id: Optional[str] = None
    ) -> str:
        """Répond à une question dans le chat conversationnel."""
        return ask_advisor(
            hf_client=self.client_manager,
            question=question,
            profile=profile,
            budget_summary=budget_summary,
            aids_reference=self.aids_reference,
            db=db,
            user_id=user_id
        )

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
