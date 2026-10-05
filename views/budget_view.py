"""
Vue Budget : Suivi budgétaire 30 jours, projection fin de mois et benchmark pairs.
"""

import streamlit as st
from services import BankBackend


def render_budget_view(db: BankBackend, me_id: str):
    st.markdown("<h3 style='text-align:center; color:#1A432A; margin-bottom:5px;'>Assistant Budget</h3>", unsafe_allow_html=True)

    budget = db.analyze_monthly_budget(me_id)
    extra_ctx = db.get_llm_financial_context(me_id)
    max_gap_cat = extra_ctx.get("max_gap_category", "")

    # 1. Indicateur du mois civil en cours
    st.markdown(f"""
        <div style="background:#F0F7F4; border-radius:14px; padding:12px 14px; margin-bottom:14px; border:1px solid #D2E7DE;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <span style="font-size:0.85rem; font-weight:700; color:#1A432A;">📅 Mois civil en cours ({budget['calendar_label']})</span>
                <span style="font-size:0.75rem; color:#666; background:white; padding:2px 8px; border-radius:10px; border:1px solid #E0E0E0;">Jour {budget['calendar_days_passed']} / {budget['calendar_total_days']}</span>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:0.82rem; margin-top:4px;">
                <span style="color:#444;">Dépensé ce mois-ci : <b>{budget['calendar_spent']:.2f} €</b></span>
                <span style="color:#1A432A; font-weight:700;">Reste fin de mois : {budget['calendar_remaining']:.2f} €</span>
            </div>
            <div style="font-size:0.73rem; color:#777; margin-top:5px; text-align:right;">
                Projection fin de mois : <b>{budget['calendar_projection']:.0f} €</b> (sur base de votre revenu de {budget['baseline_income']:.0f} €)
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 2. Suivi du budget sur le mois glissant (30 jours)
    st.markdown(f"""
        <div style="text-align:center; font-size:0.8rem; color:#555; margin-bottom:8px;">
            <b>Période de référence :</b> {budget['rolling_label']}
        </div>
    """, unsafe_allow_html=True)

    rolling_income = budget['rolling_income']
    rolling_spent = budget['rolling_spent']
    rolling_remaining = budget['rolling_remaining']
    ratio = min(1.0, rolling_spent / rolling_income) if rolling_income > 0 else 1.0

    bar_color = "#28A745" if ratio < 0.85 else "#F39C12" if ratio <= 1.0 else "#E04B59"

    st.markdown(f"""
        <div class="section-card">
            <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                <span style="font-size:0.85rem; font-weight:700; color:#333;">Consommé (30j) : {rolling_spent:.2f} €</span>
                <span style="font-size:0.85rem; font-weight:600; color:#888;">Revenus perçus : {rolling_income:.2f} €</span>
            </div>
            <div style="background-color:#E9ECEF; border-radius:10px; height:14px; width:100%;">
                <div style="background-color:{bar_color}; height:14px; border-radius:10px; width:{ratio*100}%;"></div>
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:8px; font-size:0.78rem;">
                <span style="font-weight:700; color:{bar_color};">
                    {"⚠️ Dépassement budgétaire" if budget['is_over_budget'] else f"Reste à vivre (30j) : {rolling_remaining:.2f} €"}
                </span>
                <span style="color:#777;">Taux : <b>{(rolling_spent/rolling_income*100):.1f} %</b></span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Répartition Charges fixes vs Variables
    col_fx, col_vr = st.columns(2)
    with col_fx:
        st.markdown(f"""
            <div style="background:white; border-radius:14px; padding:12px; text-align:center; border:1px solid #EEF2F0;">
                <div style="font-size:0.75rem; color:#888; text-transform:uppercase;">Charges Fixes (30j)</div>
                <div style="font-size:1.2rem; font-weight:800; color:#1A432A;">{budget['rolling_fixed']:.2f} €</div>
                <div style="font-size:0.7rem; color:#555;">Loyer, EDF, Box, Abos</div>
            </div>
        """, unsafe_allow_html=True)
    with col_vr:
        st.markdown(f"""
            <div style="background:white; border-radius:14px; padding:12px; text-align:center; border:1px solid #EEF2F0;">
                <div style="font-size:0.75rem; color:#888; text-transform:uppercase;">Dépenses Variables (30j)</div>
                <div style="font-size:1.2rem; font-weight:800; color:#F39C12;">{budget['rolling_variable']:.2f} €</div>
                <div style="font-size:0.7rem; color:#555;">Courses, Restos, Shopping</div>
            </div>
        """, unsafe_allow_html=True)

    # 3. Comparateur avec les pairs
    st.markdown("<h4 style='color:#1A432A; margin:22px 0 6px 0; font-size:1.05rem;'>Comparateur Pairs (Étudiants / Alternants Paris)</h4>", unsafe_allow_html=True)

    cats, peers, subcats = db.get_category_breakdown(me_id)

    if not cats:
        st.info("Données insuffisantes pour la comparaison.")
        return

    for cat, spent_amt in cats.items():
        if cat in peers:
            p_info = peers[cat]
            avg = p_info['avg']
            rel_pos = p_info.get("relative_position", p_info['status'])

            delta = spent_amt - avg
            delta_str = f"+{delta:.0f} €" if delta > 0 else f"{delta:.0f} €"
            is_critical = (cat == max_gap_cat)

            badge_critical = "<span style='background:#E04B59; color:white; font-size:0.68rem; font-weight:700; padding:2px 6px; border-radius:6px; margin-left:6px;'>Poste le plus élevé</span>" if is_critical else ""

            st.markdown(f"""
                <div style="background:white; padding:14px; border-radius:14px; margin-bottom:10px; border-left: 5px solid {p_info['color']}; box-shadow:0 1px 4px rgba(0,0,0,0.03);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; font-size:0.95rem; color:#222;">{cat} {badge_critical}</span>
                        <span style="font-weight:800; font-size:1rem;">{spent_amt:.2f} €</span>
                    </div>
                    <div style="margin-top:6px; background:#F8FAF9; padding:8px 10px; border-radius:8px; border-left:3px solid {p_info['color']};">
                        <span style="font-weight:700; color:{p_info['color']}; font-size:0.82rem;">{rel_pos}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px; font-size:0.75rem;">
                        <span style="color:#555;">Moyenne pairs : <b>{avg:.0f} €</b> ({delta_str})</span>
                        <span style="color:#777;">{p_info['comment']}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            if is_critical and cat in subcats and len(subcats[cat]) > 1:
                with st.expander(f"🔍 Détails exclusifs des dépenses ({cat})", expanded=True):
                    st.caption("Poste ciblé prioritairement pour résorber l'écart avec les pairs :")
                    for sub_name, sub_amt in subcats[cat].items():
                        st.write(f"• {sub_name} : **{sub_amt:.2f} €**")
