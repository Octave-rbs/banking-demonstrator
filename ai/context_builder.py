"""
Construction et formatage du contexte financier pour les prompts LLM.
"""

import os
import json
from typing import Dict, List, Optional
from models import UserProfile


def load_public_aids_reference(filepath: Optional[str] = None) -> Dict[str, List[Dict]]:
    """Charge le catalogue neutre des dispositifs d'aides sociales."""
    json_path = filepath or os.path.join("data", "public_aids_reference.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ContextBuilder] Erreur chargement public_aids_reference.json : {e}")
    return {}


def format_aids_guide(
    aids_reference: Dict[str, List[Dict]],
    country: str,
    targeted_aids: Optional[List[Dict]] = None
) -> str:
    """Formate le guide des aides publiques applicable au pays du profil."""
    if targeted_aids:
        matched_aids = targeted_aids
    else:
        country_key = country.strip().lower()
        matched_aids = []
        for c_name, aids in aids_reference.items():
            if c_name.lower() == country_key:
                matched_aids = aids
                break
        if not matched_aids:
            matched_aids = aids_reference.get("France", [])

    lines = [f"RÉFÉRENTIEL DES DISPOSITIFS SOCIAUX ANALYSÉS ({country.upper()}) :"]
    for aid in matched_aids:
        lines.append(f"• Dispositif : {aid.get('name', 'N/A')} (Organisme : {aid.get('organism', 'N/A')})")
        lines.append(f"  - Public éligible : {aid.get('target_group', '')}")
        criteria = "; ".join(aid.get('eligibility_criteria', []))
        lines.append(f"  - Critères indicatifs : {criteria}")
        lines.append(f"  - Gain indicatif : {aid.get('typical_benefit', 'Non spécifié')}")
        lines.append(f"  - Démarche : {aid.get('procedure', 'En ligne')}")
        lines.append("")
    return "\n".join(lines)


def format_audit_context(
    profile: UserProfile,
    budget_data: Dict,
    categories: Dict[str, float],
    subcategories: Dict[str, Dict[str, float]],
    peers: Dict[str, Dict],
    aids_reference: Dict[str, List[Dict]],
    extra_context: Optional[Dict] = None
) -> str:
    """Génère le contexte complet, neutre et factuel pour l'audit financier."""
    country_str = getattr(profile, "country", "France")
    custom_notes_str = profile.custom_notes.strip() if profile.custom_notes else "Aucun projet spécifique déclaré."

    detected_incomes = extra_context.get("detected_incomes", []) if extra_context else []
    if detected_incomes:
        incomes_str = "\n".join([f"  * {inc}" for inc in detected_incomes])
    else:
        incomes_str = f"  * Rémunération nette déclarée : {profile.monthly_net_income:.2f} €"

    rolling_spent = budget_data.get("rolling_spent", budget_data.get("total_spent", 0.0))
    rolling_fixed = budget_data.get("rolling_fixed", 0.0)
    rolling_variable = budget_data.get("rolling_variable", 0.0)
    rolling_remaining = budget_data.get("rolling_remaining", 0.0)
    is_over_budget = budget_data.get("is_over_budget", False)
    budget_health = "Dépassement de budget (marge nette négative)" if is_over_budget else "Budget équilibré (marge positive)"

    peer_comparison_list = extra_context.get("peer_comparison_summary", []) if extra_context else []
    if peer_comparison_list:
        peer_summary_str = "\n".join(peer_comparison_list)
    else:
        peer_summary_str = "\n".join([f"- {cat}: {spent:.2f} €" for cat, spent in categories.items()])

    subcats_lines = []
    for cat, subs in subcategories.items():
        if subs:
            subs_formatted = ", ".join([f"{k}: {v:.2f} €" for k, v in subs.items()])
            subcats_lines.append(f"  * {cat} : {subs_formatted}")
    subcats_str = "\n".join(subcats_lines) if subcats_lines else "Non ventilé"

    subscriptions_str = ", ".join(extra_context.get("subscriptions", [])) if extra_context and extra_context.get("subscriptions") else "Non détectés"
    largest_expense_str = extra_context.get("largest_expense", "N/A") if extra_context else "N/A"

    targeted_aids = extra_context.get("targeted_aids") if extra_context else None
    aids_guide_str = format_aids_guide(aids_reference, country_str, targeted_aids=targeted_aids)

    return f"""=== PROFIL DU CLIENT ===
- Nom : {profile.name}, {profile.age} ans
- Pays de résidence : {country_str}
- Ville : {profile.city}
- Situation familiale : {getattr(profile, 'family_situation', 'Célibataire')}
- Activité / Emploi : {getattr(profile, 'job_activity', profile.status)} ({profile.school_or_company})
- Logement : {getattr(profile, 'housing_type', 'Colocation')}
- Part de loyer débitée : {profile.rent_amount:.2f} € / mois
- Rémunération déclarée : {profile.monthly_net_income:.2f} € / mois
- Objectifs / Précisions libres du client : "{custom_notes_str}"

=== FLUX DE TRÉSORERIE RÉELS SUR LES 30 DERNIERS JOURS ===
- Entrées d'argent et revenus identifiés sur le compte bancaire :
{incomes_str}
- Dépenses totales sur 30 jours : {rolling_spent:.2f} € (Charges fixes : {rolling_fixed:.2f} €, Dépenses courantes variables : {rolling_variable:.2f} €)
- Reste à vivre actuel sur 30 jours : {rolling_remaining:.2f} €
- Diagnostic d'équilibre budgétaire : {budget_health}
- Abonnements récurrents identifiés : {subscriptions_str}
- Dépense ponctuelle la plus importante : {largest_expense_str}

=== ANALYSE COMPARATIVE AVEC LES PAIRS DU MÊME PROFIL (Île-de-France / Tranche similaire) ===
{peer_summary_str}

Détail des dépenses par sous-catégorie :
{subcats_str}

=== GUIDE DOCUMENTAIRE RÉGLEMENTAIRE (RÉFÉRENCE OFFICIELLE) ===
{aids_guide_str}
"""


