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

    def process_transaction_file(self, file_obj, user_id: str, file_type: str) -> int:
        return self.repo.process_transaction_file(file_obj, user_id, file_type)

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
        return add_direct_expense(
            self.transactions, merchant, amount, payer_id, split_details, date, target, note
        )

    def share_transaction(self, tx_id: str, split_details: Dict[str, float], group_id: Optional[str] = None):
        target = group_id or self.active_group_id
        share_transaction(self.transactions, tx_id, split_details, target)

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

    def get_llm_financial_context(self, user_id: str) -> Dict:
        """Extrait un contexte bancaire enrichi, factuel et neutre pour le LLM."""
        budget = self.analyze_monthly_budget(user_id)
        categories, peers, subcategories = self.get_category_breakdown(user_id, window_days=30)
        user_txs = [tx for tx in self.transactions if tx.user_id == user_id and not tx.is_settlement]

        max_date = max((tx.date for tx in user_txs), default=datetime.now())
        rolling_start = max_date - timedelta(days=30)

        # 1. Flux entrants
        detected_incomes = []
        for tx in user_txs:
            if rolling_start <= tx.date <= max_date and (tx.amount < 0 or tx.category == "Revenus & Aides"):
                amt_abs = abs(tx.amount)
                label = f"{tx.merchant} ({amt_abs:.2f} € le {tx.date.strftime('%d/%m')})"
                if label not in detected_incomes:
                    detected_incomes.append(label)

        # 2. Abonnements
        detected_subscriptions = []
        for tx in user_txs:
            if tx.category in ["Abonnements & Services", "Logement & Charges"]:
                label = f"{tx.merchant} ({tx.amount:.2f} €)"
                if label not in detected_subscriptions and tx.amount > 0:
                    detected_subscriptions.append(label)

        # Dépense ponctuelle la plus importante
        expense_txs = [tx for tx in user_txs if tx.amount > 0 and tx.category != "Revenus & Aides"]
        largest_expense = max(expense_txs, key=lambda t: t.amount) if expense_txs else None
        largest_expense_str = (
            f"{largest_expense.merchant} ({largest_expense.amount:.2f} € le {largest_expense.date.strftime('%d/%m')})"
            if largest_expense else "Aucune"
        )

        # 3. Catégorie au plus fort écart
        max_gap_cat = None
        max_gap_val = -999999.0
        for cat, spent in categories.items():
            peer_avg = peers.get(cat, {}).get("avg", 0.0)
            gap = spent - peer_avg
            if gap > max_gap_val:
                max_gap_val = gap
                max_gap_cat = cat

        critical_subcategories = subcategories.get(max_gap_cat, {}) if max_gap_cat else {}
        max_gap_info = peers.get(max_gap_cat, {})

        # 4. Catégories bien gérées
        well_managed = []
        for cat, p_info in peers.items():
            spent = categories.get(cat, 0.0)
            avg = p_info.get("avg", 0.0)
            rel_pos = p_info.get("relative_position", p_info.get("status", ""))
            if spent <= avg and spent > 0:
                well_managed.append(f"{cat} : {spent:.0f} € ({rel_pos})")
            elif cat not in categories:
                well_managed.append(f"{cat} : 0 € (Moyenne pairs : {avg:.0f} €)")

        # Résumé comparatif
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


__all__ = ["BankBackend"]
