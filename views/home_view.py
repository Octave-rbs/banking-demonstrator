"""
Vue Accueil : Solde du compte personnel et historique des opérations.
"""

import streamlit as st
from services import BankBackend
from views.dialogs import share_existing_tx_dialog


def render_home_view(db: BankBackend, me_id: str):
    # Carte du solde disponible
    st.markdown(f"""
        <div class="metric-card primary">
            <div class="metric-title">Solde Courant Disponible</div>
            <div class="metric-value">{db.account_balance:,.2f} €</div>
            <div class="metric-sub">Compte Bancaire • Mis à jour en temps réel</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<h4 style='font-size:1.05rem; color:#1A432A; margin: 18px 0 8px 0;'>Dernières opérations</h4>", unsafe_allow_html=True)

    my_txs = [tx for tx in db.transactions if tx.user_id == me_id]
    if not my_txs:
        st.info("Aucune opération enregistrée.")
        return

    # Filtre de recherche
    filter_text = st.text_input("Rechercher un commerçant ou une dépense...", label_visibility="collapsed", placeholder="🔍 Rechercher...")

    filtered_txs = reversed(my_txs)
    if filter_text.strip():
        q = filter_text.lower()
        filtered_txs = [t for t in my_txs if q in t.merchant.lower() or q in t.category.lower()]

    for tx in list(filtered_txs)[:15]:
        is_shared = tx.shared_account_id is not None
        group_name = db.groups[tx.shared_account_id].name if is_shared and tx.shared_account_id in db.groups else ""

        amt_color = "#28A745" if tx.amount < 0 else "#222"
        amt_prefix = "+" if tx.amount < 0 else "-"
        shared_badge_html = f"<span style='color:#2E8B57; font-size:0.75rem; font-weight:700;'>✓ Partagé ({group_name})</span>" if is_shared else ""

        tx_html = (
            f'<div class="tx-item">'
            f'<div style="display:flex; justify-content:space-between; align-items:flex-start;">'
            f'<div><span class="tx-merchant">{tx.merchant}</span> <span class="tx-cat-badge">{tx.category}</span></div>'
            f'<div class="tx-amt" style="color: {amt_color};">{amt_prefix}{abs(tx.amount):.2f} €</div>'
            f'</div>'
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px;">'
            f'<span class="tx-meta">{tx.date.strftime("%d/%m/%Y")} • {tx.method.capitalize()}</span>'
            f'{shared_badge_html}'
            f'</div>'
            f'</div>'
        )
        st.markdown(tx_html, unsafe_allow_html=True)

        # Bouton d'action pour partager la dépense
        if tx.amount > 0 and not tx.is_settlement:
            col_spc, col_btn = st.columns([2, 1.8])
            with col_btn:
                btn_label = "Modifier partage" if is_shared else "🤝 Partager"
                btn_type = "secondary" if is_shared else "primary"
                if st.button(btn_label, key=f"btn_share_{tx.id}", type=btn_type, use_container_width=True):
                    share_existing_tx_dialog(db, tx.id)
