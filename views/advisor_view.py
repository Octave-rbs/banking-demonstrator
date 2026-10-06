"""
Vue Coach IA : Scorecard de santé financière, rapport exécutif agentique avec outils et cartes d'actions en 1 clic.
"""

from typing import List, Dict, Any
import streamlit as st
from services import BankBackend
from ai import BankingAIAdvisor
from views.dialogs import (
    open_savings_account_dialog,
    open_stock_investment_dialog,
    set_budget_ceiling_dialog
)


def render_action_cards(cards: List[Dict[str, Any]], db: BankBackend, me_id: str, key_prefix: str = "card"):
    """Affiche des cartes d'actions interactives en 1 clic (liens externes ou déclencheurs in-app)."""
    if not cards:
        return

    st.markdown("<h5 style='color:#1A432A; margin:16px 0 8px 0; font-size:0.95rem;'>🎯 Recommandations & Actions en 1 clic :</h5>", unsafe_allow_html=True)

    for idx, card in enumerate(cards):
        with st.container(border=True):
            col_icon, col_content, col_btn = st.columns([0.10, 0.60, 0.30])
            with col_icon:
                st.markdown(f"<div style='font-size:1.8rem; text-align:center;'>{card.get('icon', '💡')}</div>", unsafe_allow_html=True)
            with col_content:
                st.markdown(f"<div style='font-weight:700; color:#1A432A; font-size:0.9rem;'>{card.get('title', 'Action')}</div>", unsafe_allow_html=True)
                desc = card.get('description', '')
                if desc:
                    st.caption(desc)
            with col_btn:
                card_type = card.get('type', 'external_link')
                btn_label = card.get('button_label', 'Agir')
                if card_type == "external_link":
                    url = card.get('url', 'https://www.service-public.fr')
                    st.link_button(f"🔗 {btn_label}", url=url, type="primary", use_container_width=True)
                elif card_type == "in_app_dialog":
                    action_name = card.get('action_name', 'open_savings_dialog')
                    if st.button(f"✨ {btn_label}", key=f"{key_prefix}_{idx}", type="primary", use_container_width=True):
                        if action_name == "open_savings_dialog":
                            open_savings_account_dialog(db, me_id)
                        elif action_name == "open_stock_investment_dialog":
                            open_stock_investment_dialog(db, me_id)
                        elif action_name == "set_budget_alert":
                            payload = card.get('payload', {})
                            set_budget_ceiling_dialog(db, me_id, payload.get('category', 'Alimentation & Restauration'))
                        else:
                            open_savings_account_dialog(db, me_id)
                elif card_type == "in_app_navigation":
                    if st.button(f"👥 {btn_label}", key=f"{key_prefix}_{idx}", type="secondary", use_container_width=True):
                        st.info("💡 Rendez-vous dans l'onglet '👥 Partagé' du menu pour régulariser vos comptes !")



