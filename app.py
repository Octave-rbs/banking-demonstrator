"""
Démonstrateur Bancaire Intelligent & Partagé.
Point d'entrée principal de l'application Streamlit.
"""

from pathlib import Path
import streamlit as st
from services import BankBackend
from services.repository import DATA_DIR, demo_date_offset
from ai import BankingAIAdvisor
from views import (
    render_home_view,
    render_shared_view,
    render_budget_view,
    render_advisor_view
)

# 1. Configuration de la page
st.set_page_config(
    page_title="Démonstrateur bancaire",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. Initialisation des états en session
if 'db' not in st.session_state:
    st.session_state.db = BankBackend()

if 'ai_advisor' not in st.session_state:
    hf_key = None
    try:
        hf_key = st.secrets.get("GROQ_API_KEY")
    except Exception:
        hf_key = None
    st.session_state.ai_advisor = BankingAIAdvisor(hf_token=hf_key)

if 'loaded_files' not in st.session_state:
    st.session_state.loaded_files = set()

if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []

if 'executive_audit_text' not in st.session_state:
    st.session_state.executive_audit_text = None

if 'is_streaming_audit' not in st.session_state:
    st.session_state.is_streaming_audit = False

if 'audit_action_cards' not in st.session_state:
    st.session_state.audit_action_cards = []

if 'audit_steps' not in st.session_state:
    st.session_state.audit_steps = []


db: BankBackend = st.session_state.db
ai: BankingAIAdvisor = st.session_state.ai_advisor
ME_ID = db.primary_user_id

# 3. Chargement automatique des fichiers CSV de démonstration
csv_candidates = [
    ("operations_60j_paul.csv", "u1"),
    ("operations_60j_emma.csv", "u2")
]
for filename, uid in csv_candidates:
    filepath = DATA_DIR / filename
    if filepath.exists() and filename not in st.session_state.loaded_files:
        try:
            with open(filepath, "rb") as f:
                db.process_transaction_file(f, uid, "csv", date_offset=demo_date_offset())
            st.session_state.loaded_files.add(filename)
        except Exception as e:
            st.warning(f"Impossible de charger {filename} : {e}")

# 4. Injection des styles CSS externes
CSS_FILE = Path(__file__).resolve().parent / "assets" / "styles.css"
if CSS_FILE.exists():
    with open(CSS_FILE, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# 5. Châssis mobile (Barre d'état & En-tête)
st.markdown("""
    <div class="status-bar">
        <span>10:05</span>
        <span>📶 5G &nbsp; 🔋 98%</span>
    </div>
    <div class="app-brand">
        <div class="app-brand-title">Démonstrateur bancaire</div>
        <div class="user-pill">👤 Paul</div>
    </div>
""", unsafe_allow_html=True)

# 6. Navigation principale
menu = st.radio(
    "Navigation",
    ["🏠 Accueil", "👥 Partagé", "📊 Budget", "🤖 Coach IA"],
    horizontal=True,
    label_visibility="collapsed"
)
st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

# 7. Routage vers les vues modulaires
if menu == "🏠 Accueil":
    render_home_view(db, ME_ID)
elif menu == "👥 Partagé":
    render_shared_view(db, ME_ID)
elif menu == "📊 Budget":
    render_budget_view(db, ME_ID)
elif menu == "🤖 Coach IA":
    render_advisor_view(db, ai, ME_ID)