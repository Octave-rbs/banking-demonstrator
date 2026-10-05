"""
Vue Admin : Configuration du token Hugging Face, gestion des données et profil démo.
"""

import os
import pandas as pd
import streamlit as st
from services import BankBackend
from ai import BankingAIAdvisor


def render_admin_view(db: BankBackend, ai: BankingAIAdvisor, me_id: str):
    st.markdown("<h4 style='color:#1A432A;'>Paramètres du démonstrateur</h4>", unsafe_allow_html=True)

    # 1. Configuration de l'IA (Token Hugging Face)
    with st.expander("🔑 Configuration Clé Hugging Face (Optionnel)", expanded=False):
        st.caption("Entrez un token Hugging Face gratuit (`hf_...`) pour exécuter les requêtes via l'Inference API.")
        current_token = ai.hf_token or ""
        token_input = st.text_input("Hugging Face API Token :", value=current_token, type="password")
        if st.button("Enregistrer le token", use_container_width=True):
            ai.set_token(token_input)
            st.success("Token enregistré !")
            st.rerun()

    # 2. Gestion des données locales
    with st.expander("📂 Fichiers de données locales (/data)", expanded=True):
        st.write(f"Transactions en mémoire : **{len(db.transactions)}**")
        st.write(f"Fichiers chargés automatiquement : {', '.join(st.session_state.loaded_files) if st.session_state.loaded_files else 'Aucun'}")

        if st.button("🔄 Réinitialiser et recharger les CSV de démo", use_container_width=True):
            st.session_state.db = BankBackend()
            st.session_state.loaded_files = set()
            st.session_state.chat_messages = []
            st.session_state.last_audit = None
            st.session_state.executive_audit_text = None
            st.toast("Données réinitialisées avec succès !")
            st.rerun()

    # 3. Profil utilisateur modifiable
    with st.expander("👤 Modifier le profil utilisateur pour la démo", expanded=False):
        prof = db.get_user_profile(me_id)
        admin_fam = st.selectbox("Situation familiale :", ["Célibataire", "En couple / Concubinage", "Pacsé(e)", "Marié(e)", "Parent solo / Avec enfant(s)"], key="adm_fam", index=0)
        admin_job = st.text_input("Activité / Emploi :", value=getattr(prof, "job_activity", prof.status), key="adm_job")
        admin_income = st.number_input("Rémunération mensuelle nette (€) :", value=float(prof.monthly_net_income), step=50.0, key="adm_inc")
        admin_rent = st.number_input("Montant de la part de loyer (€) :", value=float(prof.rent_amount), step=50.0, key="adm_rent")
        admin_country = st.text_input("Pays de résidence :", value=getattr(prof, "country", "France"), key="adm_country")
        admin_notes = st.text_area("Notes libres / Objectifs du profil :", value=getattr(prof, "custom_notes", ""), key="adm_notes")

        if st.button("Mettre à jour le profil", use_container_width=True, key="adm_save"):
            prof.family_situation = admin_fam
            prof.job_activity = admin_job
            prof.monthly_net_income = admin_income
            prof.rent_amount = admin_rent
            prof.country = admin_country.strip() or "France"
            prof.custom_notes = admin_notes
            st.session_state.last_audit = None
            st.session_state.executive_audit_text = None
            st.success("Profil mis à jour !")
            st.rerun()

    # 4. Données de benchmark des pairs
    with st.expander("📊 Données de benchmark des pairs (Fichier externe)", expanded=False):
        st.caption("Les seuils statistiques (Top 10%, Top 30%, Moyenne) proviennent du fichier externe `data/benchmark_peers.json`.")

        bench_file_found = "data/benchmark_peers.json" if os.path.exists("data/benchmark_peers.json") else "Données internes"
        st.info(f"Fichier source actif : `{bench_file_found}`")

        if st.button("🔄 Recharger les seuils depuis le fichier", use_container_width=True, key="btn_reload_bench"):
            db.peers_benchmark_data = db.load_peers_benchmark()
            st.session_state.last_audit = None
            st.toast("Seuils de benchmark rechargés avec succès !")
            st.rerun()

        bench_rows = []
        for cat_k, b_v in db.peers_benchmark_data.items():
            bench_rows.append({
                "Catégorie": cat_k,
                "Top 10% éco": f"<{b_v.get('top_10_economes', 0):.0f} €",
                "Top 30% éco": f"<{b_v.get('top_30_economes', 0):.0f} €",
                "Moyenne": f"{b_v.get('moyenne', 0):.0f} €",
                "Top 30% dép.": f">{b_v.get('top_30_depensiers', 0):.0f} €",
                "Top 10% dép.": f">{b_v.get('top_10_depensiers', 0):.0f} €",
            })
        st.dataframe(pd.DataFrame(bench_rows), use_container_width=True, hide_index=True)
