from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime

@dataclass
class User:
    id: str
    name: str
    avatar: str = "👤"

@dataclass
class UserProfile:
    id: str
    name: str
    age: int = 22
    family_situation: str = "Célibataire" # Célibataire, En couple, Pacsé(e), Marié(e), Parent solo
    status: str = "Alternant / Étudiant"
    job_activity: str = "Alternant ingénieur en informatique"
    housing_type: str = "Colocation" # Colocation, Locataire seul, Hébergé, Propriétaire
    school_or_company: str = "Polytech & Entreprise Partenaire"
    city: str = "Paris"
    country: str = "France" # Pays de résidence fiscale et bancaire
    monthly_net_income: float = 1200.0
    rent_amount: float = 650.0
    custom_notes: str = "" # Précisions libres transmises au LLM (objectifs, crédits, projet de vie, etc.)

@dataclass
class SharedGroup:
    id: str
    name: str
    description: str = ""
    members: List[str] = field(default_factory=list)  # List of user IDs
    created_at: datetime = field(default_factory=datetime.now)
    icon: str = "🏘️"
    currency: str = "€"

@dataclass
class Transaction:
    id: str
    user_id: str
    merchant: str
    amount: float
    method: str
    date: datetime
    shared_account_id: Optional[str] = None
    split_details: Dict[str, float] = field(default_factory=dict) # {user_id: amount}
    category: str = "Autre"
    subcategory: str = "Général"
    is_settlement: bool = False  # Vrai s'il s'agit d'un virement de remboursement de dette
    split_mode: str = "equal"    # "equal", "custom", "shares"
    note: str = ""