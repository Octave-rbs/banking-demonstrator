"""
Modales interactives Streamlit pour les dépenses partagées.
"""

import streamlit as st
from services import BankBackend


@st.dialog("Partager une dépense existante")
def share_existing_tx_dialog(db: BankBackend, tx_id: str):
    tx = next((t for t in db.transactions if t.id == tx_id), None)
    if not tx:
        st.error("Opération introuvable.")
        return

    st.markdown(f"<h3 style='text-align:center; color:#1A432A; margin-bottom:2px;'>{tx.merchant}</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; font-size:1.6rem; font-weight:800; margin-top:0;'>{tx.amount:.2f} €</p>", unsafe_allow_html=True)

    group_options = {gid: g.name for gid, g in db.groups.items()}
    curr_idx = list(group_options.keys()).index(db.active_group_id) if db.active_group_id in group_options else 0
    selected_gid = st.selectbox(
        "Sélectionner le groupe :",
        options=list(group_options.keys()),
        format_func=lambda x: group_options[x],
        index=curr_idx
    )

    target_group = db.groups[selected_gid]
    member_users = {uid: db.users[uid] for uid in target_group.members if uid in db.users}

    mode = st.radio("Mode de répartition", ["Équitable (parts égales)", "Personnalisé (montants exacts)"], horizontal=True)
    split_details = {}

    if mode == "Équitable (parts égales)":
        selected_members = st.multiselect(
            "Participants à cette dépense :",
            options=list(member_users.keys()),
            default=list(member_users.keys()),
            format_func=lambda uid: member_users[uid].name
        )
        if selected_members:
            share_val = round(tx.amount / len(selected_members), 2)
            st.info(f"💡 Chaque participant paiera **{share_val:.2f} €** ({len(selected_members)} personnes).")
            split_details = {uid: share_val for uid in selected_members}
        else:
            st.warning("Veuillez sélectionner au moins un participant.")
    else:
        st.write("Saisissez la part exacte de chacun :")
        allocated = 0.0
        for uid, u in member_users.items():
            amt = st.number_input(f"Part de {u.name} (€)", min_value=0.0, max_value=float(tx.amount), step=1.0, key=f"split_edit_{uid}")
            if amt > 0:
                split_details[uid] = amt
            allocated += amt
        diff = round(tx.amount - allocated, 2)
        if abs(diff) > 0.01:
            st.warning(f"Reste à répartir : **{diff:.2f} €**")
        else:
            st.success("✅ La somme correspond exactement au total !")

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("Valider le partage", type="primary", use_container_width=True):
            if not split_details:
                st.error("Répartition invalide.")
            else:
                db.share_transaction(tx.id, split_details, selected_gid)
                st.toast("Dépense ajoutée au compte partagé !")
                st.rerun()
    with col_cancel:
        if tx.shared_account_id:
            if st.button("Retirer du groupe", use_container_width=True):
                db.unshare_transaction(tx.id)
                st.rerun()


