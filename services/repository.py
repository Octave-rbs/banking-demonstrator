"""
Entrepôt de données en mémoire et ingestion de transactions.
"""

import os
import json
import uuid
import pandas as pd
from typing import Dict, List, Optional, Any
from models import User, UserProfile, SharedGroup, Transaction
from services.categorizer import categorize_transaction


class BankRepository:
    """Gère l'état des données en mémoire, les utilisateurs et les groupes."""

    def __init__(self):
        self.transactions: List[Transaction] = []

        self.users: Dict[str, User] = {
            "u1": User(id="u1", name="Paul", avatar="🧑‍💻"),
            "u2": User(id="u2", name="Emma", avatar="👩‍🎨"),
            "u3": User(id="u3", name="Lucas", avatar="👨‍🎓"),
            "u4": User(id="u4", name="Thomas", avatar="🧑‍🔬"),
            "u5": User(id="u5", name="Arthur", avatar="👨‍🍳")
        }

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

        self.active_group_id: str = "coloc_paris_01"
        self.primary_user_id: str = "u1"
        self.account_balance: float = 2847.32

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
        group = self.groups.get(self.active_group_id)
        if not group:
            return {"u1": self.users["u1"]}
        return {uid: self.users[uid] for uid in group.members if uid in self.users}

    def get_available_contacts(self, group_id: Optional[str] = None) -> List[User]:
        target_group_id = group_id or self.active_group_id
        group = self.groups.get(target_group_id)
        if not group:
            return list(self.users.values())
        return [u for uid, u in self.users.items() if uid not in group.members]

    def add_member_to_group(self, user_id: str, group_id: Optional[str] = None) -> bool:
        target_group_id = group_id or self.active_group_id
        group = self.groups.get(target_group_id)
        if group and user_id in self.users and user_id not in group.members:
            group.members.append(user_id)
            return True
        return False

    def create_group(
        self,
        name: str,
        member_ids: List[str],
        description: str = "",
        icon: str = "👥"
    ) -> SharedGroup:
        new_id = f"group_{uuid.uuid4().hex[:6]}"
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

    def process_transaction_file(self, file_obj, user_id: str, file_type: str) -> int:
        """Ingère et catégorise un CSV ou Excel de relevé bancaire."""
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
            df['shared_account_id'] = (
                df['shared_account_id']
                .replace({'none': None, '': None})
                .where(pd.notnull(df['shared_account_id']), None)
            )
        else:
            df['shared_account_id'] = None

        new_transactions = []
        for _, row in df.iterrows():
            amt = float(row['amount'])
            merchant = str(row['merchant'])
            cat, subcat = categorize_transaction(merchant, amt)

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

    def load_public_aids(self, country: Optional[str] = None) -> Any:
        """Charge le catalogue neutre des aides publiques."""
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
                return data.get("France", [])
            return data
        except Exception as e:
            print(f"[Repository] Erreur chargement aides publiques : {e}")
            return []

    def get_targeted_public_aids(self, user_id: str) -> List[Dict]:
        """Filtre les aides pertinentes pour alléger le contexte LLM."""
        profile = self.get_user_profile(user_id)
        country = getattr(profile, "country", "France")
        all_aids = self.load_public_aids(country)
        if not isinstance(all_aids, list):
            return []

        status_norm = (profile.status + " " + getattr(profile, "job_activity", "")).lower()
        housing_norm = getattr(profile, "housing_type", "").lower()
        has_rent = profile.rent_amount > 0 or "coloc" in housing_norm or "locataire" in housing_norm
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
