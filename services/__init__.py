"""
Services métier et analytiques bancaires.
Expose la façade unifiée BankBackend pour orchestrer les modules spécialisés.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from models import User, UserProfile, SharedGroup, Transaction
from services.repository import BankRepository
from services.categorizer import categorize_transaction
from services.shared_expenses import (
    split_equally,
    get_shared_transactions,
    add_direct_expense,
    share_transaction,
    unshare_transaction,
    calculate_balances,
    optimize_transfers,
    execute_instant_settlement
)
from services.budget_service import analyze_monthly_budget
from services.benchmark_service import load_peers_benchmark, get_category_breakdown
from services.health_score_service import calculate_health_score


class BankBackend:
    """Façade unifiée des services bancaires du démonstrateur."""

    def __init__(self):
        self.repo = BankRepository()
        self.peers_benchmark_data: Dict[str, Dict] = load_peers_benchmark()

    # Propriétés exposées pour compatibilité directe
    @property
    def transactions(self) -> List[Transaction]:
        return self.repo.transactions

    @property
    def users(self) -> Dict[str, User]:
        return self.repo.users

    @property
    def user_profiles(self) -> Dict[str, UserProfile]:
        return self.repo.user_profiles

    @property
    def groups(self) -> Dict[str, SharedGroup]:
        return self.repo.groups

    @property
    def active_group_id(self) -> str:
        return self.repo.active_group_id

    @active_group_id.setter
    def active_group_id(self, val: str):
        self.repo.active_group_id = val

    @property
    def primary_user_id(self) -> str:
        return self.repo.primary_user_id

    @property
    def account_balance(self) -> float:
        return self.repo.account_balance

    @account_balance.setter
    def account_balance(self, val: float):
        self.repo.account_balance = val

    # Gestion utilisateurs et groupes
    def get_user(self, user_id: str) -> Optional[User]:
        return self.repo.get_user(user_id)

    def get_user_profile(self, user_id: str) -> UserProfile:
        return self.repo.get_user_profile(user_id)

    @property
    def active_members(self) -> Dict[str, User]:
        return self.repo.active_members

    def get_available_contacts(self, group_id: Optional[str] = None) -> List[User]:
        return self.repo.get_available_contacts(group_id)

    def add_member_to_group(self, user_id: str, group_id: Optional[str] = None) -> bool:
        return self.repo.add_member_to_group(user_id, group_id)

    def create_group(
        self,
        name: str,
        member_ids: List[str],
        description: str = "",
        icon: str = "👥"
    ) -> SharedGroup:
        return self.repo.create_group(name, member_ids, description, icon)

    def switch_active_group(self, group_id: str):
        self.repo.switch_active_group(group_id)

    # Catégorisation et ingestion
    def categorize_transaction(self, merchant: str, amount: float) -> Tuple[str, str]:
        return categorize_transaction(merchant, amount)

    def process_transaction_file(
        self,
        file_obj,
        user_id: str,
        file_type: str,
        date_offset: timedelta = timedelta(0)
    ) -> int:
        return self.repo.process_transaction_file(file_obj, user_id, file_type, date_offset)

    # Compte partagé & Tricount
    def get_shared_transactions(self, group_id: Optional[str] = None) -> List[Transaction]:
        target = group_id or self.active_group_id
        return get_shared_transactions(self.transactions, target)

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
        target = group_id or self.active_group_id
        split_details = split_details or self._default_split(amount, payer_id, target)
        return add_direct_expense(
            self.transactions, merchant, amount, payer_id, split_details, date, target, note
        )

    def share_transaction(self, tx_id: str, split_details: Dict[str, float], group_id: Optional[str] = None):
        target = group_id or self.active_group_id
        if not split_details:
            tx = next((t for t in self.transactions if t.id == tx_id), None)
            if tx:
                split_details = self._default_split(tx.amount, tx.user_id, target)
        share_transaction(self.transactions, tx_id, split_details, target)

    def _default_split(self, amount: float, payer_id: str, group_id: str) -> Dict[str, float]:
        """Parts égales entre les membres actuels, figées au moment où la dépense entre dans le groupe."""
        group = self.groups.get(group_id)
        return split_equally(abs(amount), list(group.members), payer_id) if group else {}

    def unshare_transaction(self, tx_id: str):
        unshare_transaction(self.transactions, tx_id)

    def calculate_balances(self, group_id: Optional[str] = None) -> Dict[str, float]:
        target = group_id or self.active_group_id
        return calculate_balances(self.groups, self.transactions, target)

    def optimize_transfers(self, net_balances: Dict[str, float]) -> List[Tuple[str, str, float, str, str]]:
        return optimize_transfers(net_balances, self.users)

    def execute_instant_settlement(
        self,
        from_user_id: str,
        to_user_id: str,
        amount: float,
        group_id: Optional[str] = None
    ) -> Transaction:
        target = group_id or self.active_group_id
        tx, new_bal = execute_instant_settlement(
            transactions=self.transactions,
            users=self.users,
            groups=self.groups,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            amount=amount,
            group_id=target,
            primary_user_id=self.primary_user_id,
            current_balance=self.account_balance
        )
        self.account_balance = new_bal
        return tx

    # Budget et benchmark
    def analyze_monthly_budget(self, user_id: str) -> Dict:
        profile = self.get_user_profile(user_id)
        return analyze_monthly_budget(self.transactions, profile, user_id)

    def load_peers_benchmark(self, filepath: Optional[str] = None) -> Dict[str, Dict]:
        self.peers_benchmark_data = load_peers_benchmark(filepath)
        return self.peers_benchmark_data

    def get_category_breakdown(
        self,
        user_id: str,
        window_days: int = 30
    ) -> Tuple[Dict[str, float], Dict[str, Dict], Dict[str, Dict[str, float]]]:
        return get_category_breakdown(
            transactions=self.transactions,
            user_id=user_id,
            peers_benchmark_data=self.peers_benchmark_data,
            window_days=window_days
        )

    def load_public_aids(self, country: Optional[str] = None) -> Any:
        return self.repo.load_public_aids(country)

    def get_targeted_public_aids(self, user_id: str) -> List[Dict]:
        return self.repo.get_targeted_public_aids(user_id)

    def calculate_health_score(self, user_id: str) -> Dict[str, Any]:
        profile = self.get_user_profile(user_id)
        budget = self.analyze_monthly_budget(user_id)
        categories, peers, _ = self.get_category_breakdown(user_id, window_days=30)
        return calculate_health_score(profile, budget, categories, peers)


__all__ = ["BankBackend"]
