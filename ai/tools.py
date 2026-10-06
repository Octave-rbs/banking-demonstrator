"""
Outils d'audit financier pour l'agent IA.
Permet au LLM d'interroger dynamiquement la base de données bancaire et les benchmarks.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from services import BankBackend


# URLs officielles des portails d'aides publiques
OFFICIAL_AID_URLS = {
    "fr_apl": "https://www.caf.fr/allocataires/aides-et-demarches/mes-demarches/faire-une-demande-de-prestation/aide-au-logement",
    "fr_prime_activite": "https://www.caf.fr/allocataires/aides-et-demarches/mes-demarches/faire-une-demande-de-prestation/prime-d-activite",
    "fr_mobili_jeune": "https://mobilijeune.actionlogement.fr",
    "fr_lep": "https://www.service-public.fr/particuliers/vosdroits/F2367",
    "es_bono_alquiler": "https://www.mitma.gob.es/vivienda/bono-alquiler-joven",
    "es_imv": "https://sede.seg-social.gob.es/wps/portal/sede/fecha/IMV",
    "es_beca_mefp": "https://www.becaseducacion.gob.es",
    "de_wohngeld": "https://www.bmi.bund.de/DE/themen/bauen-wohnen/stadt-wohnen/wohraumfoerderung/wohngeld/wohngeld-node.html",
    "de_bafoeg": "https://www.bafoeg-digital.de",
    "de_buergergeld": "https://www.arbeitsagentur.de/buergergeld",
    "pl_dodatek_mieszkaniowy": "https://www.gov.pl/web/gov/uzyskaj-dodatek-mieszkaniowy",
    "pl_stypendium_socjalne": "https://usosweb.mimuw.edu.pl"
}


def get_budget_overview(db: BankBackend, user_id: str, window_days: int = 30) -> Dict[str, Any]:
    """
    Retourne la synthèse globale du budget sur la période glissante spécifiée :
    revenus réels identifiés vs déclarés, dépenses totales réelles (fixes vs variables),
    marge d'épargne / reste à vivre restant, et statut de santé budgétaire.
    """
    budget = db.analyze_monthly_budget(user_id)
    profile = db.get_user_profile(user_id)
    
    spent_30d = float(budget.get("rolling_spent", 0.0))
    balance = float(getattr(db, "account_balance", 0.0))
    target_3m = round(spent_30d * 3, 2)
    months_saved = round(balance / spent_30d, 1) if spent_30d > 0 else 3.0
    has_3m_savings = balance >= target_3m
    idle_cash = max(0.0, round(balance - spent_30d, 2))
    missing_emergency = max(0.0, round(target_3m - balance, 2))

    return {
        "statut_budget": budget.get("status", "safe"),
        "est_en_depassement": budget.get("is_over_budget", False),
        "revenu_net_declare_mensuel": profile.monthly_net_income,
        "revenu_reel_identifie_30j": budget.get("rolling_income", profile.monthly_net_income),
        "depenses_totales_30j": round(spent_30d, 2),
        "charges_fixes_30j": round(budget.get("rolling_fixed", 0.0), 2),
        "depenses_variables_30j": round(budget.get("rolling_variable", 0.0), 2),
        "reste_a_vivre_30j": round(budget.get("rolling_remaining", 0.0), 2),
        "projection_fin_de_mois": round(budget.get("calendar_projection", 0.0), 2),
        "periode": budget.get("rolling_label", f"{window_days} derniers jours"),
        "solde_bancaire_disponible": round(balance, 2),
        "coussin_securite_cible_3_mois": target_3m,
        "mois_epargne_securite_actuels": months_saved,
        "a_3_mois_epargne_precaution": has_3m_savings,
        "manque_pour_3_mois": missing_emergency,
        "argent_dormant_compte_courant": idle_cash
    }



def get_largest_expenses(
    db: BankBackend,
    user_id: str,
    window_days: int = 30,
    category: Optional[str] = None,
    expense_type: str = "all",
    limit: int = 5
) -> Dict[str, Any]:
    """
    Identifie les dépenses les plus importantes sur la période.
    expense_type: 'all' (toutes dépenses), 'variable' (dépenses courantes hors loyer/abonnements), ou 'fixed'.
    category: filtrer optionnellement par nom de catégorie.
    """
    user_txs = [tx for tx in db.transactions if tx.user_id == user_id and not tx.is_settlement]
    if not user_txs:
        return {"expenses": [], "count": 0}

    max_date = max(tx.date for tx in user_txs)
    start_date = max_date - timedelta(days=window_days)

    fixed_categories = ["Logement & Charges", "Abonnements & Services"]
    
    filtered = []
    for tx in user_txs:
        if start_date <= tx.date <= max_date and tx.amount > 0 and tx.category != "Revenus & Aides":
            if category and not (category.lower() in tx.category.lower() or tx.category.lower() in category.lower()):
                continue
            if expense_type == "variable" and tx.category in fixed_categories:

                continue
            if expense_type == "fixed" and tx.category not in fixed_categories:
                continue
            filtered.append(tx)

    filtered.sort(key=lambda t: t.amount, reverse=True)
    top_items = filtered[:limit]

    return {
        "filtre_type": expense_type,
        "filtre_categorie": category or "Toutes",
        "total_depenses_trouvees": len(filtered),
        "plus_grosses_depenses": [
            {
                "marchand": tx.merchant,
                "montant": round(tx.amount, 2),
                "date": tx.date.strftime("%d/%m/%Y"),
                "categorie": tx.category,
                "sous_categorie": tx.subcategory
            }
            for tx in top_items
        ]
    }


def get_peer_benchmark_comparison(db: BankBackend, user_id: str) -> Dict[str, Any]:
    """
    Compare les dépenses du client par catégorie avec les statistiques de ses pairs (même tranche d'âge/ville).
    Identifie la catégorie avec le plus grand écart de surcoût ainsi que les catégories vertueuses.
    """
    categories, peers, subcategories = db.get_category_breakdown(user_id, window_days=30)
    
    comparisons = []
    max_gap_cat = None
    max_gap_val = -999999.0

    well_managed = []
    needs_attention = []

    for cat, spent in categories.items():
        p_info = peers.get(cat, {})
        avg = float(p_info.get("avg", 0.0))
        delta = spent - avg
        ratio = round(spent / avg, 2) if avg > 0 else 1.0

        item = {
            "categorie": cat,
            "depense_client": round(spent, 2),
            "moyenne_pairs": round(avg, 2),
            "ecart_euros": round(delta, 2),
            "ratio_vs_pairs": ratio,
            "position": p_info.get("relative_position", "Dans la moyenne"),
            "statut": p_info.get("status", "")
        }
        comparisons.append(item)

        if delta > max_gap_val:
            max_gap_val = delta
            max_gap_cat = cat

        if delta > 30.0:
            needs_attention.append(item)
        elif delta <= 0.0:
            well_managed.append(item)

    # Récupération des sous-catégories de la catégorie au plus fort écart
    critical_subs = subcategories.get(max_gap_cat, {}) if max_gap_cat else {}

    return {
        "categorie_plus_grand_ecart": {
            "categorie": max_gap_cat,
            "surcout_vs_pairs_euros": round(max_gap_val, 2) if max_gap_cat else 0.0,
            "sous_categories_detail": {k: round(v, 2) for k, v in critical_subs.items()}
        },
        "postes_en_surcout": needs_attention,
        "postes_bien_maitrises": well_managed,
        "toutes_categories": comparisons
    }


def get_category_transactions(
    db: BankBackend,
    user_id: str,
    category_name: str,
    window_days: int = 30,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Inspecte en détail les transactions et sous-catégories d'une catégorie spécifique
    (ex: 'Alimentation & Restauration', 'Loisirs & Sorties', 'Shopping & Mode').
    """
    user_txs = [tx for tx in db.transactions if tx.user_id == user_id and not tx.is_settlement]
    if not user_txs:
        return {"category": category_name, "transactions": [], "total_spent": 0.0}

    max_date = max(tx.date for tx in user_txs)
    start_date = max_date - timedelta(days=window_days)

    matched = [
        tx for tx in user_txs
        if start_date <= tx.date <= max_date
        and (
            category_name.lower() in tx.category.lower()
            or tx.category.lower() in category_name.lower()
        )
        and tx.amount > 0
    ]


    matched.sort(key=lambda t: t.date, reverse=True)
    total_spent = sum(t.amount for t in matched)

    # Répartition sous-catégories
    subcats = {}
    for t in matched:
        subcats[t.subcategory] = round(subcats.get(t.subcategory, 0.0) + t.amount, 2)

    return {
        "categorie": category_name,
        "total_depense_30j": round(total_spent, 2),
        "repartition_sous_categories": subcats,
        "transactions_recentes": [
            {
                "marchand": t.merchant,
                "montant": round(t.amount, 2),
                "date": t.date.strftime("%d/%m/%Y"),
                "sous_categorie": t.subcategory
            }
            for t in matched[:limit]
        ]
    }


def detect_recurring_subscriptions(db: BankBackend, user_id: str) -> Dict[str, Any]:
    """
    Détecte les abonnements récurrents et prélèvements fixes réguliers
    (streaming, salle de sport, télécom, énergie, assurances).
    """
    user_txs = [tx for tx in db.transactions if tx.user_id == user_id and not tx.is_settlement]
    
    subscriptions = []
    total_cost = 0.0

    for tx in user_txs:
        if tx.category in ["Abonnements & Services", "Logement & Charges"] and tx.amount > 0:
            if tx.category == "Logement & Charges" and ("loyer" in tx.merchant.lower() or tx.amount > 300):
                continue  # Exclusion du loyer principal
            item = {
                "service": tx.merchant,
                "montant": round(tx.amount, 2),
                "categorie": tx.category,
                "sous_categorie": tx.subcategory
            }
            if not any(s["service"] == item["service"] for s in subscriptions):
                subscriptions.append(item)
                total_cost += tx.amount

    return {
        "nombre_abonnements": len(subscriptions),
        "cout_total_mensuel": round(total_cost, 2),
        "abonnements_detectes": subscriptions
    }


def search_eligible_public_aids(db: BankBackend, user_id: str) -> Dict[str, Any]:
    """
    Recherche les dispositifs d'aides publiques éligibles pour le profil client
    selon son pays, son âge, son statut (étudiant/alternant/salarié), son loyer et sa rémunération.
    Retourne les montants indicatifs, conditions et liens officiels de démarches.
    """
    profile = db.get_user_profile(user_id)
    country = getattr(profile, "country", "France")
    targeted = db.get_targeted_public_aids(user_id)

    results = []
    for aid in targeted:
        aid_id = aid.get("id", "")
        url = OFFICIAL_AID_URLS.get(aid_id, "https://www.service-public.fr")
        results.append({
            "id": aid_id,
            "nom": aid.get("name", ""),
            "organisme": aid.get("organism", ""),
            "public_cible": aid.get("target_group", ""),
            "gain_indicatif": aid.get("typical_benefit", ""),
            "criteres_cles": aid.get("eligibility_criteria", []),
            "demarche": aid.get("procedure", "En ligne"),
            "url_officielle": url
        })

    return {
        "pays": country,
        "profil_analyse": {
            "statut": profile.status,
            "remuneration_declaree": profile.monthly_net_income,
            "part_loyer": profile.rent_amount,
            "logement": getattr(profile, "housing_type", "Colocation")
        },
        "aides_pertinentes": results
    }


def simulate_stock_investment(

    db: Optional[BankBackend] = None,
    user_id: Optional[str] = None,
    initial_deposit: float = 200.0,
    monthly_deposit: float = 50.0,
    years: int = 5,
    annual_yield: float = 0.07,
    account_type: str = "PEA"
) -> Dict[str, Any]:
    """
    Simule un plan d'investissement en Bourse (PEA vs CTO) avec calcul d'intérêts composés et fiscalité.
    """
    total_months = int(years * 12)
    r = float(annual_yield)
    monthly_rate = (1 + r) ** (1 / 12) - 1 if r > 0 else 0.0

    invested = float(initial_deposit) + (float(monthly_deposit) * total_months)
    fv_initial = float(initial_deposit) * ((1 + r) ** years)
    if monthly_rate > 0:
        fv_monthly = float(monthly_deposit) * (((1 + monthly_rate) ** total_months - 1) / monthly_rate)
    else:
        fv_monthly = float(monthly_deposit) * total_months
    total_capital = fv_initial + fv_monthly
    capital_gain = max(0.0, total_capital - invested)

    is_pea = "pea" in str(account_type).lower()
    tax_rate = 0.172 if is_pea else 0.30
    tax = capital_gain * tax_rate
    net_gain = capital_gain - tax

    return {
        "support": "PEA (Plan d'Épargne en Actions)" if is_pea else "CTO (Compte-Titres Ordinaire)",
        "capital_investi_euros": round(invested, 2),
        "capital_final_estime_euros": round(total_capital, 2),
        "plus_value_brute_euros": round(capital_gain, 2),
        "plus_value_nette_euros": round(net_gain, 2),
        "horizon_annees": years,
        "fiscalite": "17,2% prélèvements sociaux (exonéré d'impôt sur le revenu après 5 ans)" if is_pea else "Flat Tax de 30% (CTO)"
    }


# Dictionnaire de dispatch des outils
AUDIT_TOOLS_MAP = {
    "get_budget_overview": get_budget_overview,
    "get_largest_expenses": get_largest_expenses,
    "get_peer_benchmark_comparison": get_peer_benchmark_comparison,
    "get_category_transactions": get_category_transactions,
    "detect_recurring_subscriptions": detect_recurring_subscriptions,
    "search_eligible_public_aids": search_eligible_public_aids,
    "simulate_stock_investment": simulate_stock_investment,
}

# Définitions JSON des outils présentées au LLM
AUDIT_TOOLS_SPECS = [
    {
        "name": "get_budget_overview",
        "description": "Obtenir la synthèse budgétaire globale (revenus réels identifiés, dépenses fixes vs variables, reste à vivre, statut d'alerte).",
        "parameters": {
            "window_days": {"type": "integer", "description": "Fenêtre d'analyse en jours (défaut 30)"}
        }
    },
    {
        "name": "get_largest_expenses",
        "description": "Identifier les postes de dépenses les plus élevés ou anormaux sur les 30 derniers jours.",
        "parameters": {
            "window_days": {"type": "integer", "description": "Fenêtre en jours (défaut 30)"},
            "category": {"type": "string", "description": "Nom de catégorie optionnel pour filtrer"},
            "expense_type": {"type": "string", "description": "'variable' (dépenses courantes), 'fixed' (abonnements/loyer), ou 'all'"},
            "limit": {"type": "integer", "description": "Nombre de transactions à retourner (défaut 5)"}
        }
    },
    {
        "name": "get_peer_benchmark_comparison",
        "description": "Comparer les dépenses réelles par catégorie avec la moyenne des pairs similaires. Identifie le plus grand surcoût et les postes bien tenus.",
        "parameters": {}
    },
    {
        "name": "get_category_transactions",
        "description": "Inspecter en détail les transactions et sous-catégories d'un poste précis (ex: 'Alimentation & Restauration', 'Shopping & Mode').",
        "parameters": {
            "category_name": {"type": "string", "description": "Nom exact de la catégorie à inspecter"},
            "window_days": {"type": "integer", "description": "Fenêtre en jours (défaut 30)"},
            "limit": {"type": "integer", "description": "Nombre de transactions à retourner (défaut 10)"}
        }
    },
    {
        "name": "detect_recurring_subscriptions",
        "description": "Lister tous les abonnements récurrents et frais fixes prélevés chaque mois avec le coût mensuel global.",
        "parameters": {}
    },
    {
        "name": "search_eligible_public_aids",
        "description": "Rechercher les dispositifs d'aides sociales applicables selon le profil, loyer, statut et pays de résidence, avec montants et liens officiels.",
        "parameters": {}
    },
    {
        "name": "simulate_stock_investment",
        "description": "Simuler un investissement en Bourse (PEA ou CTO) : calcul de la plus-value nette selon le versement initial, l'épargne mensuelle (DCA) et la fiscalité.",
        "parameters": {
            "initial_deposit": {"type": "number", "description": "Dépôt initial en euros (ex: 200)"},
            "monthly_deposit": {"type": "number", "description": "Épargne mensuelle programmée (ex: 50)"},
            "years": {"type": "integer", "description": "Horizon d'investissement en années (ex: 5)"},
            "annual_yield": {"type": "number", "description": "Taux de rendement moyen (ex: 0.07 pour 7%)"},
            "account_type": {"type": "string", "description": "'PEA' (fiscalité avantageuse 5 ans) ou 'CTO' (flexibilité mondiale)"}
        }
    }
]


def execute_tool(tool_name: str, arguments: Dict[str, Any], db: BankBackend, user_id: str) -> Dict[str, Any]:
    """Exécute une fonction d'audit en toute sécurité."""
    fn = AUDIT_TOOLS_MAP.get(tool_name)
    if not fn:
        return {"error": f"Outil '{tool_name}' inconnu. Outils valides : {list(AUDIT_TOOLS_MAP.keys())}"}
    try:
        if tool_name in ["get_budget_overview", "get_peer_benchmark_comparison", "detect_recurring_subscriptions", "search_eligible_public_aids"]:
            return fn(db=db, user_id=user_id)
        elif tool_name == "get_largest_expenses":
            return fn(
                db=db,
                user_id=user_id,
                window_days=int(arguments.get("window_days", 30)),
                category=arguments.get("category"),
                expense_type=arguments.get("expense_type", "all"),
                limit=int(arguments.get("limit", 5))
            )
        elif tool_name == "get_category_transactions":
            return fn(
                db=db,
                user_id=user_id,
                category_name=arguments.get("category_name", ""),
                window_days=int(arguments.get("window_days", 30)),
                limit=int(arguments.get("limit", 10))
            )
        elif tool_name == "simulate_stock_investment":
            return fn(
                db=db,
                user_id=user_id,
                initial_deposit=float(arguments.get("initial_deposit", 200.0)),
                monthly_deposit=float(arguments.get("monthly_deposit", 50.0)),
                years=int(arguments.get("years", 5)),
                annual_yield=float(arguments.get("annual_yield", 0.07)),
                account_type=str(arguments.get("account_type", "PEA"))
            )
        return fn(db=db, user_id=user_id)
    except Exception as e:
        return {"error": f"Erreur lors de l'exécution de '{tool_name}': {str(e)}"}

