"""
Génération en streaming du rapport d'audit financier exécutif.
"""

import time
import traceback
from typing import Dict, Optional, Generator
from models import UserProfile
from ai.hf_client import HFClient
from ai.context_builder import format_audit_context, build_audit_prompt


def stream_financial_audit(
    hf_client: HFClient,
    profile: UserProfile,
    budget_data: Dict,
    categories: Dict[str, float],
    subcategories: Dict[str, Dict[str, float]],
    peers_benchmark: Dict[str, Dict],
    aids_reference: Dict,
    extra_context: Optional[Dict] = None
) -> Generator[str, None, None]:
    """
    Générateur de tokens en streaming pour le rapport exécutif de diagnostic.
    Émet les fragments de texte en direct pour affichage via st.write_stream.
    """
    if not hf_client.is_configured():
        hf_client.last_status = "error_no_token"
        if not hf_client.hf_token:
            hf_client.last_error = "Aucun token Hugging Face n'a été renseigné."
        else:
            hf_client.last_error = f"Échec d'initialisation du modèle ({hf_client.init_error or 'Erreur de connexion'})."
        yield f"⚠️ **Assistant IA non disponible :** {hf_client.last_error}\n\nVeuillez renseigner votre token Hugging Face pour lancer l'analyse."
        return

    t0 = time.time()
    country = getattr(profile, "country", "France")
    context = format_audit_context(
        profile=profile,
        budget_data=budget_data,
        categories=categories,
        subcategories=subcategories,
        peers=peers_benchmark,
        aids_reference=aids_reference,
        extra_context=extra_context
    )
    prompt = build_audit_prompt(context, country=country)
    messages = [
        ("system", f"Tu es un conseiller financier expert. Rédige un rapport exécutif d'audit clair et bienveillant pour un client en {country}."),
        ("user", prompt)
    ]

    full_chunks = []
    try:
        for chunk in hf_client.client.stream(messages):
            text_chunk = getattr(chunk, "content", chunk)
            if isinstance(text_chunk, list):
                text_chunk = "\n".join(
                    item.get("text", str(item)) if isinstance(item, dict) else str(item)
                    for item in text_chunk
                )
            else:
                text_chunk = str(text_chunk)
            if text_chunk:
                full_chunks.append(text_chunk)
                yield text_chunk

        hf_client.last_execution_time = time.time() - t0
        hf_client.last_raw_response = "".join(full_chunks)
        hf_client.last_status = "llm_success"
        hf_client.last_error = None
    except Exception:
        # Fallback sur invoke synchrone si le streaming direct échoue
        try:
            response = hf_client.client.invoke(messages)
            content = getattr(response, "content", response)
            if isinstance(content, list):
                res_text = "\n".join(
                    item.get("text", str(item)) if isinstance(item, dict) else str(item)
                    for item in content
                )
            else:
                res_text = str(content)
            hf_client.last_execution_time = time.time() - t0
            hf_client.last_raw_response = res_text
            hf_client.last_status = "llm_success"
            hf_client.last_error = None
            yield res_text
        except Exception as e2:
            hf_client.last_execution_time = time.time() - t0
            hf_client.last_status = "error_llm_call"
            hf_client.last_error = f"{type(e2).__name__}: {str(e2)}"
            hf_client.last_traceback = traceback.format_exc()
            yield f"\n\n❌ **Erreur d'inférence LLM Hugging Face :** {hf_client.last_error}"