def build_audit_prompt(context: str, country: str = "France") -> str:
    """Prompt d'audit financier structuré avec consignes claires."""
    return f"""Tu es un coach financier bienveillant et expert en budget. Ton but est d'accompagner l'utilisateur pour assainir sa trésorerie sans le culpabiliser. 

Rédige un BILAN PERSONNEL CHALEUREUX ET PERCUTANT, spécialement adapté pour ce profil en {country}. 

{context}

CONSIGNES DE RÉDACTION ET D'EXPERTISE :
1. TON ET STYLE (CRITIQUE) :
   - Adresse-toi DIRECTEMENT à l'utilisateur en utilisant le "tu" (ou le "vous"). Ne parle jamais de lui à la troisième personne.
   - Adopte un ton encourageant, humain et direct.
   - Fais preuve d'empathie face à sa situation.
   - Utilise un format fluide : mets en gras les chiffres clés, utilise des listes à puces aérées, mais rédige des phrases naturelles de transition.

2. OPTIMISATION DES REVENUS :
   - S'il manque des aides publiques dans ses flux récents, explique comment accéder à ces aides. 
   - Donne le gain mensuel estimé en € et les 2-3 démarches exactes à suivre de façon très simple.

3. DIMINUTION DES DÉPENSES :
   - Identifie le poste où ses dépenses s'écartent de la moyenne des profils similaires. 
   - Formule 2 recommandations concrètes et chiffrées en € pour réduire ces frais dans cette catégorie pour revenir dans la moyenne. (ex: dépense mode excessive le mois dernier et livraison de nourriture)

4. ÉPARGNE & PROJETS :
   - Propose une stratégie d'épargne réaliste par rapport à son reste à vivre.
   - Suggère un support adapté et relie cet effort directement à la réussite de ses projets personnels.

STRUCTURE ATTENDUE (utilise ces titres comme trame narrative fluide) :

## Ton Diagnostic & Tes Points Forts
## Optimisation de tes revenus
## Gérer ton budget
## Ta stratégie d'épargne & tes projets
"""


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

