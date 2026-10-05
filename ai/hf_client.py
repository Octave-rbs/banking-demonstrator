"""
Module de configuration et gestion du client Hugging Face / LangChain.
"""

import os
from typing import Optional
import streamlit as st

try:
    from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


def get_secret_hf_key() -> Optional[str]:
    """
    Récupère le token Hugging Face depuis st.secrets ou os.environ.
    Tolère les variantes de nommage courantes.
    """
    possible_keys = [
        "HUGGING_FACE_API_KEY",
        "HF_TOKEN",
        "HUGGINGFACEHUB_API_TOKEN",
        "HUGGINGFACE_API_KEY",
        "HF_API_KEY",
        "hugging_face_api_key",
        "hf_token",
        "huggingface_api_key",
    ]
    try:
        # 1. Clés directes dans st.secrets
        for k in possible_keys:
            if k in st.secrets:
                val = st.secrets[k]
                if val:
                    return str(val).strip().strip('"').strip("'")

        # 2. Sous-sections
        for section in ["huggingface", "hf", "hugging_face"]:
            if section in st.secrets:
                sec = st.secrets[section]
                if isinstance(sec, dict):
                    for subk in ["api_key", "token", "key", "HUGGING_FACE_API_KEY"]:
                        if subk in sec and sec[subk]:
                            return str(sec[subk]).strip().strip('"').strip("'")

        # 3. Recherche dynamique
        for k in st.secrets.keys():
            k_lower = k.lower()
            if "hugging" in k_lower or "hf_" in k_lower:
                val = st.secrets[k]
                if isinstance(val, str) and val.strip():
                    return val.strip().strip('"').strip("'")
    except Exception:
        pass

    # 4. Variables d'environnement
    for env_k in ["HUGGING_FACE_API_KEY", "HF_TOKEN", "HUGGINGFACEHUB_API_TOKEN"]:
        val = os.environ.get(env_k)
        if val:
            return val.strip().strip('"').strip("'")

    return None


class HFClient:
    """Gère l'initialisation du modèle LLM et la session Hugging Face."""

    def __init__(self, token: Optional[str] = None):
        self.default_model: str = "meta-llama/Llama-3.1-8B-Instruct"
        self.hf_token: Optional[str] = (
            token
            or get_secret_hf_key()
            or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
            or os.environ.get("HF_TOKEN")
        )
        self.client: Optional[ChatHuggingFace] = None
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
            self.hf_token = get_secret_hf_key() or os.environ.get("HF_TOKEN")
        self.init_llm()

    def init_llm(self):
        self.client = None
        self.init_error = None
        if not LANGCHAIN_AVAILABLE:
            self.init_error = "Bibliothèque 'langchain-huggingface' non installée."
            return

        if self.hf_token:
            try:
                os.environ["HF_TOKEN"] = self.hf_token
                os.environ["HUGGINGFACEHUB_API_TOKEN"] = self.hf_token

                llm_backend = HuggingFaceEndpoint(
                    repo_id=self.default_model,
                    task="text-generation",
                    huggingfacehub_api_token=self.hf_token,
                    max_new_tokens=950,
                    temperature=0.25,
                    timeout=120,
                    streaming=True
                )
                self.client = ChatHuggingFace(llm=llm_backend)
            except Exception as e:
                self.init_error = f"{type(e).__name__}: {str(e)}"
                self.client = None

    def is_configured(self) -> bool:
        if not self.hf_token:
            detected = get_secret_hf_key()
            if detected:
                self.set_token(detected)
        return bool(self.client and self.hf_token)
