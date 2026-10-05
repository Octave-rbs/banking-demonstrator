"""
Moteur de dépenses partagées, calcul des soldes et virements instantanés.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from models import Transaction, User, SharedGroup
from services.categorizer import categorize_transaction


def get_shared_transactions(transactions: List[Transaction], group_id: str) -> List[Transaction]:
    """Récupère les transactions associées au groupe spécifié."""
    return [tx for tx in transactions if tx.shared_account_id == group_id]


def add_direct_expense(
    transactions: List[Transaction],
    merchant: str,
    amount: float,
    payer_id: str,
    split_details: Dict[str, float],
    date: Optional[datetime] = None,
    group_id: Optional[str] = None,
    note: str = ""
) -> Transaction:
    """Ajoute une dépense directe au compte partagé."""
    tx_date = date or datetime.now()
    cat, subcat = categorize_transaction(merchant, amount)

    tx = Transaction(
        id=str(uuid.uuid4())[:8],
        user_id=payer_id,
        merchant=merchant,
        amount=abs(amount),
        method="compte partagé",
        date=tx_date,
        shared_account_id=group_id,
        split_details=split_details,
        category=cat,
        subcategory=subcat,
        is_settlement=False,
        note=note
    )
    transactions.append(tx)
    return tx


def share_transaction(
    transactions: List[Transaction],
    tx_id: str,
    split_details: Dict[str, float],
    group_id: str
):
    """Affecte une transaction existante au compte partagé."""
    for tx in transactions:
        if tx.id == tx_id:
            tx.shared_account_id = group_id
            tx.split_details = split_details
            break


def unshare_transaction(transactions: List[Transaction], tx_id: str):
    """Retire une transaction du compte partagé."""
    for tx in transactions:
        if tx.id == tx_id:
            tx.shared_account_id = None
            tx.split_details = {}
            break


def calculate_balances(
    groups: Dict[str, SharedGroup],
    transactions: List[Transaction],
    group_id: str
) -> Dict[str, float]:
    """
    Calcule la balance nette de chaque membre dans le groupe.
    > 0 : créancier (on lui doit)
    < 0 : débiteur (il doit)
    """
    group = groups.get(group_id)
    if not group or not group.members:
        return {}

    shared_txs = get_shared_transactions(transactions, group_id)
    balances = {uid: 0.0 for uid in group.members}

    for tx in shared_txs:
        payer_id = tx.user_id

        # Virement de remboursement entre membres
        if tx.is_settlement:
            if payer_id in balances:
                balances[payer_id] += tx.amount
            for beneficiary_id, share in tx.split_details.items():
                if beneficiary_id in balances:
                    balances[beneficiary_id] -= share
            continue

        # Dépense partagée classique
        if payer_id in balances:
            balances[payer_id] += tx.amount

        if tx.split_details:
            for uid, share in tx.split_details.items():
                if uid in balances:
                    balances[uid] -= share
        else:
            default_share = tx.amount / len(group.members)
            for uid in group.members:
                balances[uid] -= default_share

    return balances


def optimize_transfers(
    net_balances: Dict[str, float],
    users: Dict[str, User]
) -> List[Tuple[str, str, float, str, str]]:
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

        d_name = users[d_id].name if d_id in users else d_id
        c_name = users[c_id].name if c_id in users else c_id

        transfers.append((d_name, c_name, amount, d_id, c_id))

        debtors[i][1] -= amount
        creditors[j][1] -= amount

        if debtors[i][1] < 0.01:
            i += 1
        if creditors[j][1] < 0.01:
            j += 1

    return transfers


def execute_instant_settlement(
    transactions: List[Transaction],
    users: Dict[str, User],
    groups: Dict[str, SharedGroup],
    from_user_id: str,
    to_user_id: str,
    amount: float,
    group_id: str,
    primary_user_id: str,
    current_balance: float
) -> Tuple[Transaction, float]:
    """
    Exécute un virement instantané soldant une dette :
    - Écriture de règlement dans le groupe
    - Transaction personnelle et mise à jour du solde si l'utilisateur principal est concerné
    Retourne (settlement_tx, new_account_balance).
    """
    group = groups.get(group_id)
    group_name = group.name if group else "Groupe"
    now = datetime.now()
    settlement_id = f"virement_{uuid.uuid4().hex[:6]}"
    to_name = users.get(to_user_id, User(id=to_user_id, name="Bénéficiaire")).name
    from_name = users.get(from_user_id, User(id=from_user_id, name="Payeur")).name

    shared_settlement_tx = Transaction(
        id=settlement_id,
        user_id=from_user_id,
        merchant=f"⚡ Virement Instantané : {from_name} ➔ {to_name}",
        amount=amount,
        method="virement instantané",
        date=now,
        shared_account_id=group_id,
        split_details={to_user_id: amount},
        category="Virement Interne",
        subcategory="Remboursement de dette",
        is_settlement=True,
        note=f"Remboursement automatique - {group_name}"
    )
    transactions.append(shared_settlement_tx)

    updated_balance = current_balance
    if from_user_id == primary_user_id:
        updated_balance -= amount
        personal_debit_tx = Transaction(
            id=f"tx_{uuid.uuid4().hex[:6]}",
            user_id=primary_user_id,
            merchant=f"Virement instantané émis vers {to_name} ({group_name})",
            amount=amount,
            method="virement instantané",
            date=now,
            category="Virement Émis",
            subcategory="Remboursement groupe",
            is_settlement=False
        )
        transactions.append(personal_debit_tx)
    elif to_user_id == primary_user_id:
        updated_balance += amount
        personal_credit_tx = Transaction(
            id=f"tx_{uuid.uuid4().hex[:6]}",
            user_id=primary_user_id,
            merchant=f"Virement instantané reçu de {from_name} ({group_name})",
            amount=-amount,
            method="virement instantané",
            date=now,
            category="Revenus & Aides",
            subcategory="Remboursements",
            is_settlement=False
        )
        transactions.append(personal_credit_tx)

    return shared_settlement_tx, updated_balance
