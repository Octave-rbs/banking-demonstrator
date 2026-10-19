"""
Module de configuration et gestion du client LLM (Groq via LangChain).

Le nom du module et de la classe (HFClient) est conservé pour ne pas casser
les imports existants ; le backend est désormais l'API gratuite de Groq.
"""

import os
from typing import Optional
import streamlit as st

try:
    from langchain_groq import ChatGroq
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


# Les modèles Llama ont été retirés par Groq le 16/08/2026 (remplaçant officiel : gpt-oss-120b)
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"


def _clean(val) -> str:
    return str(val).strip().strip('"').strip("'")


def get_secret_hf_key() -> Optional[str]:
    """
    Récupère la clé API Groq depuis st.secrets ou os.environ.
    Tolère les variantes de nommage courantes.
    """
    possible_keys = ["GROQ_API_KEY", "groq_api_key", "GROQ_KEY"]
    try:
        # 1. Clés directes dans st.secrets
        for k in possible_keys:
            if k in st.secrets and st.secrets[k]:
                return _clean(st.secrets[k])

        # 2. Sous-section [groq]
        if "groq" in st.secrets:
            sec = st.secrets["groq"]
            for subk in ["api_key", "token", "key", "GROQ_API_KEY"]:
                if subk in sec and sec[subk]:
                    return _clean(sec[subk])
    except Exception:
        pass

    # 3. Variables d'environnement
    val = os.environ.get("GROQ_API_KEY")
    if val:
        return _clean(val)

    return None


def get_model_name() -> str:
    """Modèle Groq, surchargeable via GROQ_MODEL (secrets ou environnement)."""
    try:
        if "GROQ_MODEL" in st.secrets and st.secrets["GROQ_MODEL"]:
            return _clean(st.secrets["GROQ_MODEL"])
    except Exception:
        pass
    return os.environ.get("GROQ_MODEL") or DEFAULT_GROQ_MODEL


class HFClient:
    """Gère l'initialisation du modèle LLM (Groq) et la session associée."""

    def __init__(self, token: Optional[str] = None):
        self.default_model: str = get_model_name()
        self.hf_token: Optional[str] = token or get_secret_hf_key()
        self.client: Optional[ChatGroq] = None
        self.init_error: Optional[str] = None
        self.last_status: str = "idle"
        self.last_error: Optional[str] = None
        self.last_traceback: Optional[str] = None
        self.last_raw_response: Optional[str] = None
        self.last_execution_time: float = 0.0

        self.init_llm()

    def set_token(self, token: Optional[str] = None):
        if token and token.strip():
            self.hf_token = token.strip()
        else:
            self.hf_token = get_secret_hf_key()
        self.init_llm()

    def init_llm(self):
        self.client = None
        self.init_error = None
        if not LANGCHAIN_AVAILABLE:
            self.init_error = "Bibliothèque 'langchain-groq' non installée (pip install langchain-groq)."
            return

        if self.hf_token:
            try:
                extra = {}
                if self.default_model.startswith("openai/gpt-oss"):
                    # Modèle à raisonnement : le raisonnement consomme aussi des tokens de sortie,
                    # on le limite et on laisse de la marge pour la réponse finale.
                    extra["reasoning_effort"] = "low"
                self.client = ChatGroq(
                    model=self.default_model,
                    api_key=self.hf_token,
                    max_tokens=2000,
                    temperature=0.25,
                    timeout=120,
                    max_retries=2,
                    **extra,
                )
            except Exception as e:
                self.init_error = f"{type(e).__name__}: {str(e)}"
                self.client = None

    def is_configured(self) -> bool:
        if not self.hf_token:
            detected = get_secret_hf_key()
            if detected:
                self.set_token(detected)
        return bool(self.client and self.hf_token)
