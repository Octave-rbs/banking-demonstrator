"""
Vue Budget : Suivi du budget en cours, analyse 30 jours (du global au spécifique) et benchmark pairs.
"""

import streamlit as st
from services import BankBackend


def render_budget_view(db: BankBackend, me_id: str):
    st.markdown("<h3 style='text-align:center; color:#1A432A; margin-bottom:12px;'>Assistant Budget</h3>", unsafe_allow_html=True)

    budget = db.analyze_monthly_budget(me_id)
    cal_spent = budget['calendar_spent']
    baseline_income = budget['baseline_income']
    cal_remaining = budget['calendar_remaining']
    days_passed = budget['calendar_days_passed']
    total_days = budget['calendar_total_days']
    days_remaining = budget.get('calendar_days_remaining', max(1, total_days - days_passed))
    daily_allowance = budget.get('calendar_daily_allowance', max(0.0, cal_remaining / days_remaining))

    cal_ratio = (cal_spent / baseline_income) if baseline_income > 0 else 1.0
    bar_width = min(100.0, max(0.0, cal_ratio * 100))

    if cal_ratio <= 0.75:
        cal_color = "#2E8B57"
    elif cal_ratio <= 0.90:
        cal_color = "#55A630"
    elif cal_ratio <= 1.0:
        cal_color = "#E6A117"
    else:
        cal_color = "#D9534F"

    # 1. Barre de progression du mois civil en cours et dépense quotidienne restante
    st.markdown(f"""
        <div class="section-card" style="margin-bottom:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:0.88rem; font-weight:800; color:#1A432A;">📅 Mois en cours ({budget['calendar_label']})</span>
                <span style="font-size:0.75rem; color:#555; background:#F0F4F2; padding:3px 9px; border-radius:12px; font-weight:600;">Jour {days_passed} / {total_days} ({days_remaining}j restants)</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:6px;">
                <span style="font-size:0.8rem; color:#444;">Budget consommé : <b>{cal_spent:.2f} €</b> / {baseline_income:.0f} €</span>
                <span style="font-size:0.85rem; font-weight:800; color:{cal_color};">{cal_ratio*100:.0f} %</span>
            </div>
            <div style="background-color:#E9ECEF; border-radius:10px; height:14px; width:100%; overflow:hidden; margin-bottom:12px;">
                <div style="background-color:{cal_color}; height:100%; width:{bar_width}%; border-radius:10px; transition:width 0.4s ease;"></div>
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top:6px;">
                <div style="background:#F8FAF9; padding:10px; border-radius:12px; border:1px solid #E6EFEA; text-align:center;">
                    <div style="font-size:0.72rem; color:#666; font-weight:600; text-transform:uppercase;">Reste à vivre</div>
                    <div style="font-size:1.15rem; font-weight:800; color:#1A432A; margin-top:2px;">{cal_remaining:.2f} €</div>
                </div>
                <div style="background:#F8FAF9; padding:10px; border-radius:12px; border:1px solid #E6EFEA; text-align:center;">
                    <div style="font-size:0.72rem; color:#666; font-weight:600; text-transform:uppercase;">Dépense max / jour</div>
                    <div style="font-size:1.15rem; font-weight:800; color:{cal_color}; margin-top:2px;">{daily_allowance:.2f} €<span style="font-size:0.7rem; font-weight:600;">/j</span></div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 2. Vue d'ensemble sur le mois glissant (30 jours) : Du global au spécifique
    st.markdown(f"""
        <div style="text-align:center; font-size:0.8rem; color:#555; margin-bottom:10px;">
            <b>Période de référence (30 jours glissants) :</b> {budget['rolling_label']}
        </div>
    """, unsafe_allow_html=True)

    # 2.1 Score global de gestion (Sans note sur 100)
    health = db.calculate_health_score(me_id)
    p_tre = health["pillars"]["treasury"]
    p_str = health["pillars"]["structure"]
    p_pee = health["pillars"]["peers"]

    c_tre = "#1B5E20" if p_tre["status"] == "safe" else ("#D97706" if p_tre["status"] == "warning" else "#DC2626")
    c_str = "#1B5E20" if p_str["status"] == "safe" else ("#D97706" if p_str["status"] == "warning" else "#DC2626")
    c_pee = "#1B5E20" if p_pee["status"] == "safe" else ("#D97706" if p_pee["status"] == "warning" else "#DC2626")

    st.markdown(f"""
        <div class="scorecard-card" style="margin-bottom:14px;">
            <div class="scorecard-header" style="border-bottom:none; margin-bottom:4px; padding-bottom:0;">
                <div>
                    <div style="font-size:0.72rem; text-transform:uppercase; letter-spacing:0.8px; font-weight:700; color:#64748B;">Évaluation Globale</div>
                    <div style="font-size:1.05rem; font-weight:800; color:#1A432A; margin-top:2px;">Diagnostic de Gestion</div>
                </div>
                <div style="text-align:right;">
                    <span style="display:inline-block; font-size:0.82rem; font-weight:700; color:white; background:{health['color']}; padding:4px 10px; border-radius:14px; box-shadow:0 2px 6px rgba(0,0,0,0.08);">{health['badge']}</span>
                </div>
            </div>
            <div class="scorecard-summary" style="border-left:3px solid {health['color']}; margin-top:8px;">
                💡 {health['summary']}
            </div>
            <div style="font-size:0.76rem; font-weight:800; color:#1A432A; text-transform:uppercase; letter-spacing:0.5px; margin:14px 0 8px 0;">
                ⚡ Diagnostic rapide par pilier
            </div>
            <div class="pillar-row">
                <div class="pillar-header">
                    <span style="color:#334155;">💰 {p_tre['title']}</span>
                    <span style="color:{c_tre}; font-weight:700; font-size:0.72rem;">{p_tre['verdict']}</span>
                </div>
                <div class="pillar-bar-bg"><div style="background:{c_tre}; width:{p_tre['ratio']*100}%; height:100%; border-radius:6px;"></div></div>
            </div>
            <div class="pillar-row">
                <div class="pillar-header">
                    <span style="color:#334155;">⚖️ {p_str['title']}</span>
                    <span style="color:{c_str}; font-weight:700; font-size:0.72rem;">{p_str['verdict']}</span>
                </div>
                <div class="pillar-bar-bg"><div style="background:{c_str}; width:{p_str['ratio']*100}%; height:100%; border-radius:6px;"></div></div>
            </div>
            <div class="pillar-row" style="margin-bottom:0;">
                <div class="pillar-header">
                    <span style="color:#334155;">👥 {p_pee['title']}</span>
                    <span style="color:{c_pee}; font-weight:700; font-size:0.72rem;">{p_pee['verdict']}</span>
                </div>
                <div class="pillar-bar-bg"><div style="background:{c_pee}; width:{p_pee['ratio']*100}%; height:100%; border-radius:6px;"></div></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Répartition Charges fixes vs Variables sur 30 jours
    col_fx, col_vr = st.columns(2)
    with col_fx:
        st.markdown(f"""
            <div style="background:white; border-radius:14px; padding:12px; text-align:center; border:1px solid #EEF2F0; margin-bottom:12px; box-shadow:0 1px 4px rgba(0,0,0,0.02);">
                <div style="font-size:0.74rem; color:#888; text-transform:uppercase; font-weight:600;">Charges Fixes (30j)</div>
                <div style="font-size:1.15rem; font-weight:800; color:#1A432A; margin-top:2px;">{budget['rolling_fixed']:.2f} €</div>
                <div style="font-size:0.68rem; color:#666;">Loyer, EDF, Box, Abonnements</div>
            </div>
        """, unsafe_allow_html=True)
    with col_vr:
        st.markdown(f"""
            <div style="background:white; border-radius:14px; padding:12px; text-align:center; border:1px solid #EEF2F0; margin-bottom:12px; box-shadow:0 1px 4px rgba(0,0,0,0.02);">
                <div style="font-size:0.74rem; color:#888; text-transform:uppercase; font-weight:600;">Dépenses Variables (30j)</div>
                <div style="font-size:1.15rem; font-weight:800; color:#F39C12; margin-top:2px;">{budget['rolling_variable']:.2f} €</div>
                <div style="font-size:0.68rem; color:#666;">Courses, Sorties, Loisirs</div>
            </div>
        """, unsafe_allow_html=True)

    # 2.2 Benchmark contre les pairs (Détaillé par catégorie réelle)
    st.markdown("<h4 style='color:#1A432A; margin:16px 0 8px 0; font-size:1.02rem;'>👥 Comparateur Pairs (30 jours)</h4>", unsafe_allow_html=True)

    cats, peers, subcats = db.get_category_breakdown(me_id)

    if not cats:
        st.info("Aucune opération enregistrée pour la comparaison avec les pairs.")
        return

    for cat, spent_amt in cats.items():
        if cat in peers:
            p_info = peers[cat]
            avg = p_info['avg']
            rel_pos = p_info.get("status", p_info.get("relative_position", ""))
            delta = spent_amt - avg

            if delta > 0:
                delta_html = f"<span style='color:#DC2626; font-weight:700;'>+{delta:.0f} € de dépenses supplémentaires</span>"
            else:
                delta_html = f"<span style='color:#2E8B57; font-weight:700;'>Économie de {abs(delta):.0f} € vs moyenne</span>"

            st.markdown(f"""
                <div style="background:white; padding:12px 14px; border-radius:14px; margin-bottom:10px; border-left: 5px solid {p_info['color']}; box-shadow:0 1px 4px rgba(0,0,0,0.03);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; font-size:0.92rem; color:#222;">{cat}</span>
                        <span style="font-weight:800; font-size:0.98rem; color:#1A432A;">{spent_amt:.2f} €</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px; font-size:0.76rem;">
                        <span style="font-weight:700; color:{p_info['color']}; background:#F8FAF9; padding:2px 8px; border-radius:6px; border:1px solid #EEF2F0;">{rel_pos}</span>
                        <span style="color:#555;">Moyenne pairs : <b>{avg:.0f} €</b></span>
                    </div>
                    <div style="margin-top:6px; font-size:0.75rem; color:#666; border-top:1px dashed #EEF2F0; padding-top:6px;">
                        📊 Écart : {delta_html}
                    </div>
                </div>
            """, unsafe_allow_html=True)

            if cat in subcats and len(subcats[cat]) > 1:
                with st.expander(f"🔍 Détails des dépenses ({cat})", expanded=False):
                    for sub_name, sub_amt in subcats[cat].items():
                        st.write(f"• {sub_name} : **{sub_amt:.2f} €**")