def render_advisor_view(db: BankBackend, ai: BankingAIAdvisor, me_id: str):
    st.markdown("<h3 style='text-align:center; color:#1A432A; margin-bottom:2px;'>Advisor IA</h3>", unsafe_allow_html=True)
    st.caption("Votre coach patrimonial et budgétaire agentique outillé.")

    profile = db.get_user_profile(me_id)
    budget = db.analyze_monthly_budget(me_id)
    cats, peers, subcats = db.get_category_breakdown(me_id)
    extra_ctx = db.get_llm_financial_context(me_id)

    family_val = getattr(profile, "family_situation", "Célibataire")
    job_val = getattr(profile, "job_activity", profile.status)
    housing_val = getattr(profile, "housing_type", "Colocation")
    country_val = getattr(profile, "country", "France")
    notes_val = getattr(profile, "custom_notes", "").strip()

    # Initialisation des variables de session si absentes
    if 'audit_action_cards' not in st.session_state:
        st.session_state.audit_action_cards = []
    if 'audit_steps' not in st.session_state:
        st.session_state.audit_steps = []

    # 1. Carte synthétique du profil utilisateur
    notes_badge_html = f"<div style='margin-top:6px; font-style:italic; background:white; padding:6px 10px; border-radius:8px; border-left:3px solid #2E8B57;'>🎯 <b>Objectif / Précisions :</b> {notes_val}</div>" if notes_val else ""

    st.markdown(f"""
        <div style="background:#E8F5E9; border-radius:14px; padding:12px 14px; margin-bottom:12px; font-size:0.8rem; color:#1A432A; border: 1px solid #C8E6C9;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <b>👤 {profile.name}, {profile.age} ans</b>
                <span style="background:#1A432A; color:white; padding:2px 8px; border-radius:10px; font-size:0.7rem;">{family_val}</span>
            </div>
            💼 <b>Activité :</b> {job_val} ({profile.school_or_company})<br>
            🏠 <b>Logement :</b> {housing_val} à {profile.city} ({country_val}) • Loyer : {profile.rent_amount:.0f} € • Revenu net : {profile.monthly_net_income:.0f} €<br>
            💰 <b>Épargne disponible :</b> {db.account_balance:.0f} €
            {notes_badge_html}
        </div>
    """, unsafe_allow_html=True)

    # 2. Formulaire interactif pour personnaliser le profil
    with st.expander("✏️ Personnaliser mon profil & contexte pour l'IA", expanded=False):
        st.caption("Ajustez vos paramètres réels et ajoutez des précisions libres qui seront transmises au LLM.")

        family_options = ["Célibataire", "En couple / Concubinage", "Pacsé(e)", "Marié(e)", "Parent solo / Avec enfant(s)"]
        fam_idx = family_options.index(family_val) if family_val in family_options else 0
        new_family = st.selectbox("Situation familiale :", family_options, index=fam_idx)

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            new_age = st.number_input("Âge :", min_value=16, max_value=99, value=int(profile.age), step=1)
            new_job = st.text_input("Emploi ou formation :", value=job_val)
            new_income = st.number_input("Rémunération nette (€) :", value=float(profile.monthly_net_income), step=50.0)
        with col_p2:
            housing_options = ["Colocation", "Locataire seul", "Hébergé à titre gratuit", "Propriétaire"]
            h_idx = housing_options.index(housing_val) if housing_val in housing_options else 0
            new_housing = st.selectbox("Type de logement :", housing_options, index=h_idx)
            new_city = st.text_input("Ville :", value=profile.city)
            new_country = st.text_input("Pays de résidence :", value=country_val, help="Adapte le référentiel des aides publiques.")

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            new_rent = st.number_input("Part de loyer (€) :", value=float(profile.rent_amount), step=50.0)
            new_balance = st.number_input("Solde / Épargne totale disponible (€) :", value=float(db.account_balance), step=250.0, help="Permet d'évaluer votre coussin d'urgence de 3 mois selon les Baby Steps.")
        with col_r2:
            new_company = st.text_input("Entreprise ou École :", value=profile.school_or_company)

        new_notes = st.text_area(
            "📝 Précisions libres & Objectifs (Champ libre transmis à l'agent IA) :",
            value=notes_val,
            placeholder="Ex : Je prépare un voyage au Japon dans 6 mois (budget 1500€). Je souhaite mettre au moins 100€ de côté par mois.",
            height=90
        )

        if st.button("💾 Enregistrer mon profil et actualiser l'IA", type="primary", use_container_width=True):
            profile.family_situation = new_family
            profile.age = new_age
            profile.job_activity = new_job
            profile.housing_type = new_housing
            profile.city = new_city
            profile.country = new_country.strip() or "France"
            profile.school_or_company = new_company
            profile.monthly_net_income = new_income
            profile.rent_amount = new_rent
            profile.custom_notes = new_notes
            db.account_balance = new_balance
            st.session_state.last_audit = None
            st.session_state.executive_audit_text = None
            st.session_state.audit_action_cards = []
            st.session_state.audit_steps = []
            st.session_state.is_streaming_audit = False
            st.toast("Profil et solde enregistrés !")
            st.rerun()


    # 3. Moteur IA & Statut d'inférence
    if ai.is_hf_configured():
        st.caption(f"⚡ Inférence Agentique : `{ai.default_model}` (Hugging Face API + 6 Outils d'Audit)")
    else:
        st.warning("⚠️ **Hugging Face API non connectée** : Renseignez votre token pour lancer le diagnostic IA en conditions réelles.")
        if getattr(ai, "init_error", None):
            st.error(f"🔍 **Détail technique :** {ai.init_error}")
        with st.expander("🔑 Configurer le token Hugging Face", expanded=True):
            quick_token = st.text_input("Votre token Hugging Face (`hf_...`) :", type="password", key="quick_hf_tok")
            if st.button("Connecter le LLM", key="btn_quick_tok"):
                ai.set_token(quick_token)
                st.rerun()

    # 4. Déclencheur de l'analyse agentique
    btn_label = "✨ Actualiser l'audit financier agentique" if st.session_state.executive_audit_text else "✨ Lancer l'analyse détaillée IA (Agent outillé)"
    if st.button(btn_label, type="primary", use_container_width=True):
        st.session_state.is_streaming_audit = True
        st.session_state.executive_audit_text = None
        st.session_state.audit_action_cards = []
        st.session_state.audit_steps = []

    # 5. Rendu ou Exécution de l'audit
    if st.session_state.is_streaming_audit:
        with st.spinner("Analyse approfondie de votre situation financière en cours..."):
            agent_gen = ai.stream_financial_audit(profile=profile, db=db, user_id=me_id)
            for event in agent_gen:
                ev_type = event.get("type")
                if ev_type == "done":
                    st.session_state.executive_audit_text = event.get("report", "")
                    st.session_state.audit_action_cards = event.get("actions", [])
                    st.session_state.is_streaming_audit = False
                elif ev_type == "error":
                    st.error(event.get("message", "Erreur lors de l'audit."))
                    st.session_state.is_streaming_audit = False
                    break
        st.rerun()

    elif st.session_state.executive_audit_text:

        exec_time = getattr(ai, "last_execution_time", 0.0)
        time_str = f" • En {exec_time:.1f}s" if exec_time > 0 else ""
        st.markdown(
            f"<div style='display:flex; justify-content:space-between; align-items:center; margin:16px 0 8px 0;'>"
            f"<h4 style='color:#1A432A; margin:0; font-size:1.05rem;'>📋 Rapport Exécutif de Synthèse</h4>"
            f"<span style='font-size:0.72rem; color:#666;'>IA Agent {ai.default_model}{time_str}</span></div>",
            unsafe_allow_html=True
        )

        with st.container(border=True):
            st.markdown(st.session_state.executive_audit_text)

        # Rendu des Cartes d'Actions en 1 clic
        if st.session_state.audit_action_cards:
            render_action_cards(st.session_state.audit_action_cards, db, me_id, key_prefix="audit_card")

    # 6. Chat conversationnel agentique avec l'IA
    st.markdown("<hr style='margin:18px 0; opacity:0.2;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:#1A432A; font-size:1rem; margin-bottom:6px;'>💬 Poser une question au coach</h4>", unsafe_allow_html=True)

    col_q1, col_q2 = st.columns(2)
    quick_q = None
    with col_q1:
        if st.button("🏛️ Éligibilité aides publiques ?", use_container_width=True):
            quick_q = "Quelles sont les aides publiques exactes auxquelles je peux avoir droit avec mon statut et mes revenus ?"
    with col_q2:
        if st.button("🎯 Réduire mes plus grosses dépenses ?", use_container_width=True):
            quick_q = "Quelles sont mes plus grosses dépenses du mois et comment puis-je économiser ?"

    user_query = st.text_input("Votre question :", value=quick_q or "", placeholder="Ex: Quel poste de dépense dépasse le plus par rapport aux autres ?")

    if st.button("Envoyer la question", use_container_width=True) and user_query.strip():
        with st.spinner("Votre conseiller IA investigue et vous répond..."):
            sub_list = ", ".join(extra_ctx.get('subscriptions', [])) or "Spotify, EDF"
            summary_ctx = (
                f"Dépensé 30j : {budget['rolling_spent']:.0f} € (Fixes : {budget['rolling_fixed']:.0f} €, Variables : {budget['rolling_variable']:.0f} €), "
                f"Reste à vivre : {budget['rolling_remaining']:.0f} €, Abonnements : {sub_list}"
            )
            reply, chat_actions, chat_steps = ai.ask_advisor_agentic(
                question=user_query,
                profile=profile,
                db=db,
                user_id=me_id,
                budget_summary=summary_ctx
            )
            st.session_state.chat_messages.append({"role": "user", "text": user_query})
            st.session_state.chat_messages.append({
                "role": "advisor",
                "text": reply,
                "actions": chat_actions,
                "steps": chat_steps
            })

    for m_idx, msg in enumerate(st.session_state.chat_messages[-6:]):
        if msg["role"] == "user":
            st.markdown(f"<div style='background:#E8F5E9; padding:8px 12px; border-radius:12px; margin-bottom:4px; margin-top:10px; font-size:0.8rem; font-weight:600; border-left:4px solid #2E8B57;'>🧑‍💻 {msg['text']}</div>", unsafe_allow_html=True)
        else:
            with st.container(border=True):
                st.markdown(f"🤖 {msg['text']}")
                if msg.get("actions"):
                    render_action_cards(msg["actions"], db, me_id, key_prefix=f"chat_msg_{m_idx}")

