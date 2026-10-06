"""
Package des vues et composants graphiques Streamlit.
"""

from views.home_view import render_home_view
from views.shared_view import render_shared_view
from views.budget_view import render_budget_view
from views.advisor_view import render_advisor_view
from views.dialogs import open_savings_account_dialog, open_stock_investment_dialog, set_budget_ceiling_dialog

__all__ = [
    "render_home_view",
    "render_shared_view",
    "render_budget_view",
    "render_advisor_view",
    "open_savings_account_dialog",
    "open_stock_investment_dialog",
    "set_budget_ceiling_dialog"
]


