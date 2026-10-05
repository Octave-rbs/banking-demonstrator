"""
Vue Partagé : Compte partagé multi-groupes, calcul des balances et virements instantanés.
"""

import streamlit as st
from services import BankBackend
from models import User
from views.dialogs import add_new_group_expense_dialog, create_group_dialog


def render_shared_view(db: BankBackend, me_id: str):
    group_ids = list(db.groups.keys())
    curr_index = group_ids.index(db.active_group_id) if db.active_group_id in group_ids else 0

    col_grp_sel, col_new_grp = st.columns([3, 1])
    with col_grp_sel:
        selected_group_id = st.selectbox(
            "Groupe actif :",
            options=group_ids,
            index=curr_index,
            format_func=lambda gid: f"{db.groups[gid].icon} {db.groups[gid].name}",
            label_visibility="collapsed"
        )
        if selected_group_id != db.active_group_id:
            db.switch_active_group(selected_group_id)
            st.rerun()

    with col_new_grp:
        if st.button("➕ Nouveau", use_container_width=True):
            create_group_dialog(db, me_id)

    group = db.groups[db.active_group_id]
    st.caption(f"{group.description} • {len(group.members)} membres")

    # Calcul des balances nettes du groupe
    balances = db.calculate_balances(db.active_group_id)
    my_balance = balances.get(me_id, 0.0)

    is_creditor = my_balance >= -0.01
    card_class = "credit" if is_creditor else "debt"
    status_text = "On vous doit" if is_creditor else "Vous devez"

    st.markdown(f"""
        <div class="metric-card {card_class}">
            <div class="metric-title">Votre Situation ({status_text})</div>
            <div class="metric-value">{abs(my_balance):.2f} €</div>
            <div class="metric-sub">{len(group.members)} amis dans ce compte partagé</div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("➕ Ajouter une dépense dans ce groupe", type="primary", use_container_width=True):
        add_new_group_expense_dialog(db, db.active_group_id, me_id)

    st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

    tab_dep, tab_bal, tab_mem = st.tabs(["🧾 Dépenses", "⚡ Rembourser (1 Clic)", "👥 Membres"])

    with tab_dep:
        shared_txs = db.get_shared_transactions(db.active_group_id)
        if not shared_txs:
            st.info("Aucune dépense partagée dans ce groupe. Cliquez sur le bouton ci-dessus ou partagez une opération depuis l'Accueil !")
        else:
            total_spent_group = sum(t.amount for t in shared_txs if not t.is_settlement)
            st.markdown(f"<div style='font-size:0.85rem; color:#555; margin-bottom:10px;'>Total des dépenses du groupe : <b>{total_spent_group:.2f} €</b></div>", unsafe_allow_html=True)

            for tx in reversed(shared_txs):
                payer_user = db.users.get(tx.user_id, User(id=tx.user_id, name="Inconnu"))
                payer_label = "Moi" if tx.user_id == me_id else payer_user.name

                if tx.is_settlement:
                    st.markdown(f"""
                        <div class="settle-badge">
                            <b>{tx.merchant}</b><br>
                            <span style="color:#555; font-size:0.75rem;">{tx.date.strftime('%d/%m/%Y')} • Remboursement instantané validé</span>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                        <div class="tx-item">
                            <div style="display:flex; justify-content:space-between;">
                                <span class="tx-merchant">{tx.merchant}</span>
                                <span class="tx-amt">{tx.amount:.2f} €</span>
                            </div>
                            <div class="tx-meta" style="margin-top:4px;">
                                Payé par <b>{payer_label}</b> le {tx.date.strftime('%d/%m/%Y')}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

    with tab_bal:
        st.markdown("<h5 style='color:#1A432A; margin-bottom:8px;'>Optimisation des virements</h5>", unsafe_allow_html=True)
        st.caption("Le moteur bancaire résout les dettes croisées pour minimiser le nombre de transactions.")

        transfers = db.optimize_transfers(balances)
        if not transfers:
            st.success("🎉 Tout est équilibré ! Personne ne doit rien dans ce groupe.")
        else:
            for d_name, c_name, amt, d_id, c_id in transfers:
                st.markdown(f"""
                    <div style="background:white; border-radius:14px; padding:12px; margin-bottom:8px; border-left: 4px solid #F39C12; box-shadow:0 1px 4px rgba(0,0,0,0.04);">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <span style="font-weight:700; font-size:0.9rem;">{d_name}</span> ➔ <span style="font-weight:700; font-size:0.9rem;">{c_name}</span>
                                <div style="font-size:0.75rem; color:#777;">Dette nette calculée</div>
                            </div>
                            <div style="font-size:1.1rem; font-weight:800; color:#1A432A;">
                                {amt:.2f} €
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                btn_key = f"settle_{d_id}_{c_id}_{amt}"
                if st.button(f"⚡ Demande de paiement instantané de {amt:.2f} € ({d_name} ➔ {c_name})", key=btn_key, type="primary", use_container_width=True):
                    db.execute_instant_settlement(
                        from_user_id=d_id,
                        to_user_id=c_id,
                        amount=amt,
                        group_id=db.active_group_id
                    )
                    st.success(f"Virement instantané de {amt:.2f} € validé ! Comptes mis à jour.")
                    st.rerun()

    with tab_mem:
        st.markdown("<h5 style='color:#1A432A;'>Membres du groupe</h5>", unsafe_allow_html=True)
        for uid in group.members:
            u = db.users.get(uid, User(id=uid, name="Inconnu"))
            bal_val = balances.get(uid, 0.0)
            bal_str = f"+{bal_val:.2f} €" if bal_val > 0 else f"{bal_val:.2f} €"
            bal_col = "#28A745" if bal_val >= 0 else "#C82333"

            st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; background:white; padding:10px 14px; border-radius:12px; margin-bottom:6px;">
                    <div>{u.avatar} <b>{u.name}</b> {'(Moi)' if uid == me_id else ''}</div>
                    <div style="font-weight:700; color:{bal_col};">{bal_str}</div>
                </div>
            """, unsafe_allow_html=True)

        available_to_add = db.get_available_contacts(db.active_group_id)
        if available_to_add:
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            add_sel = st.selectbox(
                "Ajouter un contact au groupe :",
                options=[u.id for u in available_to_add],
                format_func=lambda x: next(u.name for u in available_to_add if u.id == x)
            )
            if st.button("Ajouter ce membre", use_container_width=True):
                db.add_member_to_group(add_sel, db.active_group_id)
                st.rerun()
