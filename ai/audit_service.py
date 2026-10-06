"""
Génération agentique du rapport d'audit financier exécutif.
Orchestre l'appel d'outils d'audit, la restitution des étapes et l'émission des actions en 1 clic.
"""

from typing import Dict, Optional, Generator, Any
from models import UserProfile
from services import BankBackend
from ai.hf_client import HFClient
from ai.agent_runner import run_agentic_audit


def stream_agentic_audit(
    hf_client: HFClient,
    db: BankBackend,
    user_id: str,
    max_steps: int = 5
) -> Generator[Dict[str, Any], None, None]:
    """
    Exécute l'audit financier agentique.
    Émet les événements d'étapes d'outils et la synthèse finale avec cartes d'actions.
    """
    yield from run_agentic_audit(
        hf_client=hf_client,
        db=db,
        user_id=user_id,
        max_steps=max_steps
    )
