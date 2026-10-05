"""
Service d'assistant financier conversationnel interactif.
"""

from typing import Dict
from models import UserProfile
from ai.hf_client import HFClient
from ai.context_builder import format_aids_guide, build_chat_system_prompt


def ask_advisor(
    hf_client: HFClient,
    question: str,
    profile: UserProfile,
    budget_summary: str,
    aids_reference: Dict
) -> str:
    """
    Répond aux questions de l'utilisateur via le LLM.
    Retourne un message d'erreur clair si non configuré.
    """
    if not hf_client.is_configured():
        return (
            "⚠️ **Assistant IA non connecté** : Aucun token Hugging Face n'est actuellement configuré. "
            "Veuillez renseigner un token Hugging Face valide dans l'application pour activer le dialogue avec le coach."
        )

    country = getattr(profile, "country", "France")
    aids_guide = format_aids_guide(aids_reference, country)
    system_prompt = build_chat_system_prompt(profile, budget_summary, country, aids_guide)

    try:
        messages = [
            ("system", system_prompt),
            ("user", question)
        ]
        response = hf_client.client.invoke(messages)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            return "\n".join(
                item.get("text", str(item)) if isinstance(item, dict) else str(item)
                for item in content
            )
        return str(content)
    except Exception as e:
        return f"⚠️ **Erreur lors de la communication avec le modèle IA Hugging Face** : {type(e).__name__} - {str(e)}"