@st.dialog("Ajouter une dépense au groupe")
def add_new_group_expense_dialog(db: BankBackend, group_id: str, me_id: str):
    group = db.groups.get(group_id)
    if not group:
        st.error("Groupe introuvable.")
        return

    st.markdown(f"<h3 style='text-align:center; color:#1A432A;'>{group.icon} {group.name}</h3>", unsafe_allow_html=True)

    merchant = st.text_input("Titre de la dépense (ex: Courses Lidl, Billets train)", placeholder="Ex: Courses colocation")
    amount = st.number_input("Montant total (€)", min_value=0.01, step=1.0, value=25.0)

    member_users = {uid: db.users[uid] for uid in group.members if uid in db.users}
    payer_id = st.selectbox(
        "Payé par :",
        options=list(member_users.keys()),
        index=list(member_users.keys()).index(me_id) if me_id in member_users else 0,
        format_func=lambda uid: f"{member_users[uid].avatar} {member_users[uid].name} (Moi)" if uid == me_id else f"{member_users[uid].avatar} {member_users[uid].name}"
    )

    mode = st.radio("Type de répartition :", ["Parts égales entre tous", "Sélection de membres", "Montants personnalisés"])
    split_details = {}

    if mode == "Parts égales entre tous":
        share_val = round(amount / len(group.members), 2)
        st.info(f"💡 Part par personne : **{share_val:.2f} €** ({len(group.members)} membres)")
        split_details = {uid: share_val for uid in group.members}
    elif mode == "Sélection de membres":
        selected = st.multiselect(
            "Qui participe ?",
            options=list(member_users.keys()),
            default=list(member_users.keys()),
            format_func=lambda uid: member_users[uid].name
        )
        if selected:
            share_val = round(amount / len(selected), 2)
            st.info(f"💡 Part par personne : **{share_val:.2f} €** ({len(selected)} sélectionnés)")
            split_details = {uid: share_val for uid in selected}
    else:
        allocated = 0.0
        for uid, u in member_users.items():
            amt = st.number_input(f"Part de {u.name} (€)", min_value=0.0, max_value=float(amount), step=1.0, key=f"new_split_{uid}")
            if amt > 0:
                split_details[uid] = amt
            allocated += amt
        diff = round(amount - allocated, 2)
        if abs(diff) > 0.01:
            st.warning(f"Reste à répartir : **{diff:.2f} €**")
        else:
            st.success("✅ Total parfaitement équilibré !")

    if st.button("Enregistrer la dépense", type="primary", use_container_width=True):
        if not merchant.strip():
            st.error("Veuillez indiquer un titre.")
        elif not split_details:
            st.error("Veuillez définir au moins un participant.")
        else:
            db.add_direct_expense(
                merchant=merchant,
                amount=amount,
                payer_id=payer_id,
                split_details=split_details,
                group_id=group_id
            )
            st.toast(f"Dépense ajoutée avec succès à {group_id} !")
            st.rerun()


@st.dialog("Créer un nouveau compte partagé")
def create_group_dialog(db: BankBackend, me_id: str):
    st.markdown("<h3 style='text-align:center; color:#1A432A;'>Nouveau Groupe</h3>", unsafe_allow_html=True)
    g_name = st.text_input("Nom du groupe", placeholder="Ex: Voyage Barcelone, Weekend Ski")
    g_icon = st.selectbox("Icône", ["🏘️", "✈️", "🏖️", "🍕", "🎉", "🚗", "🎓"])
    g_desc = st.text_input("Description", placeholder="Ex: Dépenses partagées du séjour")

    available_contacts = [u for uid, u in db.users.items() if uid != me_id]
    contact_map = {u.id: u.name for u in available_contacts}
    selected_uids = st.multiselect(
        "Membres invités :",
        options=list(contact_map.keys()),
        default=list(contact_map.keys())[:2],
        format_func=lambda uid: contact_map[uid]
    )

    if st.button("Créer le groupe", type="primary", use_container_width=True):
        if not g_name.strip():
            st.error("Veuillez saisir un nom.")
        else:
            new_g = db.create_group(name=g_name, member_ids=selected_uids, description=g_desc, icon=g_icon)
            st.toast(f"Groupe {new_g.name} créé avec succès !")
            st.rerun()


