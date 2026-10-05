import os
import json
import pandas as pd
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from models import User, UserProfile, SharedGroup, Transaction

class BankBackend:
    def __init__(self):
        # Base de données simulée en mémoire
        self.transactions: List[Transaction] = []
        
        # Répertoire des utilisateurs du démonstrateur
        self.users: Dict[str, User] = {
            "u1": User(id="u1", name="Paul", avatar="🧑‍💻"),
            "u2": User(id="u2", name="Emma", avatar="👩‍🎨"),
            "u3": User(id="u3", name="Lucas", avatar="👨‍🎓"),
            "u4": User(id="u4", name="Thomas", avatar="🧑‍🔬"),
            "u5": User(id="u5", name="Arthur", avatar="👨‍🍳")
        }
        
        # Profils financiers détaillés
        self.user_profiles: Dict[str, UserProfile] = {
            "u1": UserProfile(
                id="u1",
                name="Paul",
                age=22,
                family_situation="Célibataire",
                status="Alternant / Étudiant",
                job_activity="Apprenti Ingénieur en Informatique",
                housing_type="Colocation",
                school_or_company="Thales & Polytech",
                city="Paris 5e",
                country="France",
                monthly_net_income=1350.0,
                rent_amount=650.0,
                custom_notes=""
            ),
            "u2": UserProfile(
                id="u2",
                name="Emma",
                age=23,
                family_situation="En couple",
                status="Alternante Graphisme",
                job_activity="Designer UI/UX en alternance",
                housing_type="Colocation",
                school_or_company="École Estienne",
                city="Paris 5e",
                country="France",
                monthly_net_income=1200.0,
                rent_amount=650.0,
                custom_notes=""
            )
        }
        
        # Groupes de dépenses partagées (Tricount intégré)
        self.groups: Dict[str, SharedGroup] = {
            "coloc_paris_01": SharedGroup(
                id="coloc_paris_01",
                name="Coloc Paris - Rivoli",
                description="Dépenses courantes de la colocation à 4",
                members=["u1", "u2", "u3", "u4"],
                icon="🏘️"
            ),
            "voyage_barcelone": SharedGroup(
                id="voyage_barcelone",
                name="Weekend Barcelone",
                description="Billets, Airbnb et tapas entre amis",
                members=["u1", "u2", "u5"],
                icon="✈️"
            )
        }
        
        # Groupe actif par défaut
        self.active_group_id = "coloc_paris_01"
        self.primary_user_id = "u1"
        self.account_balance = 2847.32 # Solde du compte principal
        # Données de référence externes pour les benchmarks de pairs (multi-seuils)
        self.peers_benchmark_data: Dict[str, Dict] = self.load_peers_benchmark()

    # ==========================================
    # GESTION DES UTILISATEURS ET GROUPES
    # ==========================================

    def get_user(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)

    def get_user_profile(self, user_id: str) -> UserProfile:
        if user_id not in self.user_profiles:
            user = self.get_user(user_id)
            name = user.name if user else "Utilisateur"
            self.user_profiles[user_id] = UserProfile(id=user_id, name=name)
        return self.user_profiles[user_id]

    @property
    def active_members(self) -> Dict[str, User]:
        """Retourne le dictionnaire des membres du groupe actif."""
        group = self.groups.get(self.active_group_id)
        if not group:
            return {"u1": self.users["u1"]}
        return {uid: self.users[uid] for uid in group.members if uid in self.users}

    def get_available_contacts(self, group_id: Optional[str] = None) -> List[User]:
        """Retourne les utilisateurs qui ne sont pas encore dans le groupe donné."""
        target_group_id = group_id or self.active_group_id
        group = self.groups.get(target_group_id)
        if not group:
            return list(self.users.values())
        return [u for uid, u in self.users.items() if uid not in group.members]

    def add_member_to_group(self, user_id: str, group_id: Optional[str] = None) -> bool:
        """Ajoute un utilisateur à un groupe."""
        target_group_id = group_id or self.active_group_id
        group = self.groups.get(target_group_id)
        if group and user_id in self.users and user_id not in group.members:
            group.members.append(user_id)
            return True
        return False

    def create_group(self, name: str, member_ids: List[str], description: str = "", icon: str = "👥") -> SharedGroup:
        """Crée un nouveau groupe de compte partagé."""
        new_id = f"group_{uuid.uuid4().hex[:6]}"
        # Toujours inclure l'utilisateur principal
        final_members = list(set([self.primary_user_id] + member_ids))
        new_group = SharedGroup(
            id=new_id,
            name=name,
            description=description,
            members=final_members,
            icon=icon
        )
        self.groups[new_id] = new_group
        self.active_group_id = new_id
        return new_group

    def switch_active_group(self, group_id: str):
        if group_id in self.groups:
            self.active_group_id = group_id

    # ==========================================
    # MOTEUR DE CATÉGORISATION INTELLIGENTE
    # ==========================================

    def categorize_transaction(self, merchant: str, amount: float) -> Tuple[str, str]:
        """
        Détermine automatiquement la catégorie et sous-catégorie d'une dépense.
        Supporte les libellés bancaires réalistes (ex: 'CB CARREFOUR PARIS 05', 'VIR SEPA SALAIRE THALES').
        Retourne (catégorie, sous_catégorie).
        """
        m_lower = merchant.lower()
        
        # 1. Revenus et Aides
        if amount < 0 or any(kw in m_lower for kw in ["salaire", "bourse", "apl", "caf", "virement parents", "remboursement", "remb", "thales", "paie"]):
            if "apl" in m_lower or "caf" in m_lower:
                return "Revenus & Aides", "Aides Publiques (CAF / APL)"
            elif "salaire" in m_lower or "alternance" in m_lower or "thales" in m_lower or "paie" in m_lower:
                return "Revenus & Aides", "Rémunération / Salaire"
            elif "bourse" in m_lower:
                return "Revenus & Aides", "Bourses d'études"
            elif "remboursement" in m_lower or "remb" in m_lower or "xprojets" in m_lower:
                return "Revenus & Aides", "Remboursements & Notes de frais"
            else:
                return "Revenus & Aides", "Virements reçus"
                
        # 2. Logement & Charges
        if any(kw in m_lower for kw in ["loyer", "edf", "engie", "electricite", "électricité", "eau", "assurance hab", "immobilier"]):
            if "loyer" in m_lower or "immobilier" in m_lower:
                return "Logement & Charges", "Loyer"
            elif "edf" in m_lower or "engie" in m_lower or "electricite" in m_lower:
                return "Logement & Charges", "Électricité & Gaz"
            else:
                return "Logement & Charges", "Charges & Assurance"

        # 3. Abonnements & Services Numériques
        if any(kw in m_lower for kw in ["spotify", "netflix", "internet", "freebox", "free telecom", "orange", "bouygues", "sfr", "apple", "prime", "chatgpt", "icloud"]):
            if "internet" in m_lower or any(f in m_lower for f in ["freebox", "free telecom", "orange", "sfr", "bouygues"]):
                return "Abonnements & Services", "Box Internet & Télécoms"
            else:
                return "Abonnements & Services", "Streaming & Musique"

        # 4. Alimentation & Supermarché
        if any(kw in m_lower for kw in ["carrefour", "monoprix", "franprix", "lidl", "auchan", "leclerc", "boulangerie", "paul", "brioche", "biocoop", "landemaine", "naturalia", "intermarche", "intermarché"]):
            if any(b in m_lower for b in ["boulangerie", "paul", "brioche", "landemaine"]):
                return "Alimentation", "Boulangerie & Pause Déjeuner"
            else:
                return "Alimentation", "Courses & Supermarché"

        # 5. Sorties, Loisirs & Restauration
        if any(kw in m_lower for kw in ["deliveroo", "uber eats", "restaurant", "triskell", "bar", "nelson", "cinéma", "cinema", "ugc", "pathe", "pathé", "fnac", "zara", "apm monaco", "fast food", "mcdo", "burger king", "bistrot", "brasserie", "decathlon", "sephora"]):
            if "deliveroo" in m_lower or "uber eats" in m_lower:
                return "Sorties & Loisirs", "Livraison de repas"
            elif any(r in m_lower for r in ["restaurant", "triskell", "bar", "nelson", "bistrot", "brasserie"]):
                return "Sorties & Loisirs", "Restaurants & Sorties"
            elif any(c in m_lower for c in ["cinéma", "cinema", "ugc", "pathe", "pathé", "fnac"]):
                return "Sorties & Loisirs", "Culture & Électronique"
            elif any(s in m_lower for s in ["zara", "apm", "decathlon", "sephora"]):
                return "Sorties & Loisirs", "Shopping & Mode"
            else:
                return "Sorties & Loisirs", "Loisirs divers"

        # 6. Transports
        if any(kw in m_lower for kw in ["ratp", "navigo", "sncf", "train", "uber", "bolt", "velib", "lime", "dott"]):
            return "Transports", "Mobilité & Transports"

        # 7. Santé & Pharmacie
        if any(kw in m_lower for kw in ["pharmacie", "doctolib", "medecin", "dentiste"]):
            return "Autre", "Santé & Pharmacie"

        return "Autre", "Dépenses courantes"

    # ==========================================
    # INGESTION DES TRANSACTIONS
    # ==========================================

    def process_transaction_file(self, file_obj, user_id: str, file_type: str) -> int:
        """
        Ingère un CSV ou Excel, nettoie les données et enrichit avec la catégorisation.
        """
        if file_type == "csv":
            try:
                df = pd.read_csv(file_obj, encoding="utf-8")
            except UnicodeDecodeError:
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
                df = pd.read_csv(file_obj, encoding="latin-1")
        else:
            df = pd.read_excel(file_obj)

        df['date'] = pd.to_datetime(df['date'])
        if 'shared_account_id' in df.columns:
            df['shared_account_id'] = df['shared_account_id'].replace({'none': None, '': None}).where(pd.notnull(df['shared_account_id']), None)
        else:
            df['shared_account_id'] = None

        new_transactions = []
        for _, row in df.iterrows():
            amt = float(row['amount'])
            merchant = str(row['merchant'])
            cat, subcat = self.categorize_transaction(merchant, amt)
            
            tx = Transaction(
                id=str(uuid.uuid4())[:8],
                user_id=user_id,
                merchant=merchant,
                amount=amt,
                method=str(row.get('method', 'carte')),
                date=row['date'].to_pydatetime(),
                shared_account_id=row['shared_account_id'],
                category=cat,
                subcategory=subcat
            )
            new_transactions.append(tx)
        
        self.transactions.extend(new_transactions)
        return len(new_transactions)

    # ==========================================
    # COMPTE PARTAGÉ / TRICOUNT INTEGRE
    # ==========================================

    def get_shared_transactions(self, group_id: Optional[str] = None) -> List[Transaction]:
        """Récupère les transactions associées au groupe spécifié (ou groupe actif)."""
        target_group = group_id or self.active_group_id
        return [tx for tx in self.transactions if tx.shared_account_id == target_group]

    def add_direct_expense(
        self,
        merchant: str,
        amount: float,
        payer_id: str,
        split_details: Dict[str, float],
        date: Optional[datetime] = None,
        group_id: Optional[str] = None,
        note: str = ""
    ) -> Transaction:
        """Ajoute une dépense directe saisie manuellement dans le groupe partagé."""
        target_group = group_id or self.active_group_id
        tx_date = date #or datetime.now()
        cat, subcat = self.categorize_transaction(merchant, amount)
        
        tx = Transaction(
            id=str(uuid.uuid4())[:8],
            user_id=payer_id,
            merchant=merchant,
            amount=abs(amount),
            method="compte partagé",
            date=tx_date,
            shared_account_id=target_group,
            split_details=split_details,
            category=cat,
            subcategory=subcat,
            is_settlement=False,
            note=note
        )
        self.transactions.append(tx)
        return tx

    def share_transaction(self, tx_id: str, split_details: Dict[str, float], group_id: Optional[str] = None):
        """Affecte une transaction existante au compte partagé."""
        target_group = group_id or self.active_group_id
        for tx in self.transactions:
            if tx.id == tx_id:
                tx.shared_account_id = target_group
                tx.split_details = split_details
                break

    def unshare_transaction(self, tx_id: str):
        """Retire une transaction du compte partagé."""
        for tx in self.transactions:
            if tx.id == tx_id:
                tx.shared_account_id = None
                tx.split_details = {}
                break

    def calculate_balances(self, group_id: Optional[str] = None) -> Dict[str, float]:
        """
        Calcule la balance nette de chaque membre dans le groupe.
        > 0 : on lui doit de l'argent (créancier)
        < 0 : il doit de l'argent (débiteur)
        Prend en compte les dépenses standard et les virements instantanés de remboursement.
        """
        target_group = group_id or self.active_group_id
        group = self.groups.get(target_group)
        if not group or not group.members:
            return {}

        shared_txs = self.get_shared_transactions(target_group)
        balances = {uid: 0.0 for uid in group.members}

        for tx in shared_txs:
            payer_id = tx.user_id
            
            # Cas 1 : Virement de remboursement entre deux membres
            if tx.is_settlement:
                # Le payeur a remboursé sa dette (crédité dans la balance pour compenser sa dette)
                if payer_id in balances:
                    balances[payer_id] += tx.amount
                # Le bénéficiaire a reçu son remboursement (débité dans la balance pour réduire son crédit)
                for beneficiary_id, share in tx.split_details.items():
                    if beneficiary_id in balances:
                        balances[beneficiary_id] -= share
                continue

            # Cas 2 : Dépense partagée classique
            # Le payeur est crédité du montant total qu'il a avancé
            if payer_id in balances:
                balances[payer_id] += tx.amount

            # Déduction de la part de chacun
            if tx.split_details:
                for uid, share in tx.split_details.items():
                    if uid in balances:
                        balances[uid] -= share
            else:
                # Répartition équitable par défaut entre tous les membres du groupe
                default_share = tx.amount / len(group.members)
                for uid in group.members:
                    balances[uid] -= default_share

        return balances

    def optimize_transfers(self, net_balances: Dict[str, float]) -> List[Tuple[str, str, float, str, str]]:
        """
        Minimise le nombre de transactions pour équilibrer les comptes.
        Retourne une liste de tuples :
        (Nom_Débiteur, Nom_Créancier, Montant, ID_Débiteur, ID_Créancier)
        """
        creditors = [[uid, bal] for uid, bal in net_balances.items() if bal > 0.01]
        debtors = [[uid, -bal] for uid, bal in net_balances.items() if bal < -0.01]

        creditors.sort(key=lambda x: x[1], reverse=True)
        debtors.sort(key=lambda x: x[1], reverse=True)

        transfers = []
        i, j = 0, 0

        while i < len(debtors) and j < len(creditors):
            d_id, d_amt = debtors[i]
            c_id, c_amt = creditors[j]
            amount = round(min(d_amt, c_amt), 2)

            d_name = self.users[d_id].name if d_id in self.users else d_id
            c_name = self.users[c_id].name if c_id in self.users else c_id

            transfers.append((d_name, c_name, amount, d_id, c_id))

            debtors[i][1] -= amount
            creditors[j][1] -= amount

            if debtors[i][1] < 0.01:
                i += 1
            if creditors[j][1] < 0.01:
                j += 1

        return transfers

    def execute_instant_settlement(
        self,
        from_user_id: str,
        to_user_id: str,
        amount: float,
        group_id: Optional[str] = None
    ) -> Transaction:
        """
        FONCTIONNALITÉ INNOVANTE :
        Exécute un virement instantané directement dans l'application bancaire pour solder une dette.
        - Crée l'écriture de compensation dans le groupe partagé.
        - Met à jour le solde du compte personnel de Paul si impliqué.
        - Ajoute une transaction bancaire officielle dans l'historique du compte.
        """
        target_group = group_id or self.active_group_id
        group = self.groups.get(target_group)
        group_name = group.name if group else "Groupe"
        
        now = datetime.now()
        settlement_id = f"virement_{uuid.uuid4().hex[:6]}"
        to_name = self.users.get(to_user_id, User(id=to_user_id, name="Bénéficiaire")).name
        from_name = self.users.get(from_user_id, User(id=from_user_id, name="Payeur")).name

        # 1. Écriture de règlement dans le groupe partagé
        shared_settlement_tx = Transaction(
            id=settlement_id,
            user_id=from_user_id,
            merchant=f"⚡ Virement Instantané : {from_name} ➔ {to_name}",
            amount=amount,
            method="virement instantané",
            date=now,
            shared_account_id=target_group,
            split_details={to_user_id: amount},
            category="Virement Interne",
            subcategory="Remboursement de dette",
            is_settlement=True,
            note=f"Remboursement automatique - {group_name}"
        )
        self.transactions.append(shared_settlement_tx)

        # 2. Si Paul est l'émetteur, déduire de son solde bancaire et enregistrer la ligne personnelle
        if from_user_id == self.primary_user_id:
            self.account_balance -= amount
            personal_debit_tx = Transaction(
                id=f"tx_{uuid.uuid4().hex[:6]}",
                user_id=self.primary_user_id,
                merchant=f"Virement instantané émis vers {to_name} ({group_name})",
                amount=amount,
                method="virement instantané",
                date=now,
                category="Virement Émis",
                subcategory="Remboursement groupe",
                is_settlement=False
            )
            self.transactions.append(personal_debit_tx)

        # 3. Si Paul est le destinataire, créditer son solde bancaire
        elif to_user_id == self.primary_user_id:
            self.account_balance += amount
            personal_credit_tx = Transaction(
                id=f"tx_{uuid.uuid4().hex[:6]}",
                user_id=self.primary_user_id,
                merchant=f"Virement instantané reçu de {from_name} ({group_name})",
                amount=-amount, # Valeur négative dans le format du CSV pour un crédit
                method="virement instantané",
                date=now,
                category="Revenus & Aides",
                subcategory="Remboursements",
                is_settlement=False
            )
            self.transactions.append(personal_credit_tx)

        return shared_settlement_tx

    # ==========================================
    # OUTIL DE BUDGÉTISATION INTELLIGENTE
    # ==========================================

    def analyze_monthly_budget(self, user_id: str) -> Dict:
        """
        Analyse détaillée du budget :
        - Mois glissant (30 jours) : base d'analyse de fond pour le chatbot et comparaison aux pairs.
        - Mois en cours (ex: du 1er au 11) : indicateur des dépenses actuelles et reste à vivre de fin de mois.
        """
        user_txs = [tx for tx in self.transactions if tx.user_id == user_id and not tx.is_settlement]
        profile = self.get_user_profile(user_id)
        baseline_income = profile.monthly_net_income
        fixed_categories = ["Logement & Charges", "Abonnements & Services"]

        if not user_txs:
            return {
                "income": baseline_income,
                "baseline_income": baseline_income,
                "rolling_income": baseline_income,
                "rolling_spent": 0.0,
                "rolling_fixed": 0.0,
                "rolling_variable": 0.0,
                "rolling_remaining": baseline_income,
                "rolling_label": "Mois glissant (30 jours)",
                "calendar_spent": 0.0,
                "calendar_remaining": baseline_income,
                "calendar_projection": 0.0,
                "calendar_days_passed": 1,
                "calendar_total_days": 30,
                "calendar_label": "Mois en cours",
                "total_spent": 0.0,
                "fixed_expenses": 0.0,
                "variable_expenses": 0.0,
                "remaining": baseline_income,
                "projection": 0.0,
                "days_passed": 1,
                "total_days": 30,
                "ceiling": baseline_income,
                "status": "safe",
                "is_over_budget": False
            }

        # Date de référence : dernière transaction enregistrée (ex: 11 Septembre 2026)
        max_date = max(tx.date for tx in user_txs)

        # ----------------------------------------------------
        # 1. MOIS GLISSANT SUR 30 JOURS (ex: 11 août au 11 sept)
        # ----------------------------------------------------
        rolling_start = max_date - timedelta(days=30)
        rolling_txs = [tx for tx in user_txs if rolling_start <= tx.date <= max_date]
        
        rolling_income_detected = sum(abs(tx.amount) for tx in rolling_txs if tx.category == "Revenus & Aides")
        rolling_income = max(rolling_income_detected, baseline_income)

        rolling_expense_txs = [tx for tx in rolling_txs if tx.category != "Revenus & Aides" and tx.amount > 0]
        rolling_fixed = sum(tx.amount for tx in rolling_expense_txs if tx.category in fixed_categories)
        rolling_variable = sum(tx.amount for tx in rolling_expense_txs if tx.category not in fixed_categories)
        rolling_total_spent = rolling_fixed + rolling_variable
        rolling_remaining = max(0.0, rolling_income - rolling_total_spent)
        rolling_label = f"Mois glissant (du {rolling_start.strftime('%d/%m')} au {max_date.strftime('%d/%m/%Y')})"

        # ----------------------------------------------------
        # 2. MOIS CALENDAIRE EN COURS (ex: 1er au 11 septembre)
        # ----------------------------------------------------
        calendar_txs = [
            tx for tx in user_txs
            if tx.date.year == max_date.year and tx.date.month == max_date.month
        ]
        calendar_expense_txs = [tx for tx in calendar_txs if tx.category != "Revenus & Aides" and tx.amount > 0]
        calendar_spent = sum(tx.amount for tx in calendar_expense_txs)
        calendar_remaining = max(0.0, baseline_income - calendar_spent)
        calendar_days_passed = max_date.day
        calendar_total_days = 30

        calendar_fixed = sum(tx.amount for tx in calendar_expense_txs if tx.category in fixed_categories)
        calendar_variable = sum(tx.amount for tx in calendar_expense_txs if tx.category not in fixed_categories)
        daily_rate = calendar_variable / max(1, calendar_days_passed)
        calendar_projection = calendar_fixed + (daily_rate * calendar_total_days)
        calendar_label = max_date.strftime("%B %Y").capitalize()

        # Évaluation de la santé budgétaire (dépassement)
        is_over_budget = (rolling_total_spent > rolling_income) or (calendar_projection > baseline_income * 1.05) or (calendar_spent / baseline_income > (calendar_days_passed / calendar_total_days) * 1.35)
        status = "danger" if is_over_budget else ("warning" if (calendar_spent / baseline_income > 0.8) else "safe")

        return {
            # Mois glissant (30 jours)
            "income": rolling_income,
            "baseline_income": baseline_income,
            "rolling_income": rolling_income,
            "rolling_spent": rolling_total_spent,
            "rolling_fixed": rolling_fixed,
            "rolling_variable": rolling_variable,
            "rolling_remaining": rolling_remaining,
            "rolling_label": rolling_label,
            "rolling_period_days": 30,
            
            # Mois calendaire en cours
            "calendar_spent": calendar_spent,
            "calendar_remaining": calendar_remaining,
            "calendar_projection": calendar_projection,
            "calendar_days_passed": calendar_days_passed,
            "calendar_total_days": calendar_total_days,
            "calendar_label": calendar_label,
            "current_month_label": calendar_label,
            
            # Clés de compatibilité
            "total_spent": rolling_total_spent,
            "fixed_expenses": rolling_fixed,
            "variable_expenses": rolling_variable,
            "remaining": calendar_remaining,
            "projection": calendar_projection,
            "days_passed": calendar_days_passed,
            "total_days": calendar_total_days,
            "ceiling": baseline_income,
            "status": status,
            "is_over_budget": is_over_budget
        }

    def load_peers_benchmark(self, filepath: Optional[str] = None) -> Dict[str, Dict]:
        """
        Charge dynamiquement les benchmarks statistiques des pairs depuis un fichier externe JSON ou CSV.
        Contient pour chaque catégorie :
        - top_10_economes (p10)
        - top_30_economes (p30)
        - moyenne
        - top_30_depensiers (p70)
        - top_10_depensiers (p90)
        """
        json_path = filepath or os.path.join("data", "benchmark_peers.json")
        csv_path = filepath or os.path.join("data", "benchmark_peers.csv")

        # 1. Essai de chargement depuis JSON
        if os.path.exists(json_path) and json_path.endswith(".json"):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and data:
                        return data
            except Exception as e:
                print(f"[Backend] Erreur de lecture JSON {json_path}: {e}")

        # 2. Essai de chargement depuis CSV
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path, encoding="utf-8")
                res = {}
                for _, row in df.iterrows():
                    cat = str(row["category"]).strip()
                    res[cat] = {
                        "top_10_economes": float(row.get("top_10_economes", 50.0)),
                        "top_30_economes": float(row.get("top_30_economes", 100.0)),
                        "moyenne": float(row.get("moyenne", 150.0)),
                        "top_30_depensiers": float(row.get("top_30_depensiers", 200.0)),
                        "top_10_depensiers": float(row.get("top_10_depensiers", 300.0)),
                        "benchmark_title": str(row.get("benchmark_title", cat)),
                        "unit": "€/mois",
                        "comment_eco": str(row.get("comment_eco", "Dépenses bien maîtrisées.")),
                        "comment_avg": str(row.get("comment_avg", "Conforme à la moyenne.")),
                        "comment_high": str(row.get("comment_high", "Dépenses élevées par rapport aux pairs."))
                    }
                if res:
                    return res
            except Exception as e:
                print(f"[Backend] Erreur de lecture CSV {csv_path}: {e}")

        # 3. Données de secours par défaut si aucun fichier n'est trouvé
        fallback = {
            "Logement & Charges": {
                "top_10_economes": 450.0, "top_30_economes": 580.0, "moyenne": 750.0,
                "top_30_depensiers": 850.0, "top_10_depensiers": 980.0,
                "benchmark_title": "Colocation / Studio IDF", "unit": "€/mois",
                "comment_eco": "Loyer et charges très bien maîtrisés en colocation.",
                "comment_avg": "Loyer conforme au coût moyen étudiant en Île-de-France.",
                "comment_high": "Part de loyer élevée par rapport aux étudiants parisiens."
            },
            "Alimentation": {
                "top_10_economes": 160.0, "top_30_economes": 220.0, "moyenne": 280.0,
                "top_30_depensiers": 350.0, "top_10_depensiers": 450.0,
                "benchmark_title": "Courses & Supermarché", "unit": "€/mois",
                "comment_eco": "Budget alimentaire très rigoureux (cuisine maison, hard-discount).",
                "comment_avg": "Panier alimentaire conforme à la moyenne étudiante.",
                "comment_high": "Dépenses alimentaires élevées (achats d'appoint fréquents)."
            },
            "Sorties & Loisirs": {
                "top_10_economes": 50.0, "top_30_economes": 100.0, "moyenne": 160.0,
                "top_30_depensiers": 230.0, "top_10_depensiers": 320.0,
                "benchmark_title": "Bars, Restos & Livraisons", "unit": "€/mois",
                "comment_eco": "Dépenses de loisirs très modérées.",
                "comment_avg": "Niveau de sorties conforme à la moyenne étudiante.",
                "comment_high": "Poste au-dessus de la majorité des pairs (commandes repas & shopping)."
            },
            "Transports": {
                "top_10_economes": 20.0, "top_30_economes": 35.0, "moyenne": 42.0,
                "top_30_depensiers": 65.0, "top_10_depensiers": 95.0,
                "benchmark_title": "Navigo & Mobilité", "unit": "€/mois",
                "comment_eco": "Usage exclusif des mobilités douces ou vélo.",
                "comment_avg": "Navigo avec prise en charge employeur 50%.",
                "comment_high": "Nombreux trajets VTC / taxis en complément des transports."
            },
            "Abonnements & Services": {
                "top_10_economes": 15.0, "top_30_economes": 25.0, "moyenne": 35.0,
                "top_30_depensiers": 55.0, "top_10_depensiers": 80.0,
                "benchmark_title": "Forfaits & Abonnements", "unit": "€/mois",
                "comment_eco": "Abonnements réduits au strict nécessaire.",
                "comment_avg": "Forfait mobile et un service de streaming musical.",
                "comment_high": "Cumul important d'abonnements numériques et audiovisuels."
            },
            "Autre": {
                "top_10_economes": 20.0, "top_30_economes": 40.0, "moyenne": 60.0,
                "top_30_depensiers": 90.0, "top_10_depensiers": 140.0,
                "benchmark_title": "Dépenses diverses & Imprévus", "unit": "€/mois",
                "comment_eco": "Imprévus quasi nuls.",
                "comment_avg": "Dépenses diverses courantes sous contrôle.",
                "comment_high": "Volume important de dépenses imprévues ou shopping."
            }
        }
        return fallback

    def get_category_breakdown(self, user_id: str, window_days: int = 30) -> Tuple[Dict[str, float], Dict[str, Dict], Dict[str, Dict[str, float]]]:
        """
        Calcule la ventilation des dépenses par catégorie et sous-catégorie sur les 30 derniers jours,
        et fournit la comparaison dynamique avec les pairs basée sur le fichier externe multi-seuils :
        - Top 10% plus économes (p10)
        - Top 30% plus économes (p30)
        - Moyenne
        - Top 30% moins économes (p70)
        - Top 10% moins économes (p90)
        """
        user_txs = [tx for tx in self.transactions if tx.user_id == user_id and not tx.is_settlement]
        if not user_txs:
            return {}, {}, {}

        max_date = max(tx.date for tx in user_txs)
        start_date = max_date - timedelta(days=window_days)

        recent_txs = [
            tx for tx in user_txs
            if start_date <= tx.date <= max_date and tx.category != "Revenus & Aides" and tx.amount > 0
        ]

        categories: Dict[str, float] = {}
        subcategories: Dict[str, Dict[str, float]] = {}

        for tx in recent_txs:
            cat = tx.category
            subcat = tx.subcategory
            categories[cat] = categories.get(cat, 0.0) + tx.amount
            if cat not in subcategories:
                subcategories[cat] = {}
            subcategories[cat][subcat] = subcategories.get(subcat, 0.0) + tx.amount

        # S'assurer que les données de référence sont chargées
        if not hasattr(self, "peers_benchmark_data") or not self.peers_benchmark_data:
            self.peers_benchmark_data = self.load_peers_benchmark()

        peers_result: Dict[str, Dict] = {}

        # Évaluer toutes les catégories de référence et celles présentes dans les transactions
        all_cats = list(dict.fromkeys(list(self.peers_benchmark_data.keys()) + list(categories.keys())))

        for cat in all_cats:
            spent = categories.get(cat, 0.0)
            b = self.peers_benchmark_data.get(cat, {
                "top_10_economes": 30.0,
                "top_30_economes": 50.0,
                "moyenne": 80.0,
                "top_30_depensiers": 120.0,
                "top_10_depensiers": 180.0,
                "benchmark_title": cat,
                "unit": "€/mois",
                "comment_eco": "Dépenses bien maîtrisées.",
                "comment_avg": "Dépenses dans la moyenne.",
                "comment_high": "Dépenses élevées."
            })

            avg = float(b.get("moyenne", 100.0))
            p10 = float(b.get("top_10_economes", avg * 0.5))
            p30 = float(b.get("top_30_economes", avg * 0.75))
            p70 = float(b.get("top_30_depensiers", avg * 1.35))
            p90 = float(b.get("top_10_depensiers", avg * 1.8))

            # Classification dynamique par tranche statistique et positionnement relatif
            if spent <= p10:
                tier = "top_10_eco"
                status = "Top 10% plus économe 🏆"
                relative_position = "Vous faites partie du top 10% des plus économes (vous dépensez moins que 90% de vos pairs)"
                color = "#1B5E20"
                tier_idx = 1
                comment = b.get("comment_eco", "Gestion des dépenses remarquablement économe.")
            elif spent <= p30:
                tier = "top_30_eco"
                status = "Top 30% économe 🟢"
                relative_position = "Vous faites partie du top 30% des plus économes (vous dépensez moins que 70% de vos pairs)"
                color = "#2E8B57"
                tier_idx = 2
                comment = b.get("comment_eco", "Dépenses bien maîtrisées en-dessous de la moyenne.")
            elif spent <= p70:
                tier = "moyenne"
                status = "Dans la moyenne 👍"
                relative_position = "Vous vous situez dans la moyenne de vos pairs"
                color = "#F39C12"
                tier_idx = 3
                comment = b.get("comment_avg", "Dépenses conformes au panier moyen des pairs.")
            elif spent <= p90:
                tier = "top_30_dep"
                status = "Top 30% moins économe ⚠️"
                relative_position = "Vous dépensez plus que 70% de vos pairs (top 30% des moins économes)"
                color = "#E67E22"
                tier_idx = 4
                comment = b.get("comment_high", "Dépenses supérieures à la majorité des pairs.")
            else:
                tier = "top_10_dep"
                status = "Top 10% moins économe 🚨"
                relative_position = "Vous dépensez plus que 90% de vos pairs (top 10% des moins économes)"
                color = "#D9534F"
                tier_idx = 5
                comment = b.get("comment_high", "Poste de dépense très élevé parmi les 10% les plus dépensiers.")

            delta = spent - avg
            ratio = spent / avg if avg > 0 else 1.0

            peers_result[cat] = {
                "avg": avg,
                "moyenne": avg,
                "top_10_economes": p10,
                "top_30_economes": p30,
                "top_30_depensiers": p70,
                "top_10_depensiers": p90,
                "benchmark_title": b.get("benchmark_title", cat),
                "unit": b.get("unit", "€/mois"),
                "color": color,
                "status": status,
                "relative_position": relative_position,
                "tier": tier,
                "tier_idx": tier_idx,
                "delta": delta,
                "ratio": ratio,
                "comment": comment
            }

        return categories, peers_result, subcategories

    def load_public_aids(self, country: Optional[str] = None) -> Any:
        """
        Charge le catalogue neutre de référence des dispositifs d'aides publiques
        (France, Espagne, Allemagne, Pologne).
        """
        json_path = os.path.join("data", "public_aids_reference.json")
        if not os.path.exists(json_path):
            return []
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if country:
                country_key = country.strip().lower()
                for c_name, aids in data.items():
                    if c_name.lower() == country_key:
                        return aids
                # Fallback sur France si pays non trouvé dans le dictionnaire
                return data.get("France", [])
            return data
        except Exception as e:
            print(f"[Backend] Erreur chargement aides publiques : {e}")
            return []

    def get_llm_financial_context(self, user_id: str) -> Dict:
        """
        Extrait un contexte bancaire enrichi, factuel et neutre pour le LLM :
        - Flux entrants détectés (libellés réels, montants, sans présumer des aides manquantes)
        - Double échelle : Mois glissant 30 jours (pour l'analyse de fond) + Mois en cours
        - Catégorie de dépenses au plus fort écart avec les pairs et toutes les sous-catégories
        - Positionnement relatif précis par rapport aux pairs
        - Postes bien gérés sous contrôle
        - Statut de dépassement budgétaire (is_over_budget)
        """
        budget = self.analyze_monthly_budget(user_id)
        categories, peers, subcategories = self.get_category_breakdown(user_id, window_days=30)
        user_txs = [tx for tx in self.transactions if tx.user_id == user_id and not tx.is_settlement]
        
        # 1. Détection des flux de revenus / entrées d'argent réelles sur les 30 derniers jours
        max_date = max((tx.date for tx in user_txs), default=datetime.now())
        rolling_start = max_date - timedelta(days=30)
        
        detected_incomes = []
        for tx in user_txs:
            if rolling_start <= tx.date <= max_date and (tx.amount < 0 or tx.category == "Revenus & Aides"):
                amt_abs = abs(tx.amount)
                label = f"{tx.merchant} ({amt_abs:.2f} € le {tx.date.strftime('%d/%m')})"
                if label not in detected_incomes:
                    detected_incomes.append(label)

        # 2. Détection des récurrences / abonnements identifiés
        detected_subscriptions = []
        for tx in user_txs:
            if tx.category in ["Abonnements & Services", "Logement & Charges"]:
                label = f"{tx.merchant} ({tx.amount:.2f} €)"
                if label not in detected_subscriptions and tx.amount > 0:
                    detected_subscriptions.append(label)

        # Plus grosse dépense ponctuelle
        expense_txs = [tx for tx in user_txs if tx.amount > 0 and tx.category != "Revenus & Aides"]
        largest_expense = max(expense_txs, key=lambda t: t.amount) if expense_txs else None
        largest_expense_str = f"{largest_expense.merchant} ({largest_expense.amount:.2f} € le {largest_expense.date.strftime('%d/%m')})" if largest_expense else "Aucune"

        # 3. Identifier la catégorie avec le PLUS FORT ÉCART POSITIF par rapport aux pairs
        max_gap_cat = None
        max_gap_val = -999999.0
        for cat, spent in categories.items():
            peer_avg = peers.get(cat, {}).get("avg", 0.0)
            gap = spent - peer_avg
            if gap > max_gap_val:
                max_gap_val = gap
                max_gap_cat = cat

        critical_subcategories = {}
        if max_gap_cat and max_gap_cat in subcategories:
            critical_subcategories = subcategories[max_gap_cat]

        max_gap_info = peers.get(max_gap_cat, {})

        # 4. Identifier les éléments bien gérés (dépenses inférieures ou égales aux pairs)
        well_managed = []
        for cat, p_info in peers.items():
            spent = categories.get(cat, 0.0)
            avg = p_info.get("avg", 0.0)
            rel_pos = p_info.get("relative_position", p_info.get("status", ""))
            if spent <= avg and spent > 0:
                diff = avg - spent
                well_managed.append(f"{cat} : {spent:.0f} € ({rel_pos})")
            elif cat not in categories:
                well_managed.append(f"{cat} : 0 € (Moyenne pairs : {avg:.0f} €)")

        # Résumé du positionnement relatif par rapport aux pairs
        peer_comparison_summary = []
        for cat, p_info in peers.items():
            if cat in categories:
                spent = categories[cat]
                peer_comparison_summary.append(
                    f"- {cat} : {spent:.2f} € | {p_info['relative_position']} (Moyenne pairs : {p_info['avg']:.0f} €)"
                )

        return {
            "budget": budget,
            "categories": categories,
            "subcategories": subcategories,
            "peers": peers,
            "max_gap_category": max_gap_cat,
            "max_gap_value": max_gap_val,
            "max_gap_tier": max_gap_info.get("relative_position", max_gap_info.get("status", "")),
            "max_gap_threshold_p90": max_gap_info.get("top_10_depensiers", 0.0),
            "critical_subcategories": critical_subcategories,
            "well_managed_categories": well_managed,
            "peer_comparison_summary": peer_comparison_summary,
            "detected_incomes": detected_incomes,
            "subscriptions": detected_subscriptions[:5],
            "largest_expense": largest_expense_str,
            "total_transactions_count": len(user_txs),
            "is_over_budget": budget.get("is_over_budget", False),
            "targeted_aids": self.get_targeted_public_aids(user_id)
        }

    def calculate_health_score(self, user_id: str) -> Dict[str, Any]:
        """
        Calcule instantanément (<5ms) le Score de Santé Budgétaire (/100)
        et la décomposition sur 3 piliers stratégiques :
        1. Équilibre & Trésorerie (40 pts)
        2. Structure Budgétaire / Règle 50-30-20 (30 pts)
        3. Positionnement vs Pairs (30 pts)
        """
        profile = self.get_user_profile(user_id)
        budget = self.analyze_monthly_budget(user_id)
        categories, peers, subcategories = self.get_category_breakdown(user_id, window_days=30)
        
        rolling_income = budget.get("rolling_income", profile.monthly_net_income) or profile.monthly_net_income or 1200.0
        rolling_spent = budget.get("rolling_spent", 0.0)
        rolling_fixed = budget.get("rolling_fixed", 0.0)
        rolling_variable = budget.get("rolling_variable", 0.0)
        rolling_remaining = budget.get("rolling_remaining", 0.0)
        is_over_budget = budget.get("is_over_budget", False)
        
        # --- Pilier 1 : Équilibre & Trésorerie (40 pts) ---
        expense_ratio = (rolling_spent / rolling_income) if rolling_income > 0 else 1.0
        if is_over_budget or rolling_spent > rolling_income:
            deficit = max(0.0, rolling_spent - rolling_income)
            deficit_str = f"déficit de {deficit:.0f} € sur 30j" if deficit > 0 else "dépenses supérieures aux rentrées"
            p1_score = max(5, int(30/expense_ratio))
            p1_verdict = f"Budget sous tension : {deficit_str}"
            p1_status = "warning"
        elif expense_ratio <= 0.75:
            p1_score = 40
            p1_verdict = f"Trésorerie excellente : {rolling_remaining:.0f} € de marge d'épargne"
            p1_status = "safe"
        elif expense_ratio <= 0.90:
            p1_score = 35
            p1_verdict = f"Budget équilibré : {rolling_remaining:.0f} € de reste à vivre"
            p1_status = "safe"
        elif expense_ratio <= 1.0:
            p1_score = 30
            p1_verdict = f"Marge étroite : {rolling_remaining:.0f} € disponibles"
            p1_status = "warning"
        else:
            p1_score = 30
            p1_verdict = "Équilibre fragile : budget presque intégralement consommé"
            p1_status = "warning"

        # --- Pilier 2 : Structure Budgétaire / Règle 50-30-20 (30 pts) ---
        fixed_ratio = (rolling_fixed / rolling_income) if rolling_income > 0 else 0.5
        if fixed_ratio <= 0.50:
            p2_score = 30
            p2_verdict = f"Charges fixes sous contrôle ({fixed_ratio * 100:.0f}% des revenus)"
            p2_status = "safe"
        elif fixed_ratio <= 0.60:
            p2_score = 23
            p2_verdict = f"Charges fixes modérées ({fixed_ratio * 100:.0f}% des revenus)"
            p2_status = "safe"
        elif fixed_ratio <= 0.70:
            p2_score = 15
            p2_verdict = f"Poids important des fixes ({fixed_ratio * 100:.0f}% des revenus)"
            p2_status = "warning"
        else:
            p2_score = 8
            p2_verdict = f"Charges fixes prépondérantes ({fixed_ratio * 100:.0f}% des revenus)"
            p2_status = "danger"

        # --- Pilier 3 : Positionnement vs Pairs (30 pts) ---
        critical_count = 0
        moderate_count = 0
        max_gap_cat = None
        max_gap_val = 0.0

        for cat, spent in categories.items():
            if cat in peers:
                avg = peers[cat].get("avg", 0.0)
                p90 = peers[cat].get("top_10_depensiers", avg * 1.5)
                gap = spent - avg
                if gap > max_gap_val:
                    max_gap_val = gap
                    max_gap_cat = cat
                if spent >= p90 or gap >= 100.0:
                    critical_count += 1
                elif gap >= 25.0:
                    moderate_count += 1

        p3_score = max(5, 30 - (critical_count * 10) - (moderate_count * 4))
        if critical_count == 0 and moderate_count == 0:
            p3_verdict = "Dépenses conformes ou plus sobres que la moyenne des pairs"
            p3_status = "safe"
        elif critical_count == 0:
            p3_verdict = f"{moderate_count} poste(s) légèrement au-dessus de la moyenne"
            p3_status = "warning"
        else:
            gap_info = f" (notamment {max_gap_cat} : +{max_gap_val:.0f} €)" if max_gap_cat else ""
            p3_verdict = f"Écart notable avec les pairs{gap_info}"
            p3_status = "danger"

        # --- Score Global /100 ---
        total_score = min(100, max(0, p1_score + p2_score + p3_score))
        if total_score >= 80:
            overall_status = "Excellente santé"
            color = "#2E8B57"
            badge = "🟢 Excellente santé"
            summary = "Vos finances sont saines et pérennes avec une bonne capacité d'épargne."
        elif total_score >= 60:
            overall_status = "Situation équilibrée"
            color = "#D97706"
            badge = "🟡 Situation équilibrée"
            summary = "Trésorerie globalement stable avec des marges d'optimisation identifiées."
        else:
            overall_status = "Vigilance requise"
            color = "#DC2626"
            badge = "🔴 Vigilance requise"
            summary = "Budget sous tension : des arbitrages rapides sont recommandés."

        return {
            "total_score": total_score,
            "status": overall_status,
            "badge": badge,
            "color": color,
            "summary": summary,
            "pillars": {
                "treasury": {
                    "title": "Équilibre Trésorerie",
                    "score": p1_score,
                    "max_score": 40,
                    "verdict": p1_verdict,
                    "status": p1_status,
                    "ratio": round(p1_score / 40, 2)
                },
                "structure": {
                    "title": "Structure 50/30/20",
                    "score": p2_score,
                    "max_score": 30,
                    "verdict": p2_verdict,
                    "status": p2_status,
                    "ratio": round(p2_score / 30, 2)
                },
                "peers": {
                    "title": "Maîtrise vs Pairs",
                    "score": p3_score,
                    "max_score": 30,
                    "verdict": p3_verdict,
                    "status": p3_status,
                    "ratio": round(p3_score / 30, 2)
                }
            }
        }

    def get_targeted_public_aids(self, user_id: str) -> List[Dict]:
        """
        Sélectionne intelligemment les aides publiques les plus pertinentes
        pour le profil de l'utilisateur afin d'alléger le prompt du LLM (~60% de tokens en moins).
        """
        profile = self.get_user_profile(user_id)
        country = getattr(profile, "country", "France")
        all_aids = self.load_public_aids(country)
        if not isinstance(all_aids, list):
            return []

        status_norm = (profile.status + " " + getattr(profile, "job_activity", "")).lower()
        housing_norm = getattr(profile, "housing_type", "").lower()
        has_rent = profile.rent_amount > 0 or "coloc" in housing_norm or "locataire" in housing_norm
        is_young = profile.age <= 30
        is_student_or_apprentice = any(w in status_norm for w in ["alternan", "étudiant", "etudiant", "apprenti"])

        targeted = []
        for aid in all_aids:
            aid_id = aid.get("id", "").lower()
            aid_name = aid.get("name", "").lower()

            if has_rent and any(w in aid_id or w in aid_name for w in ["apl", "alquiler", "wohngeld", "mobili_jeune", "logement"]):
                targeted.append(aid)
            elif any(w in aid_id or w in aid_name for w in ["prime_activite", "activit", "imv", "buergergeld"]):
                targeted.append(aid)
            elif any(w in aid_id or w in aid_name for w in ["lep", "epargne"]):
                targeted.append(aid)
            elif is_student_or_apprentice and any(w in aid_id or w in aid_name for w in ["beca", "bafoeg", "bourse"]):
                targeted.append(aid)

        return targeted if targeted else all_aids[:3]