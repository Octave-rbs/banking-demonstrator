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
