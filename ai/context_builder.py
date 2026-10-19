"""
Prompts système du coach conversationnel.
"""

from models import UserProfile


def build_compact_agent_prompt(profile: UserProfile, country: str = "France") -> str:
    """Génère un prompt initial très compact pour le coach agentique."""
    family_sit = getattr(profile, "family_situation", "Célibataire")
    job = getattr(profile, "job_activity", profile.status)
    housing = getattr(profile, "housing_type", "Colocation")
    custom_notes = getattr(profile, "custom_notes", "").strip()

    return f"""Tu es un conseiller financier expert, empathique et pragmatique.
Profil client : {profile.name}, {profile.age} ans | {country} | {profile.city}.
Situation : {family_sit} | {job} ({profile.school_or_company}).
Logement : {housing} (Loyer débité : {profile.rent_amount:.0f} € / mois).
Revenu net déclaré : {profile.monthly_net_income:.0f} € / mois.
Objectifs client : "{custom_notes or 'Aucun projet spécifique déclaré'}".

Tu disposes d'outils d'audit pour explorer les dépenses et les aides en temps réel."""


def build_chat_system_prompt(
    profile: UserProfile,
    budget_summary: str = "",
    country: str = "France",
    aids_guide: str = ""
) -> str:
    """System prompt compact pour l'assistant conversationnel."""
    base = build_compact_agent_prompt(profile, country)
    if budget_summary:
        base += f"\nContexte bancaire immédiat : {budget_summary}"
    base += (
        "\n\nConsignes :"
        "\n- Réponds de manière percutante, personnalisée et chiffrée."
        "\n- Si tu identifies une opportunité d'aide ou d'épargne, termine ta réponse par des recommandations concrètes."
    )
    return base

