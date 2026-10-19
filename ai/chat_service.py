"""
Service d'assistant financier conversationnel agentique et interactif.
Permet au coach de faire appel aux outils d'audit pour répondre précisément
et de proposer des cartes d'actions contextuelles en 1 clic.
"""

import json
from typing import Dict, List, Any, Tuple
from models import UserProfile
from services import BankBackend
from ai.hf_client import HFClient
from ai.tools import AUDIT_TOOLS_SPECS, execute_tool, OFFICIAL_AID_URLS
from ai.context_builder import build_chat_system_prompt
from ai.agent_runner import extract_tool_call, extract_action_cards


def ask_advisor_agentic(
    hf_client: HFClient,
    question: str,
    profile: UserProfile,
    db: BankBackend,
    user_id: str,
    budget_summary: str = "",
    max_steps: int = 3
) -> Tuple[str, List[Dict[str, Any]], List[str]]:
    """
    Traite la question de l'utilisateur avec capacité d'interrogation d'outils.
    Retourne : (texte_reponse, liste_cartes_actions, liste_etapes_executees).
    """
    if not hf_client.is_configured():
        return (
            "⚠️ **Assistant IA non connecté** : Aucune clé API Groq n'est actuellement configurée. "
            "Veuillez renseigner une clé API Groq valide pour dialoguer avec votre coach.",
            [],
            []
        )

    country = getattr(profile, "country", "France")
    base_prompt = build_chat_system_prompt(profile, budget_summary=budget_summary, country=country)
    tools_doc = json.dumps(AUDIT_TOOLS_SPECS, ensure_ascii=False, indent=1)

    system_prompt = f"""{base_prompt}

Tu disposes des outils d'audit suivants :
{tools_doc}

Si la question nécessite d'inspecter les données réelles (dépenses, aides, abonnements, pairs), appelle un outil via :
```tool_call
{{
  "tool": "nom_outil",
  "parameters": {{}}
}}
```
Sinon, réponds directement. Si ta réponse suggère une démarche ou une action d'épargne, termine par un bloc d'actions :
```actions
[
  {{
    "id": "action_id",
    "type": "external_link",
    "icon": "🏛️",
    "title": "Titre",
    "description": "Courte description",
    "button_label": "Bouton"
  }}
]
```
Pour une carte "external_link", "id" doit être l'un de : {", ".join(OFFICIAL_AID_URLS)}. Le lien officiel est ajouté automatiquement, n'écris jamais d'URL.
"""

    messages = [
        ("system", system_prompt),
        ("user", question)
    ]

    steps_log = []

    for step_idx in range(max_steps):
        try:
            response = hf_client.client.invoke(messages)
            content = getattr(response, "content", response)
            res_text = "\n".join(str(i) for i in content) if isinstance(content, list) else str(content)
        except Exception as e:
            return f"⚠️ Erreur LLM : {str(e)}", [], steps_log

        tool_call = extract_tool_call(res_text)
        if tool_call and step_idx < max_steps - 1:
            tool_name, tool_params = tool_call
            steps_log.append(f"🔍 Outil `{tool_name}` interrogé")
            obs = execute_tool(tool_name, tool_params, db, user_id)
            messages.append(("assistant", res_text))
            messages.append((
                "user",
                f"OBSERVATION DE L'OUTIL `{tool_name}` :\n{json.dumps(obs, ensure_ascii=False, indent=1)}\nRéponds à la question initiale de l'utilisateur."
            ))
        else:
            cleaned_text, action_cards = extract_action_cards(res_text)
            return cleaned_text, action_cards, steps_log

    cleaned_text, action_cards = extract_action_cards(res_text)
    return cleaned_text, action_cards, steps_log
