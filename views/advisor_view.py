"""
Vue Coach IA : Scorecard de santé financière, rapport exécutif en streaming et chat.
"""

import streamlit as st
from services import BankBackend
from ai import BankingAIAdvisor


def render_advisor_view(db: BankBackend, ai: BankingAIAdvisor, me_id: str):
    st.markdown("<h3 style='text-align:center; color:#1A432A; margin-bottom:2px;'>Advisor IA</h3>", unsafe_allow_html=True)
    st.caption("Votre coach patrimonial et budgétaire propulsé par l'IA.")

    profile = db.get_user_profile(me_id)
    budget = db.analyze_monthly_budget(me_id)
    cats, peers, subcats = db.get_category_breakdown(me_id)
    extra_ctx = db.get_llm_financial_context(me_id)

    family_val = getattr(profile, "family_situation", "Célibataire")
    job_val = getattr(profile, "job_activity", profile.status)
    housing_val = getattr(profile, "housing_type", "Colocation")
    country_val = getattr(profile, "country", "France")
    notes_val = getattr(profile, "custom_notes", "").strip()

    # 1. Carte synthétique du profil utilisateur
    notes_badge_html = f"<div style='margin-top:6px; font-style:italic; background:white; padding:6px 10px; border-radius:8px; border-left:3px solid #2E8B57;'>🎯 <b>Objectif / Précisions :</b> {notes_val}</div>" if notes_val else ""

    st.markdown(f"""
        <div style="background:#E8F5E9; border-radius:14px; padding:12px 14px; margin-bottom:12px; font-size:0.8rem; color:#1A432A; border: 1px solid #C8E6C9;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <b>👤 {profile.name}, {profile.age} ans</b>
                <span style="background:#1A432A; color:white; padding:2px 8px; border-radius:10px; font-size:0.7rem;">{family_val}</span>
            </div>
            💼 <b>Activité :</b> {job_val} ({profile.school_or_company})<br>
            🏠 <b>Logement :</b> {housing_val} à {profile.city} ({country_val}) • Loyer : {profile.rent_amount:.0f} € • Revenu net : {profile.monthly_net_income:.0f} €
            {notes_badge_html}
        </div>
    """, unsafe_allow_html=True)

    # 2. Formulaire interactif pour personnaliser le profil
    with st.expander("✏️ Personnaliser mon profil & contexte pour l'IA", expanded=False):
        st.caption("Ajustez vos paramètres réels et ajoutez des précisions libres qui seront directement intégrées dans le prompt du LLM.")

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
            new_country = st.text_input("Pays de résidence :", value=country_val, help="Adapte le référentiel des aides publiques (France, Espagne, Allemagne, Pologne...).")

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            new_rent = st.number_input("Part de loyer (€) :", value=float(profile.rent_amount), step=50.0)
        with col_r2:
            new_company = st.text_input("Entreprise ou École :", value=profile.school_or_company)

        new_notes = st.text_area(
            "📝 Précisions libres & Objectifs (Champ libre transmis au LLM) :",
            value=notes_val,
            placeholder="Ex : Je prépare un voyage au Japon dans 6 mois (budget 1500€). J'ai un crédit étudiant de 60€/mois et je souhaite mettre au moins 100€ de côté par mois. Comment optimiser mes dépenses ?",
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
            st.session_state.last_audit = None
            st.session_state.executive_audit_text = None
            st.session_state.is_streaming_audit = False
            st.toast("Profil et contexte IA enregistrés avec succès !")
            st.rerun()

    # 3. Scorecard de Santé Budgétaire Instantanée (< 5ms)
    health = db.calculate_health_score(me_id)
    p_tre = health["pillars"]["treasury"]
    p_str = health["pillars"]["structure"]
    p_pee = health["pillars"]["peers"]

    c_tre = "#2E8B57" if p_tre["status"] == "safe" else ("#D97706" if p_tre["status"] == "warning" else "#DC2626")
    c_str = "#2E8B57" if p_str["status"] == "safe" else ("#D97706" if p_str["status"] == "warning" else "#DC2626")
    c_pee = "#2E8B57" if p_pee["status"] == "safe" else ("#D97706" if p_pee["status"] == "warning" else "#DC2626")

    scorecard_html = (
        f'<div class="scorecard-card">'
        f'<div class="scorecard-header">'
        f'<div><div style="font-size:0.72rem; text-transform:uppercase; letter-spacing:0.8px; font-weight:700; color:#64748B;">Score Budgétaire</div>'
        f'<div style="font-size:1.05rem; font-weight:800; color:#1A432A;">Diagnostic Instantané</div></div>'
        f'<div style="text-align:right;"><span style="font-size:2.1rem; font-weight:900; color:{health["color"]};">{health["total_score"]}</span>'
        f'<span style="font-size:0.95rem; font-weight:700; color:#94A3B8;">/100</span>'
        f'<div style="font-size:0.72rem; font-weight:700; color:{health["color"]};">{health["badge"]}</div></div>'
        f'</div>'
        f'<div class="scorecard-summary" style="border-left:3px solid {health["color"]};">💡 {health["summary"]}</div>'
        f'<div class="pillar-row">'
        f'<div class="pillar-header"><span style="color:#334155;">💰 {p_tre["title"]}</span><span style="color:#64748B;">{p_tre["score"]} / {p_tre["max_score"]} pts</span></div>'
        f'<div class="pillar-bar-bg"><div style="background:{c_tre}; width:{p_tre["ratio"]*100}%; height:100%; border-radius:6px;"></div></div>'
        f'<div class="pillar-verdict">{p_tre["verdict"]}</div>'
        f'</div>'
        f'<div class="pillar-row">'
        f'<div class="pillar-header"><span style="color:#334155;">⚖️ {p_str["title"]}</span><span style="color:#64748B;">{p_str["score"]} / {p_str["max_score"]} pts</span></div>'
        f'<div class="pillar-bar-bg"><div style="background:{c_str}; width:{p_str["ratio"]*100}%; height:100%; border-radius:6px;"></div></div>'
        f'<div class="pillar-verdict">{p_str["verdict"]}</div>'
        f'</div>'
        f'<div class="pillar-row" style="margin-bottom:0;">'
        f'<div class="pillar-header"><span style="color:#334155;">👥 {p_pee["title"]}</span><span style="color:#64748B;">{p_pee["score"]} / {p_pee["max_score"]} pts</span></div>'
        f'<div class="pillar-bar-bg"><div style="background:{c_pee}; width:{p_pee["ratio"]*100}%; height:100%; border-radius:6px;"></div></div>'
        f'<div class="pillar-verdict">{p_pee["verdict"]}</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(scorecard_html, unsafe_allow_html=True)

    if ai.is_hf_configured():
        st.caption(f"⚡ Inférence IA connectée : `{ai.default_model}` (Hugging Face API)")
    else:
        st.warning("⚠️ **Hugging Face API non connectée** : Renseignez votre token pour lancer le diagnostic IA approfondi en conditions réelles.")
        if getattr(ai, "init_error", None):
            st.error(f"🔍 **Détail technique :** {ai.init_error}")
        with st.expander("🔑 Configurer le token Hugging Face", expanded=True):
            quick_token = st.text_input("Votre token Hugging Face (`hf_...`) :", type="password", key="quick_hf_tok")
            if st.button("Connecter le LLM", key="btn_quick_tok"):
                ai.set_token(quick_token)
                st.rerun()

    # 4. Déclencheur de l'analyse IA
    btn_label = "✨ Actualiser le rapport exécutif IA" if st.session_state.executive_audit_text else "✨ Lancer l'analyse détaillée IA (Streaming)"
    if st.button(btn_label, type="primary", use_container_width=True):
        st.session_state.is_streaming_audit = True
        st.session_state.executive_audit_text = None

    # 5. Rendu en Streaming ou Affichage persistant
    if st.session_state.is_streaming_audit:
        st.markdown("<h4 style='color:#1A432A; margin:16px 0 8px 0; font-size:1.05rem;'>📋 Rapport Exécutif de Synthèse</h4>", unsafe_allow_html=True)
        with st.container(border=True):
            stream_gen = ai.stream_financial_audit(
                profile=profile,
                budget_data=budget,
                categories=cats,
                subcategories=subcats,
                peers_benchmark=peers,
                extra_context=extra_ctx
            )
            streamed_text = st.write_stream(stream_gen)
            st.session_state.executive_audit_text = streamed_text
            st.session_state.last_audit = {"raw_text": streamed_text, "status": "success"}
            st.session_state.is_streaming_audit = False
            exec_time = getattr(ai, "last_execution_time", 0.0)
            if exec_time > 0:
                st.caption(f"⚡ Inférence terminée en **{exec_time:.1f}s** via `{ai.default_model}`")

    elif st.session_state.executive_audit_text:
        exec_time = getattr(ai, "last_execution_time", 0.0)
        time_str = f" • En {exec_time:.1f}s" if exec_time > 0 else ""
        st.markdown(f"<div style='display:flex; justify-content:space-between; align-items:center; margin:16px 0 8px 0;'><h4 style='color:#1A432A; margin:0; font-size:1.05rem;'>📋 Rapport Exécutif de Synthèse</h4><span style='font-size:0.72rem; color:#666;'>IA {ai.default_model}{time_str}</span></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(st.session_state.executive_audit_text)

    # 6. Chat conversationnel avec l'IA
    st.markdown("<hr style='margin:18px 0; opacity:0.2;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:#1A432A; font-size:1rem; margin-bottom:6px;'>💬 Poser une question au coach</h4>", unsafe_allow_html=True)

    col_q1, col_q2 = st.columns(2)
    quick_q = None
    with col_q1:
        if st.button("🏛️ Prime d'activité ?", use_container_width=True):
            quick_q = "Comment puis-je demander la Prime d'Activité avec mon statut et ma rémunération ?"
    with col_q2:
        if st.button("🎯 Mon projet / épargne ?", use_container_width=True):
            quick_q = "Comment puis-je financer mon projet avec mon budget actuel ?"

    user_query = st.text_input("Votre question :", value=quick_q or "", placeholder="Ex: Comment optimiser mes abonnements ?")

    if st.button("Envoyer la question", use_container_width=True) and user_query.strip():
        with st.spinner("Votre conseiller IA vous répond..."):
            sub_list = ", ".join(extra_ctx.get('subscriptions', [])) or "Spotify, EDF"
            incomes_str = ", ".join(extra_ctx.get('detected_incomes', [])) or f"Revenu déclaré: {profile.monthly_net_income:.0f}€"
            summary_ctx = (
                f"Entrées détectées: {incomes_str}, Dépensé (30j): {budget['rolling_spent']:.0f}€ "
                f"(Fixes: {budget['rolling_fixed']:.0f}€, Variables: {budget['rolling_variable']:.0f}€), "
                f"Reste fin de mois civil: {budget['calendar_remaining']:.0f}€, Dépensé mois civil: {budget['calendar_spent']:.0f}€, "
                f"Abonnements: {sub_list}, Poste le plus élevé: {extra_ctx.get('max_gap_category', 'N/A')}, "
                f"Part de loyer débitée: {profile.rent_amount:.0f}€"
            )
            reply = ai.ask_advisor(user_query, profile, summary_ctx)
            st.session_state.chat_messages.append({"role": "user", "text": user_query})
            st.session_state.chat_messages.append({"role": "advisor", "text": reply})

    for msg in st.session_state.chat_messages[-6:]:
        if msg["role"] == "user":
            st.markdown(f"<div style='background:#E8F5E9; padding:8px 12px; border-radius:12px; margin-bottom:4px; margin-top:10px; font-size:0.8rem; font-weight:600; border-left:4px solid #2E8B57;'>🧑‍💻 {msg['text']}</div>", unsafe_allow_html=True)
        else:
            with st.container(border=True):
                st.markdown(f"🤖 {msg['text']}")