@st.dialog("Simulateur & Ouverture : Livret d'Épargne Populaire (LEP)")
def open_savings_account_dialog(db: BankBackend, me_id: str):
    """Modale interactive pour simuler et ouvrir un LEP avec calcul d'intérêts en direct."""
    profile = db.get_user_profile(me_id)
    st.markdown("<h3 style='text-align:center; color:#1A432A; margin-bottom:2px;'>📈 Livret d'Épargne Populaire (LEP)</h3>", unsafe_allow_html=True)
    st.caption("Le livret réglementé le plus rémunérateur du marché, sans aucun risque de perte en capital.")

    st.markdown("""
        <div style="background:#E8F5E9; border-left:4px solid #2E8B57; padding:10px 14px; border-radius:8px; margin-bottom:12px; font-size:0.85rem;">
            <b>✨ Caractéristiques réglementées :</b><br>
            • Taux net garanti : <b>4,00 % / an</b> (exonéré d'impôts et prélèvements sociaux)<br>
            • Plafond de dépôt : <b>10 000 €</b><br>
            • Éligibilité : Réservé aux revenus modestes (Revenu fiscal &lt; 22 419 €).
        </div>
    """, unsafe_allow_html=True)

    deposit_init = st.number_input("Versement initial (€) :", min_value=10.0, max_value=10000.0, value=150.0, step=50.0)
    monthly_add = st.slider("Épargne programmée chaque mois (€) :", min_value=0, max_value=500, value=50, step=10)

    # Calcul des gains estimés sur 1 an
    rate = 0.04
    estimated_total_placed = deposit_init + (monthly_add * 12)
    # Intérêts approximatifs selon la règle des quinzaines
    interest_1y = (deposit_init * rate) + (monthly_add * 6 * rate)

    st.markdown(f"""
        <div style="background:#F4FBF7; border:1px solid #C8E6C9; border-radius:10px; padding:12px; text-align:center; margin:14px 0;">
            <span style="font-size:0.8rem; color:#666;">Gain estimé au bout de 12 mois :</span><br>
            <span style="font-size:1.6rem; font-weight:800; color:#1A432A;">+{interest_1y:.2f} € net</span><br>
            <span style="font-size:0.75rem; color:#2E8B57;">Capital final estimé : <b>{estimated_total_placed + interest_1y:.2f} €</b></span>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 Valider la demande d'ouverture en ligne", type="primary", use_container_width=True):
        st.session_state.lep_opened = True
        st.success(f"Félicitations {profile.name} ! Votre dossier de LEP a été pré-validé. Un versement de {deposit_init:.0f} € et une épargne automatique de {monthly_add:.0f} €/mois ont été enregistrés.")


@st.dialog("Investir en Bourse : PEA ou Compte-Titres (CTO)")
def open_stock_investment_dialog(db: BankBackend, me_id: str):
    """Modale interactive pour simuler et ouvrir un plan d'investissement en actions (PEA ou CTO)."""
    profile = db.get_user_profile(me_id)
    st.markdown("<h3 style='text-align:center; color:#1A432A; margin-bottom:2px;'>📈 Investissement en Bourse</h3>", unsafe_allow_html=True)
    st.caption("Faites fructifier votre capital sur les marchés financiers avec les meilleurs supports réglementés.")

    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.markdown("""
            <div style="background:#E8F5E9; border-left:3px solid #2E8B57; padding:8px 10px; border-radius:6px; font-size:0.75rem;">
                <b>🇪🇺 PEA (Plan d'Épargne Actions)</b><br>
                • Exonération d'impôt sur les gains après 5 ans (seuls 17,2% de prélèvements sociaux).<br>
                • Plafond : 150 000 €.<br>
                • Univers : Actions européennes et ETF monde éligibles.
            </div>
        """, unsafe_allow_html=True)
    with col_info2:
        st.markdown("""
            <div style="background:#E3F2FD; border-left:3px solid #1976D2; padding:8px 10px; border-radius:6px; font-size:0.75rem;">
                <b>🌍 CTO (Compte-Titres Ordinaire)</b><br>
                • Liberté totale sans aucun plafond.<br>
                • Univers mondial illimité (actions US, tech, ETF globaux).<br>
                • Fiscalité : Flat tax de 30% sur les plus-values réalisées.
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    account_choice = st.radio(
        "Support d'investissement souhaité :",
        ["PEA (Recommandé - Fiscalité avantageuse)", "CTO (Compte-Titres - Flexibilité mondiale)"],
        horizontal=True
    )

    col_inv1, col_inv2 = st.columns(2)
    with col_inv1:
        initial_invest = st.number_input("Investissement initial (€) :", min_value=50.0, value=200.0, step=50.0)
        years = st.slider("Horizon de placement (années) :", min_value=2, max_value=25, value=5, step=1)
    with col_inv2:
        monthly_dca = st.slider("Versement mensuel programmé (DCA) (€) :", min_value=0, max_value=500, value=50, step=10)
        annual_yield = st.slider("Hypothèse de rendement annuel moyen (%) :", min_value=3.0, max_value=12.0, value=7.0, step=0.5, help="Rendement historique moyen annualisé des marchés mondiaux diversifiés (ex: MSCI World).")

    # Calcul des intérêts composés
    r = annual_yield / 100.0
    total_months = years * 12
    monthly_rate = (1 + r) ** (1 / 12) - 1

    capital_invested = initial_invest + (monthly_dca * total_months)
    # Formule valeur future avec versements réguliers
    fv_initial = initial_invest * ((1 + r) ** years)
    if monthly_rate > 0:
        fv_monthly = monthly_dca * (((1 + monthly_rate) ** total_months - 1) / monthly_rate)
    else:
        fv_monthly = monthly_dca * total_months
    final_capital = fv_initial + fv_monthly
    capital_gain = max(0.0, final_capital - capital_invested)

    is_pea = "PEA" in account_choice
    tax_rate = 0.172 if is_pea else 0.30
    tax_amount = capital_gain * tax_rate
    net_gain = capital_gain - tax_amount

    st.markdown(f"""
        <div style="background:#F4FBF7; border:1px solid #C8E6C9; border-radius:10px; padding:12px; margin:12px 0; text-align:center;">
            <div style="display:flex; justify-content:space-around; align-items:center;">
                <div>
                    <span style="font-size:0.75rem; color:#666;">Capital investi :</span><br>
                    <b style="font-size:1.1rem; color:#1A432A;">{capital_invested:.0f} €</b>
                </div>
                <div>
                    <span style="font-size:0.75rem; color:#666;">Capital final estimé :</span><br>
                    <b style="font-size:1.3rem; color:#2E8B57;">{final_capital:.0f} €</b>
                </div>
                <div>
                    <span style="font-size:0.75rem; color:#666;">Gain net estimé :</span><br>
                    <b style="font-size:1.1rem; color:#1B5E20;">+{net_gain:.0f} €</b>
                </div>
            </div>
            <div style="font-size:0.7rem; color:#777; margin-top:6px;">
                Fiscalité appliquée : {"17,2% de prélèvements sociaux (exonéré d'impôt sur le revenu via PEA)" if is_pea else "Flat Tax de 30% (CTO)"}
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 Valider la demande d'ouverture de compte d'investissement", type="primary", use_container_width=True):
        st.session_state.stock_account_opened = account_choice
        chosen_type = "PEA" if is_pea else "CTO"
        st.success(f"Bravo {profile.name} ! Votre demande d'ouverture de {chosen_type} a été prise en compte avec un dépôt initial de {initial_invest:.0f} € et {monthly_dca:.0f} €/mois programmés.")


@st.dialog("Définir une alerte de plafond de budget")
def set_budget_ceiling_dialog(db: BankBackend, me_id: str, category_name: str = "Alimentation & Restauration", current_spent: float = 250.0):
    """Modale interactive pour instaurer une limite saine sur une catégorie en surcoût."""
    st.markdown("<h3 style='text-align:center; color:#1A432A; margin-bottom:2px;'>🎯 Alerte Plafond de Budget</h3>", unsafe_allow_html=True)
    st.caption("Gardez le contrôle sur vos dépenses courantes en fixant une limite préventive.")

    st.markdown(f"""
        <div style="background:#FFF9C4; border-left:4px solid #FBC02D; padding:10px; border-radius:8px; margin-bottom:12px; font-size:0.85rem;">
            Poste ciblé : <b>{category_name}</b><br>
            Dépenses constatées sur 30 jours : <b>{current_spent:.2f} €</b>
        </div>
    """, unsafe_allow_html=True)

    ceiling = st.number_input("Plafond mensuel maximal souhaité (€) :", min_value=10.0, value=max(50.0, round(current_spent * 0.8, 0)), step=10.0)

    if st.button("💾 Enregistrer ce plafond d'alerte", type="primary", use_container_width=True):
        if 'budget_ceilings' not in st.session_state:
            st.session_state.budget_ceilings = {}
        st.session_state.budget_ceilings[category_name] = ceiling
        st.toast(f"Plafond de {ceiling:.0f} € activé pour {category_name} !")
        st.rerun()


