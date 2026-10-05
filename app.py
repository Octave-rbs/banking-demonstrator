import streamlit as st
import os
from datetime import datetime
from backend import BankBackend
from ai_advisor import BankingAIAdvisor
from models import User, Transaction, SharedGroup, UserProfile

# ==========================================
# 1. CONFIGURATION ET INITIALISATION DE SESSION
# ==========================================
st.set_page_config(
    page_title="Démonstrateur bancaire",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Initialisation de la base de données métier dans la session
if 'db' not in st.session_state:
    st.session_state.db = BankBackend()

# Initialisation du conseiller IA
if 'ai_advisor' not in st.session_state:
    hf_key = None
    try:
        hf_key = st.secrets.get("HUGGING_FACE_API_KEY")
    except Exception:
        hf_key = None
    st.session_state.ai_advisor = BankingAIAdvisor(hf_token=hf_key)

# Suivi des fichiers de démo chargés automatiquement
if 'loaded_files' not in st.session_state:
    st.session_state.loaded_files = set()

# Historique du chat avec le coach financier
if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []

# Cache du dernier audit financier généré
if 'last_audit' not in st.session_state:
    st.session_state.last_audit = None

if 'executive_audit_text' not in st.session_state:
    st.session_state.executive_audit_text = None

if 'is_streaming_audit' not in st.session_state:
    st.session_state.is_streaming_audit = False

db: BankBackend = st.session_state.db
ai: BankingAIAdvisor = st.session_state.ai_advisor
ME_ID = db.primary_user_id

# ==========================================
# CHARGEMENT AUTOMATIQUE DES DONNÉES DE DÉMO
# ==========================================
DATA_DIR = "data"
if os.path.exists(DATA_DIR):
    csv_candidates = [
        ("operations_60j_paul.csv", "u1"),
        ("operations_60j_emma.csv", "u2")
    ]
    for filename, uid in csv_candidates:
        filepath = os.path.join(DATA_DIR, filename)
        if os.path.exists(filepath) and filename not in st.session_state.loaded_files:
            try:
                with open(filepath, "rb") as f:
                    db.process_transaction_file(f, uid, "csv")
                st.session_state.loaded_files.add(filename)
            except Exception as e:
                pass

# ==========================================
# 2. DESIGN & STYLES CSS (FRAME SMARTPHONE)
# ==========================================
st.markdown("""
    <style>
    /* Masquer les éléments natifs Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Châssis de smartphone moderne */
    [data-testid="block-container"] {
        max-width: 420px !important;
        margin: 10px auto !important;
        padding: 20px 14px 75px 14px !important;
        background-color: #F8FAF9;
        border-radius: 42px;
        box-shadow: 0px 15px 40px rgba(0, 0, 0, 0.18);
        border: 9px solid #1C1E21;
        min-height: 870px;
        position: relative;
    }

    /* Barre d'état smartphone */
    .status-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.72rem;
        font-weight: 700;
        color: #444;
        padding: 0 8px 10px 8px;
    }

    /* En-tête de l'application */
    .app-brand {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .app-brand-title {
        font-size: 1.25rem;
        font-weight: 800;
        color: #1A432A;
        letter-spacing: -0.5px;
    }
    .user-pill {
        background: #E8F5E9;
        color: #1A432A;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* Cartes métriques bancaires */
    .metric-card {
        border-radius: 22px;
        padding: 20px;
        color: white;
        text-align: center;
        margin-bottom: 15px;
        box-shadow: 0 8px 20px rgba(46, 139, 87, 0.25);
    }
    .metric-card.primary {
        background: linear-gradient(135deg, #1A432A 0%, #2E8B57 100%);
    }
    .metric-card.credit {
        background: linear-gradient(135deg, #1E7E34 0%, #28A745 100%);
    }
    .metric-card.debt {
        background: linear-gradient(135deg, #C82333 0%, #E04B59 100%);
    }
    .metric-title {
        font-size: 0.8rem;
        opacity: 0.85;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        margin: 4px 0;
        letter-spacing: -1px;
    }
    .metric-sub {
        font-size: 0.75rem;
        opacity: 0.9;
    }

    /* Lignes d'opérations */
    .tx-item {
        background: white;
        padding: 12px 14px;
        border-radius: 16px;
        margin-bottom: 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        border: 1px solid #EEF2F0;
    }
    .tx-merchant {
        font-size: 0.88rem;
        font-weight: 700;
        color: #222;
    }
    .tx-cat-badge {
        font-size: 0.65rem;
        background: #F0F4F2;
        color: #555;
        padding: 2px 6px;
        border-radius: 6px;
        font-weight: 600;
        margin-left: 6px;
    }
    .tx-meta {
        font-size: 0.72rem;
        color: #888;
        margin-top: 3px;
    }
    .tx-amt {
        font-size: 0.95rem;
        font-weight: 800;
        text-align: right;
    }

    /* Navigation Radio personnalisée */
    div.row-widget.stRadio > div {
        background: white;
        border-radius: 22px;
        padding: 4px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        justify-content: space-around;
        margin-bottom: 12px;
    }
    div.row-widget.stRadio label {
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        color: #1A432A !important;
    }

    /* Cartes de sections */
    .section-card {
        background: white;
        border-radius: 18px;
        padding: 16px;
        margin-bottom: 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        border: 1px solid #EEF2F0;
    }

    /* Scorecard de santé budgétaire */
    .scorecard-card {
        background: white;
        border-radius: 18px;
        padding: 16px;
        margin-bottom: 14px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 3px 10px rgba(0,0,0,0.03);
    }
    .scorecard-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #F1F5F9;
        padding-bottom: 10px;
        margin-bottom: 10px;
    }
    .scorecard-summary {
        font-size: 0.8rem;
        color: #475569;
        margin-bottom: 12px;
        background: #F8FAF9;
        padding: 8px 12px;
        border-radius: 10px;
    }
    .pillar-row {
        margin-bottom: 10px;
    }
    .pillar-header {
        display: flex;
        justify-content: space-between;
        font-size: 0.76rem;
        font-weight: 700;
        margin-bottom: 3px;
    }
    .pillar-bar-bg {
        background: #EEF2F0;
        border-radius: 6px;
        height: 7px;
        overflow: hidden;
    }
    .pillar-verdict {
        font-size: 0.7rem;
        color: #64748B;
        margin-top: 2px;
    }

    /* Style des boutons instantanés */
    .settle-badge {
        background: #E8F5E9;
        border-left: 4px solid #28A745;
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 8px;
        font-size: 0.82rem;
    }

    /* Style des boutons primaires doux (Partager, Enregistrer, etc.) */
    button[kind="primary"],
    [data-testid="stBaseButton-primary"],
    [data-testid="baseButton-primary"] {
        background-color: #3D7B66 !important;
        border-color: #3D7B66 !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 8px rgba(61, 123, 102, 0.22) !important;
        transition: all 0.2s ease-in-out !important;
    }
    button[kind="primary"]:hover,
    [data-testid="stBaseButton-primary"]:hover,
    [data-testid="baseButton-primary"]:hover {
        background-color: #326553 !important;
        border-color: #326553 !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(61, 123, 102, 0.32) !important;
    }
    button[kind="primary"]:active,
    [data-testid="stBaseButton-primary"]:active,
    [data-testid="baseButton-primary"]:active {
        background-color: #275243 !important;
        border-color: #275243 !important;
        color: #FFFFFF !important;
    }

    /* Style des boutons secondaires doux */
    button[kind="secondary"],
    [data-testid="stBaseButton-secondary"],
    [data-testid="baseButton-secondary"] {
        border-radius: 12px !important;
        border-color: #D4DFD8 !important;
        color: #2E5C4D !important;
        background-color: #FFFFFF !important;
        transition: all 0.2s ease-in-out !important;
    }
    button[kind="secondary"]:hover,
    [data-testid="stBaseButton-secondary"]:hover,
    [data-testid="baseButton-secondary"]:hover {
        border-color: #3D7B66 !important;
        color: #1A432A !important;
        background-color: #F4F8F6 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Barre de statut smartphone (Horloge & Réseau)
st.markdown("""
    <div class="status-bar">
        <span>10:05</span>
        <span>📶 5G &nbsp; 🔋 98%</span>
    </div>
""", unsafe_allow_html=True)

# En-tête de la marque
st.markdown(f"""
    <div class="app-brand">
        <div class="app-brand-title">Démonstrateur bancaire</div>
        <div class="user-pill">👤 Paul</div>
    </div>
""", unsafe_allow_html=True)

# Menu de navigation principal
menu = st.radio(
    "Navigation",
    ["🏠 Accueil", "👥 Partagé", "📊 Budget", "🤖 Coach IA", "⚙️ Admin"],
    horizontal=True,
    label_visibility="collapsed"
)
st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

# ==========================================
# MODALES DIALOG : DÉPENSES PARTAGÉES
# ==========================================

@st.dialog("Partager une dépense existante")
def share_existing_tx_dialog(tx_id: str):
    tx = next((t for t in db.transactions if t.id == tx_id), None)
    if not tx:
        st.error("Opération introuvable.")
        return

    st.markdown(f"<h3 style='text-align:center; color:#1A432A; margin-bottom:2px;'>{tx.merchant}</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; font-size:1.6rem; font-weight:800; margin-top:0;'>{tx.amount:.2f} €</p>", unsafe_allow_html=True)

    # Choix du groupe
    group_options = {gid: g.name for gid, g in db.groups.items()}
    selected_gid = st.selectbox("Sélectionner le groupe :", options=list(group_options.keys()), format_func=lambda x: group_options[x], index=list(group_options.keys()).index(db.active_group_id))
    
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
def add_new_group_expense_dialog(group_id: str):
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
        index=list(member_users.keys()).index(ME_ID) if ME_ID in member_users else 0,
        format_func=lambda uid: f"{member_users[uid].avatar} {member_users[uid].name} (Moi)" if uid == ME_ID else f"{member_users[uid].avatar} {member_users[uid].name}"
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
def create_group_dialog():
    st.markdown("<h3 style='text-align:center; color:#1A432A;'>Nouveau Groupe</h3>", unsafe_allow_html=True)
    g_name = st.text_input("Nom du groupe", placeholder="Ex: Voyage Barcelone, Weekend Ski")
    g_icon = st.selectbox("Icône", ["🏘️", "✈️", "🏖️", "🍕", "🎉", "🚗", "🎓"])
    g_desc = st.text_input("Description", placeholder="Ex: Dépenses partagées du séjour")

    available_contacts = [u for uid, u in db.users.items() if uid != ME_ID]
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

# ==========================================
# VUE 1 : ACCUEIL & OPÉRATIONS PERSONNELLES
# ==========================================
if menu == "🏠 Accueil":
    # Carte du solde disponible du compte bancaire principal
    st.markdown(f"""
        <div class="metric-card primary">
            <div class="metric-title">Solde Courant Disponible</div>
            <div class="metric-value">{db.account_balance:,.2f} €</div>
            <div class="metric-sub">Compte Bancaire • Mis à jour en temps réel</div>
        </div>
    """, unsafe_allow_html=True)

    # Historique des transactions
    st.markdown("<h4 style='font-size:1.05rem; color:#1A432A; margin: 18px 0 8px 0;'>Dernières opérations</h4>", unsafe_allow_html=True)

    my_txs = [tx for tx in db.transactions if tx.user_id == ME_ID]
    if not my_txs:
        st.info("Aucune opération enregistrée. Allez dans l'onglet Admin pour charger vos données de test.")
    else:
        # Filtre de recherche rapide
        filter_text = st.text_input("Rechercher un commerçant ou une dépense...", label_visibility="collapsed", placeholder="🔍 Rechercher...")
        
        filtered_txs = reversed(my_txs)
        if filter_text.strip():
            filtered_txs = [t for t in my_txs if filter_text.lower() in t.merchant.lower() or filter_text.lower() in t.category.lower()]

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
                        share_existing_tx_dialog(tx.id)

# ==========================================
# VUE 2 : COMPTE PARTAGÉ / TRICOUNT INTÉGRÉ
# ==========================================
elif menu == "👥 Partagé":
    # Sélecteur de groupe en haut
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
            create_group_dialog()

    group = db.groups[db.active_group_id]
    st.caption(f"{group.description} • {len(group.members)} membres")

    # Calcul des balances nettes du groupe
    balances = db.calculate_balances(db.active_group_id)
    my_balance = balances.get(ME_ID, 0.0)

    # Carte de statut personnalisée
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

    # Bouton rapide d'ajout direct d'une dépense de groupe
    if st.button("➕ Ajouter une dépense dans ce groupe", type="primary", use_container_width=True):
        add_new_group_expense_dialog(db.active_group_id)

    st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

    # Onglets Dépenses vs Remboursements & Équilibre
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
                payer_label = "Moi" if tx.user_id == ME_ID else payer_user.name
                
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

                # Innovation Bancaire : Le bouton de virement instantané en 1 clic
                btn_key = f"settle_{d_id}_{c_id}_{amt}"
                if st.button(f"⚡ Demande de paiement instantané de {amt:.2f} € ({d_name} ➔ {c_name})", key=btn_key, type="primary", use_container_width=True):
                    settlement_tx = db.execute_instant_settlement(
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
                    <div>{u.avatar} <b>{u.name}</b> {'(Moi)' if uid == ME_ID else ''}</div>
                    <div style="font-weight:700; color:{bal_col};">{bal_str}</div>
                </div>
            """, unsafe_allow_html=True)

        available_to_add = db.get_available_contacts(db.active_group_id)
        if available_to_add:
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            add_sel = st.selectbox("Ajouter un contact au groupe :", options=[u.id for u in available_to_add], format_func=lambda x: next(u.name for u in available_to_add if u.id == x))
            if st.button("Ajouter ce membre", use_container_width=True):
                db.add_member_to_group(add_sel, db.active_group_id)
                st.rerun()

# ==========================================
# VUE 3 : OUTIL DE BUDGÉTISATION INTELLIGENTE
# ==========================================
elif menu == "📊 Budget":
    st.markdown("<h3 style='text-align:center; color:#1A432A; margin-bottom:5px;'>Assistant Budget</h3>", unsafe_allow_html=True)
    
    budget = db.analyze_monthly_budget(ME_ID)
    extra_ctx = db.get_llm_financial_context(ME_ID)
    max_gap_cat = extra_ctx.get("max_gap_category", "")

    # 1. INDICATEUR DU MOIS CIVIL EN COURS (Ex: 1er au 11 septembre)
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

    # 2. SUIVI DU BUDGET SUR LE MOIS GLISSANT (30 JOURS)
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

    # 3. COMPARATEUR AVEC LES PAIRS (SUR 30 JOURS GLISSANTS)
    st.markdown("<h4 style='color:#1A432A; margin:22px 0 6px 0; font-size:1.05rem;'>Comparateur Pairs (Étudiants / Alternants Paris)</h4>", unsafe_allow_html=True)

    cats, peers, subcats = db.get_category_breakdown(ME_ID)

    if not cats:
        st.info("Données insuffisantes pour la comparaison.")
    else:
        for cat, spent_amt in cats.items():
            if cat in peers:
                p_info = peers[cat]
                avg = p_info['avg']
                tier = p_info.get('tier', 'moyenne')
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

                # Détail sous-catégories UNIQUEMENT si c'est la catégorie où l'écart est le plus important
                if is_critical and cat in subcats and len(subcats[cat]) > 1:
                    with st.expander(f"🔍 Détails exclusifs des dépenses ({cat})", expanded=True):
                        st.caption("Poste ciblé prioritairement pour résorber l'écart avec les pairs :")
                        for sub_name, sub_amt in subcats[cat].items():
                            st.write(f"• {sub_name} : **{sub_amt:.2f} €**")

# ==========================================
# VUE 4 : COACH FINANCIER IA (LANGCHAIN & HUGGING FACE)
# ==========================================
elif menu == "🤖 Coach IA":
    st.markdown("<h3 style='text-align:center; color:#1A432A; margin-bottom:2px;'>Advisor IA</h3>", unsafe_allow_html=True)
    st.caption("Votre coach patrimonial et budgétaire propulsé par l'IA.")

    profile = db.get_user_profile(ME_ID)
    budget = db.analyze_monthly_budget(ME_ID)
    cats, peers, subcats = db.get_category_breakdown(ME_ID)
    extra_ctx = db.get_llm_financial_context(ME_ID)

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

    # 2. Formulaire interactif pour personnaliser le profil et le champ libre
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
            help="Ce texte libre est injecté directement dans le contexte du modèle pour personnaliser ses réponses.",
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
            st.session_state.last_audit = None  # Réinitialiser pour forcer la régénération
            st.session_state.executive_audit_text = None
            st.session_state.is_streaming_audit = False
            st.toast("Profil et contexte IA enregistrés avec succès !")
            st.rerun()

    # 3. Scorecard de Santé Budgétaire Instantanée (< 5ms)
    health = db.calculate_health_score(ME_ID)
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

    # 4. Indicateur de statut du LLM & Configuration rapide
    if ai.is_hf_configured():
        st.caption(f"⚡ Inférence IA connectée : `{ai.default_model}` (Hugging Face API)")
    else:
        st.warning("⚠️ **Hugging Face API non connectée** : Renseignez votre token pour lancer le diagnostic IA approfondi en conditions réelles.")
        with st.expander("🔑 Configurer le token Hugging Face", expanded=True):
            quick_token = st.text_input("Votre token Hugging Face (`hf_...`) :", type="password", key="quick_hf_tok")
            if st.button("Connecter le LLM", key="btn_quick_tok"):
                ai.set_token(quick_token)
                st.rerun()

    # 5. Déclencheur de l'analyse IA
    btn_label = "✨ Actualiser le rapport exécutif IA" if st.session_state.executive_audit_text else "✨ Lancer l'analyse détaillée IA (Streaming)"
    if st.button(btn_label, type="primary", use_container_width=True):
        st.session_state.is_streaming_audit = True
        st.session_state.executive_audit_text = None

    # 6. Rendu en Streaming ou Affichage persistant du Rapport Exécutif
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
    
    # Suggestions rapides de questions
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

    # Affichage des échanges récents (ordre chronologique : question en premier, réponse en-dessous)
    for msg in st.session_state.chat_messages[-6:]:
        if msg["role"] == "user":
            st.markdown(f"<div style='background:#E8F5E9; padding:8px 12px; border-radius:12px; margin-bottom:4px; margin-top:10px; font-size:0.8rem; font-weight:600; border-left:4px solid #2E8B57;'>🧑‍💻 {msg['text']}</div>", unsafe_allow_html=True)
        else:
            with st.container(border=True):
                st.markdown(f"🤖 {msg['text']}")

# ==========================================
# VUE 5 : PARAMÈTRES & ADMIN
# ==========================================
elif menu == "⚙️ Admin":
    st.markdown("<h4 style='color:#1A432A;'>Paramètres du démonstrateur</h4>", unsafe_allow_html=True)

    # 1. Configuration de l'IA (Token Hugging Face)
    with st.expander("🔑 Configuration Clé Hugging Face (Optionnel)", expanded=False):
        st.caption("Entrez un token Hugging Face gratuit (`hf_...`) pour exécuter les requêtes via l'Inference API. Si vide, le moteur analytique expert intégré prend le relais sans risque.")
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
        prof = db.get_user_profile(ME_ID)
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

    # 4. Données de benchmark externe des pairs
    with st.expander("📊 Données de benchmark des pairs (Fichier externe)", expanded=False):
        st.caption("Les seuils statistiques (Top 10%, Top 30%, Moyenne) proviennent du fichier externe `data/benchmark_peers.json` ou `data/benchmark_peers.csv`.")
        
        bench_file_found = "data/benchmark_peers.json" if os.path.exists("data/benchmark_peers.json") else ("data/benchmark_peers.csv" if os.path.exists("data/benchmark_peers.csv") else "Données internes")
        st.info(f"Fichier source actif : `{bench_file_found}`")
        
        if st.button("🔄 Recharger les seuils depuis le fichier", use_container_width=True, key="btn_reload_bench"):
            db.peers_benchmark_data = db.load_peers_benchmark()
            st.session_state.last_audit = None
            st.toast("Seuils de benchmark rechargés avec succès !")
            st.rerun()

        # Tableau des seuils actuels
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