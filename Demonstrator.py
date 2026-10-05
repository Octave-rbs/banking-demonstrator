import streamlit as st
import pandas as pd

# ==========================================
# 1. CONFIGURATION DE LA PAGE
# ==========================================
st.set_page_config(page_title="Nova Banque", page_icon="🌿", layout="centered")

# ==========================================
# 2. INJECTION CSS (LE SECRET DE L'UI MOBILE)
# ==========================================
st.markdown("""
    <style>
    /* Masquer le menu Streamlit et le header par défaut */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* Simuler l'écran d'un smartphone (iPhone) sur desktop */
    [data-testid="block-container"] {
        max-width: 414px !important; /* Largeur d'un smartphone */
        margin: 20px auto !important; /* Centrer sur l'écran */
        padding: 30px 15px 80px 15px !important;
        background-color: #F7F9F8;
        border-radius: 40px;
        box-shadow: 0px 10px 30px rgba(0, 0, 0, 0.15); /* Ombre pour l'effet 3D */
        border: 8px solid #222; /* Contour noir du téléphone */
        min-height: 850px;
        position: relative;
        overflow-x: hidden;
    }

    /* Couleurs et typographie */
    :root {
        --primary-green: #1A432A;
        --accent-green: #2E8B57;
    }

    /* Composants UI Bancaires */
    .metric-card {
        background: linear-gradient(135deg, #1A432A, #2E8B57);
        border-radius: 20px;
        padding: 25px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(46,139,87,0.3);
    }
    .metric-title { font-size: 0.9rem; opacity: 0.8; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 2.5rem; font-weight: 700; margin: 5px 0; }
    
    .tx-row {
        background: white;
        padding: 15px;
        border-radius: 16px;
        margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }
    
    .tx-details { font-size: 0.9rem; font-weight: 600; color: #333; }
    .tx-date { font-size: 0.75rem; color: #888; margin-top: 2px;}
    .tx-amount { font-weight: 700; font-size: 0.95rem; text-align: right;}
    .tx-amount.positive { color: #2E8B57; }
    .tx-amount.negative { color: #333; }

    /* Customisation de la barre de navigation Streamlit (st.radio) */
    div.row-widget.stRadio > div {
        background: white;
        border-radius: 20px;
        padding: 5px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    /* Titre de l'app */
    .app-header {
        text-align: center;
        font-size: 1.2rem;
        font-weight: bold;
        color: var(--primary-green);
        margin-bottom: 20px;
        padding-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. DONNÉES ET MOTEUR (MOCK)
# ==========================================
if 'personal_balance' not in st.session_state:
    st.session_state.personal_balance = 2847.32

if 'transactions' not in st.session_state:
    st.session_state.transactions = [
        {"id": 1, "date": "Aujourd'hui", "desc": "Carrefour", "amount": -72.40, "icon": "🛒", "shared": False},
        {"id": 2, "date": "Hier", "desc": "Boutique APM Monaco", "amount": -120.00, "icon": "💍", "shared": False},
        {"id": 3, "date": "05 Sept", "desc": "Virement Arthur", "amount": 50.00, "icon": "⬇️", "shared": False},
        {"id": 4, "date": "02 Sept", "desc": "Loyer Septembre", "amount": -650.00, "icon": "🏠", "shared": False},
        {"id": 5, "date": "01 Sept", "desc": "Remboursement", "amount": 145.50, "icon": "💼", "shared": False},
    ]

if 'shared_group' not in st.session_state:
    st.session_state.shared_group = {
        "name": "Coloc Paris",
        "members": ["Moi", "Emma", "Lucas", "Thomas"],
        "expenses": [
            {"id": 101, "desc": "Électricité (EDF)", "amount": 84.20, "paid_by": "Emma", "date": "01 Sept"},
        ]
    }

def calculate_balances():
    group = st.session_state.shared_group
    balances = {m: 0.0 for m in group["members"]}
    for exp in group["expenses"]:
        payer = exp["paid_by"]
        amount = exp["amount"]
        split = amount / len(group["members"])
        balances[payer] += amount
        for m in balances:
            balances[m] -= split
    return balances

def optimize_transfers(balances):
    creditors = [[m, b] for m, b in balances.items() if b > 0.01]
    debtors = [[m, -b] for m, b in balances.items() if b < -0.01]
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)
    transfers = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        d_name, d_amt = debtors[i]
        c_name, c_amt = creditors[j]
        amount = min(d_amt, c_amt)
        transfers.append((d_name, c_name, amount))
        debtors[i][1] -= amount
        creditors[j][1] -= amount
        if debtors[i][1] < 0.01: i += 1
        if creditors[j][1] < 0.01: j += 1
    return transfers

def share_tx_to_group(tx_id):
    tx = next(t for t in st.session_state.transactions if t["id"] == tx_id)
    tx["shared"] = True
    st.session_state.shared_group["expenses"].insert(0, {
        "id": tx["id"] + 1000,
        "desc": tx["desc"],
        "amount": abs(tx["amount"]),
        "paid_by": "Moi",
        "date": "Aujourd'hui"
    })

# ==========================================
# 4. NAVIGATION TOP-BAR (STYLE MOBILE)
# ==========================================
st.markdown("<div class='app-header'>🌿 Nova Banque</div>", unsafe_allow_html=True)

# Navigation horizontale sans sidebar
menu = st.radio(" ", ["Accueil", "Partagé", "Profil"], horizontal=True, label_visibility="collapsed")
st.markdown("<br/>", unsafe_allow_html=True)

# ==========================================
# 5. VUES DE L'APPLICATION
# ==========================================
if menu == "Accueil":
    # Carte bancaire / Solde
    st.markdown("""
        <div class="metric-card">
            <div class="metric-title">Solde Disponible</div>
            <div class="metric-value">{:,.2f} €</div>
            <div style="font-size: 0.8rem; opacity: 0.9;">Mise à jour à l'instant</div>
        </div>
    """.format(st.session_state.personal_balance).replace(',', ' '), unsafe_allow_html=True)
    
    st.markdown("<h4 style='font-size:1.1rem; color:#1A432A;'>Historique</h4>", unsafe_allow_html=True)
    
    for tx in st.session_state.transactions:
        with st.container():
            col1, col2 = st.columns([3, 1.5])
            with col1:
                st.markdown(f"""
                    <div class="tx-details">{tx['icon']} {tx['desc']}</div>
                    <div class="tx-date">{tx['date']}</div>
                """, unsafe_allow_html=True)
            with col2:
                amount_class = "positive" if tx['amount'] > 0 else "negative"
                st.markdown(f"<div class='tx-amount {amount_class}'>{tx['amount']:.2f} €</div>", unsafe_allow_html=True)
                
                # Le bouton d'innovation "Partager"
                if not tx["shared"] and tx["amount"] < 0:
                    if st.button("Partager", key=f"share_{tx['id']}", use_container_width=True):
                        share_tx_to_group(tx["id"])
                        st.rerun()
                elif tx["shared"]:
                    st.markdown("<div style='color:#2E8B57; font-size:0.75rem; text-align:right; font-weight:bold;'>✓ Partagé</div>", unsafe_allow_html=True)
            st.markdown("<hr style='margin:10px 0; opacity: 0.1;'/>", unsafe_allow_html=True)

elif menu == "Partagé":
    st.markdown(f"<h3 style='text-align:center;'>🏘️ {st.session_state.shared_group['name']}</h3>", unsafe_allow_html=True)
    
    balances = calculate_balances()
    my_balance = balances["Moi"]
    
    # Carte de statut de la colocation
    bg_color = "linear-gradient(135deg, #2E8B57, #3CB371)" if my_balance >= 0 else "linear-gradient(135deg, #D9534F, #E74C3C)"
    status_text = "On vous doit" if my_balance >= 0 else "Vous devez"
    
    st.markdown(f"""
        <div class="metric-card" style="background: {bg_color};">
            <div class="metric-title">{status_text}</div>
            <div class="metric-value">{abs(my_balance):.2f} €</div>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🧾 Dépenses", "💸 Équilibrer"])
    
    with tab1:
        for exp in st.session_state.shared_group["expenses"]:
            st.markdown(f"""
                <div class="tx-row">
                    <div class="tx-details">{exp['desc']}</div>
                    <div class="tx-date">Payé par {exp['paid_by']} - {exp['date']}</div>
                    <div class="tx-amount">{exp['amount']:.2f} €</div>
                </div>
            """, unsafe_allow_html=True)

    with tab2:
        transfers = optimize_transfers(balances)
        if not transfers:
            st.success("🎉 Tout est équilibré !")
        else:
            for d, c, amt in transfers:
                st.info(f"**{d}** doit **{amt:.2f} €** à **{c}**")
            
            if st.button("Rembourser les dettes", type="primary", use_container_width=True):
                st.session_state.shared_group["expenses"] = []
                st.rerun()

else:
    st.info("Paramètres de l'application (Fictif)")