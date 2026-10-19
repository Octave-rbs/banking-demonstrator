"""
Simulation d'un plan d'investissement en Bourse (PEA ou CTO).
"""

from typing import Dict

# Fiscalité sur les plus-values : prélèvements sociaux (PEA de plus de 5 ans) ou flat tax (CTO)
PEA_TAX_RATE = 0.172
CTO_TAX_RATE = 0.30

# Taux net du Livret d'Épargne Populaire, fixé à 2,5 % au 1er août 2026 (jusqu'au 31/01/2027)
LEP_ANNUAL_RATE = 0.025


def simulate_investment(
    initial_deposit: float,
    monthly_deposit: float,
    years: int,
    annual_yield: float,
    is_pea: bool
) -> Dict[str, float]:
    """Intérêts composés avec versements mensuels, puis fiscalité du support choisi."""
    total_months = int(years * 12)
    r = float(annual_yield)
    monthly_rate = (1 + r) ** (1 / 12) - 1 if r > 0 else 0.0

    invested = float(initial_deposit) + float(monthly_deposit) * total_months
    fv_initial = float(initial_deposit) * ((1 + r) ** years)
    if monthly_rate > 0:
        fv_monthly = float(monthly_deposit) * (((1 + monthly_rate) ** total_months - 1) / monthly_rate)
    else:
        fv_monthly = float(monthly_deposit) * total_months
    final_capital = fv_initial + fv_monthly
    capital_gain = max(0.0, final_capital - invested)
    net_gain = capital_gain * (1 - (PEA_TAX_RATE if is_pea else CTO_TAX_RATE))

    return {
        "invested": invested,
        "final_capital": final_capital,
        "capital_gain": capital_gain,
        "net_gain": net_gain,
    }
