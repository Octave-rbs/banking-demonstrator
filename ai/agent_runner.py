"""
Moteur d'exécution agentique (Agent Runner) Fact-Grounded.
Orchestre l'investigation bancaire outillée, élimine les hallucinations arithmétiques
et produit une synthèse humaine impeccable avec des Cartes d'Actions en 1 clic garanties.
"""

import json
import math
import re
import time
from typing import Dict, List, Optional, Any, Generator, Tuple
from models import UserProfile
from services import BankBackend
from services.investment_service import LEP_ANNUAL_RATE
from ai.hf_client import HFClient
from ai.tools import (
    get_budget_overview,
    get_peer_benchmark_comparison,
    get_largest_expenses,
    detect_recurring_subscriptions,
    search_eligible_public_aids,
    OFFICIAL_AID_URLS
)


def extract_tool_call(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Détecte un appel d'outil structuré dans la réponse."""
    match = re.search(r"```(?:tool_call|json)?\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if match:
        try:
            data = json.loads(match.group(1))
            if "tool" in data:
                return data["tool"], data.get("parameters", {})
        except Exception:
            pass
    return None


ALLOWED_IN_APP_ACTIONS = {"open_savings_dialog", "open_stock_investment_dialog", "set_budget_alert"}


def sanitize_llm_action_card(card: Any) -> Optional[Dict[str, Any]]:
    """
    Valide une carte d'action proposée par le LLM.
    Toute URL fournie par le modèle est ignorée : le lien est résolu côté serveur
    via OFFICIAL_AID_URLS à partir de l'id. Les cartes inconnues sont écartées.
    """
    if not isinstance(card, dict):
        return None
    card_type = card.get("type", "external_link")
    if card_type == "external_link":
        url = OFFICIAL_AID_URLS.get(str(card.get("id", "")))
        if not url:
            return None
        return {**card, "url": url}
    if card_type == "in_app_dialog":
        return card if card.get("action_name") in ALLOWED_IN_APP_ACTIONS else None
    if card_type == "in_app_navigation":
        return card
    return None


def extract_action_cards(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Extrait d'éventuelles cartes d'actions au format JSON, les valide et nettoie le texte."""
    cards = []
    clean = text
    match = re.search(r"```actions\s*(\[[\s\S]*?\])\s*```", text, re.IGNORECASE)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, list):
                cards = [c for c in (sanitize_llm_action_card(p) for p in parsed) if c]
                clean = text.replace(match.group(0), "").strip()
        except Exception:
            pass
    return clean, cards



def fmt_eur(value: float) -> str:
    """Formate un montant à la française : 1 468,55 €."""
    return f"{value:,.2f}".replace(",", " ").replace(".", ",") + " €"


def parse_benefit_range(text: str) -> Optional[Tuple[float, float]]:
    """Extrait la fourchette mensuelle (min, max) en € d'un libellé du catalogue d'aides."""
    nums = [float(n.replace(",", ".")) for n in re.findall(r"(\d+(?:[.,]\d+)?)\s*€", text or "")]
    if not nums:
        return None
    return min(nums[:2]), max(nums[:2])


def assess_aid_conditions(aid: Dict[str, Any], profile: UserProfile) -> Tuple[List[str], List[str]]:
    """
    Sépare les conditions d'une aide en deux listes : celles que le profil confirme
    et celles qui restent à vérifier (information absente des données de la banque).
    """
    aid_id = aid.get("id", "")
    status = (profile.status + " " + getattr(profile, "job_activity", "")).lower()
    is_apprentice = "apprenti" in status or "apprentissage" in status
    is_alternant = is_apprentice or "alternan" in status
    confirmed: List[str] = []
    to_check: List[str] = []

    if aid_id == "fr_apl":
        if profile.rent_amount > 0:
            confirmed.append(f"paie un loyer de {fmt_eur(profile.rent_amount)} par mois")
        to_check += ["bail ou contrat de colocation à son nom", "ressources sous les plafonds CAF"]
    elif aid_id == "fr_prime_activite":
        if profile.age >= 18:
            confirmed.append(f"a {profile.age} ans")
        if profile.monthly_net_income > 0:
            confirmed.append("perçoit un revenu d'activité")
        # Seuil du catalogue pour les étudiants et alternants (data/public_aids_reference.json)
        if is_alternant and profile.monthly_net_income > 1082.87:
            confirmed.append("revenu net supérieur au seuil de 1 082,87 € exigé des alternants")
        to_check.append("montant réel, qui dépend de l'ensemble des ressources du foyer")
    elif aid_id == "fr_mobili_jeune":
        if profile.age < 30:
            confirmed.append(f"a moins de 30 ans ({profile.age} ans)")
        if is_apprentice:
            confirmed.append("est en contrat d'apprentissage")
        elif is_alternant:
            to_check.append("type de contrat (apprentissage ou professionnalisation)")
        to_check += ["employeur du secteur privé non agricole", "salaire brut inférieur ou égal au SMIC"]
    elif aid_id == "fr_lep":
        to_check.append("revenu fiscal de référence sous le plafond (avis d'imposition)")
    else:
        to_check += list(aid.get("criteres_cles", []))

    return confirmed, to_check


def build_fact_grounded_dossier(db: BankBackend, user_id: str) -> Tuple[Dict[str, Any], str]:
    """
    Exécute l'audit exhaustif et construit un dossier factuel pré-calculé.
    Tous les totaux, écarts et scénarios sont calculés ici : le LLM n'a plus qu'à rédiger.
    """
    profile = db.get_user_profile(user_id)
    country = getattr(profile, "country", "France")
    job = getattr(profile, "job_activity", profile.status)
    housing = getattr(profile, "housing_type", "Colocation")
    notes = getattr(profile, "custom_notes", "").strip() or "Aucun projet spécifique déclaré."

    # 1. Budget, trésorerie et coussin de sécurité
    b_data = get_budget_overview(db, user_id)
    income = b_data.get("revenu_reel_identifie_30j", profile.monthly_net_income)
    spent = b_data.get("depenses_totales_30j", 0.0)
    fixed = b_data.get("charges_fixes_30j", 0.0)
    variable = b_data.get("depenses_variables_30j", 0.0)
    net_margin = round(income - spent, 2)
    is_deficit = net_margin < 0

    balance = b_data.get("solde_bancaire_disponible", 0.0)
    available_savings = b_data.get("epargne_disponible_hors_mois_en_cours", 0.0)
    target_emergency = b_data.get("coussin_securite_cible_3_mois", 0.0)
    months_saved = b_data.get("mois_epargne_securite_actuels", 0.0)
    has_3m_savings = b_data.get("a_3_mois_epargne_precaution", False)
    missing_emergency = b_data.get("manque_pour_3_mois", 0.0)
    idle_cash = b_data.get("argent_dormant_compte_courant", 0.0)

    # 2. Benchmark pairs : dépense réelle du poste en surcoût ET écart avec les pairs
    peer_data = get_peer_benchmark_comparison(db, user_id)
    max_gap = peer_data.get("categorie_plus_grand_ecart", {})
    gap_cat = max_gap.get("categorie") or "Sorties & Loisirs"
    gap_overcost = max(0.0, max_gap.get("surcout_vs_pairs_euros", 0.0))
    gap_subs = max_gap.get("sous_categories_detail", {})
    gap_item = next((c for c in peer_data.get("toutes_categories", []) if c["categorie"] == gap_cat), {})
    gap_spent = gap_item.get("depense_client", 0.0)
    gap_peer_avg = gap_item.get("moyenne_pairs", 0.0)
    # Objectif raisonnable : combler la moitié de l'écart avec les pairs
    cut_target = round(gap_overcost / 2, 2)
    subs_formatted = ", ".join(f"{k} : {fmt_eur(v)}" for k, v in gap_subs.items()) if gap_subs else "non détaillé"

    well_managed = peer_data.get("postes_bien_maitrises", [])
    well_managed_str = ", ".join(
        f"{p['categorie']} ({fmt_eur(p['depense_client'])}, moyenne des pairs {fmt_eur(p['moyenne_pairs'])})"
        for p in well_managed[:2]
    ) if well_managed else "aucun poste sous la moyenne des pairs"

    # 3. Dépenses majeures
    large_data = get_largest_expenses(db, user_id, expense_type="variable", limit=3)
    top_txs = large_data.get("plus_grosses_depenses", [])
    top_txs_str = ", ".join(f"{t['marchand']} ({fmt_eur(t['montant'])} le {t['date']})" for t in top_txs) if top_txs else "aucune"

    # 4. Abonnements (services) et charges récurrentes (énergie, assurances...) séparés
    sub_data = detect_recurring_subscriptions(db, user_id)
    subs_list = sub_data.get("abonnements_detectes", [])
    subs_cost = sub_data.get("cout_total_mensuel", 0.0)
    services_subs = [s for s in subs_list if s["categorie"] == "Abonnements & Services"]
    charges_subs = [s for s in subs_list if s["categorie"] != "Abonnements & Services"]
    services_str = ", ".join(f"{s['service']} ({fmt_eur(s['montant'])})" for s in services_subs) or "aucun"
    charges_str = ", ".join(f"{s['service']} ({fmt_eur(s['montant'])})" for s in charges_subs) or "aucune"

    # 5. Aides publiques : fourchettes indicatives + conditions confirmées / à vérifier
    aids_data = search_eligible_public_aids(db, user_id)
    matched_aids = aids_data.get("aides_pertinentes", [])
    aids_lines = []
    aids_low, aids_high = 0.0, 0.0
    lep_to_check: List[str] = []
    for a in matched_aids:
        confirmed, to_check = assess_aid_conditions(a, profile)
        if a.get("id") == "fr_lep":
            lep_to_check = to_check
            continue  # Le LEP est traité dans la stratégie d'épargne
        rng = parse_benefit_range(a.get("gain_indicatif", ""))
        if rng:
            aids_low += rng[0]
            aids_high += rng[1]
            gain = f"entre {fmt_eur(rng[0])} et {fmt_eur(rng[1])} par mois (fourchette indicative du catalogue)"
        else:
            gain = a.get("gain_indicatif", "montant non précisé")
        aids_lines.append(
            f"- {a['nom']} ({a['organisme']}) : {gain}.\n"
            f"    Conditions confirmées : {'; '.join(confirmed) or 'aucune'}.\n"
            f"    Conditions à vérifier : {'; '.join(to_check) or 'aucune'}."
        )
    aids_dossier_str = "\n".join(aids_lines) if aids_lines else "- Aucune aide identifiée dans le catalogue officiel."

    # 6. Scénarios d'épargne mensuelle calculés (le LLM ne fait aucune addition)
    scenarios = [("Situation actuelle", net_margin)]
    if cut_target > 0:
        scenarios.append((f"Avec la réduction ciblée de {fmt_eur(cut_target)} sur {gap_cat}", round(net_margin + cut_target, 2)))
    if aids_low > 0:
        scenarios.append((
            ("Avec cette réduction et les aides" if cut_target > 0 else "Avec les aides")
            + " au bas de leur fourchette, si elles sont accordées",
            round(net_margin + cut_target + aids_low, 2),
        ))
    scenario_lines = []
    for label, monthly in scenarios:
        if has_3m_savings:
            outcome = "coussin déjà complet"
        elif monthly > 0 and math.ceil(missing_emergency / monthly) <= 60:
            outcome = f"coussin complet en {math.ceil(missing_emergency / monthly)} mois"
        elif monthly > 0:
            outcome = "le coussin progresse trop lentement (plus de 5 ans) : ce scénario ne suffit pas"
        else:
            outcome = "le coussin ne progresse pas, le compte baisse chaque mois"
        sign = "+" if monthly >= 0 else "−"
        scenario_lines.append(f"• {label} : {sign}{fmt_eur(abs(monthly))} par mois → {outcome}.")
    scenarios_str = "\n".join(scenario_lines)

    # 7. Consigne d'épargne : une seule règle, celle qui s'applique au client
    lep_rate = f"{LEP_ANNUAL_RATE * 100:.1f}".replace(".", ",") + " %"
    lep_condition = "; ".join(lep_to_check) or "revenu fiscal de référence sous le plafond"
    if has_3m_savings:
        excess = round(available_savings - target_emergency, 2)
        savings_rule = (
            f"Le coussin de 3 mois est complet. Félicite-le, puis propose un premier pas en Bourse via un PEA "
            f"avec tout ou partie de l'excédent au-delà du coussin ({fmt_eur(excess)}), en versements réguliers."
        )
    else:
        savings_rule = (
            "Le coussin de 3 mois n'est pas encore constitué : la priorité est de le bâtir sur un livret disponible à tout moment. "
            "Explique avec bienveillance qu'il vaut mieux attendre qu'il soit complet avant d'investir en Bourse (PEA ou CTO), "
            "parce qu'un imprévu pourrait obliger à vendre au mauvais moment."
        )
        if idle_cash > 200:
            savings_rule += (
                f" Propose de placer dès maintenant les {fmt_eur(idle_cash)} disponibles au-delà des dépenses du mois "
                f"sur un LEP ({lep_rate} net, disponible à tout moment), sous réserve d'éligibilité : {lep_condition}."
            )

    margin_str = (
        f"DÉFICIT de {fmt_eur(abs(net_margin))} par mois (les dépenses dépassent les revenus)"
        if is_deficit else f"EXCÉDENT de {fmt_eur(net_margin)} par mois"
    )

    dossier_text = f"""=== DOSSIER FINANCIER DE {profile.name.upper()} ===
• Profil : {profile.name}, {profile.age} ans, {job} ({profile.school_or_company}).
• Résidence : {housing} à {profile.city} ({country}). Part de loyer payée : {fmt_eur(profile.rent_amount)} par mois.
• Objectif personnel déclaré : "{notes}"

=== FLUX DES 30 DERNIERS JOURS ===
• Rémunération nette déclarée : {fmt_eur(profile.monthly_net_income)} | Revenus constatés : {fmt_eur(income)}
• Dépenses totales : {fmt_eur(spent)}, dont charges fixes {fmt_eur(fixed)} et dépenses variables {fmt_eur(variable)}
• Bilan mensuel : {margin_str}

=== TRÉSORERIE ET COUSSIN DE SÉCURITÉ ===
• Solde du compte courant : {fmt_eur(balance)}. Ce solde inclut l'argent nécessaire aux dépenses du mois ({fmt_eur(spent)}) : ce n'est pas de l'épargne.
• Épargne disponible au-delà des dépenses du mois : {fmt_eur(available_savings)}, soit {str(months_saved).replace('.', ',')} mois de dépenses d'avance.
• Objectif du coussin de sécurité (3 mois de dépenses) : {fmt_eur(target_emergency)}.
• Statut du coussin : {"COMPLET" if has_3m_savings else f"INCOMPLET, il manque {fmt_eur(missing_emergency)}"}.

=== SCÉNARIOS D'ÉPARGNE MENSUELLE (DÉJÀ CALCULÉS) ===
{scenarios_str}

=== CONSIGNE D'ÉPARGNE À APPLIQUER ===
{savings_rule}

=== DÉPENSES ET COMPARAISON AVEC LES PAIRS ===
• Poste au plus fort surcoût : "{gap_cat}". Dépense du client : {fmt_eur(gap_spent)}. Moyenne des pairs : {fmt_eur(gap_peer_avg)}. Écart : +{fmt_eur(gap_overcost)}.
  Détail des sous-postes : {subs_formatted}.
  Objectif de réduction proposé : {fmt_eur(cut_target)} par mois (la moitié de l'écart avec les pairs).
• Postes sous la moyenne des pairs : {well_managed_str}.
• Plus grosses dépenses variables : {top_txs_str}.
• Abonnements à des services ({fmt_eur(sum(s['montant'] for s in services_subs))} par mois) : {services_str}.
• Charges récurrentes hors loyer (énergie, assurances...) : {charges_str}.

=== AIDES DU CATALOGUE OFFICIEL (LES SEULES AUTORISÉES) ===
{aids_dossier_str}
"""

    audit_summary = {
        "profile": profile,
        "income": income,
        "spent": spent,
        "fixed": fixed,
        "variable": variable,
        "is_deficit": is_deficit,
        "margin": net_margin,
        "balance": balance,
        "available_savings": available_savings,
        "target_emergency": target_emergency,
        "months_saved": months_saved,
        "has_3m_savings": has_3m_savings,
        "idle_cash": idle_cash,
        "missing_emergency": missing_emergency,
        "gap_cat": gap_cat,
        "gap_overcost": gap_overcost,
        "gap_spent": gap_spent,
        "cut_target": cut_target,
        "gap_subs": gap_subs,
        "top_txs": top_txs,
        "subscriptions": subs_list,
        "subs_cost": subs_cost,
        "matched_aids": matched_aids,
        "aids_low": aids_low,
        "aids_high": aids_high,
        "scenarios": scenarios,
        "country": country
    }

    return audit_summary, dossier_text


def build_guaranteed_action_cards(audit_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Génère les cartes d'actions en 1 clic garanties selon la méthodologie des Baby Steps."""
    cards = []
    matched_aids = audit_summary.get("matched_aids", [])

    # 1. Cartes pour les aides publiques officielles détectées
    for aid in matched_aids:
        aid_id = aid.get("id", "")
        nom = aid.get("nom", "Aide publique")
        url = aid.get("url_officielle") or OFFICIAL_AID_URLS.get(aid_id, "https://www.service-public.fr")
        benefit = aid.get("gain_indicatif", "Complément financier")

        icon = "🏛️"
        btn_label = "Faire la démarche en ligne"
        if "apl" in aid_id or "logement" in aid_id or "wohngeld" in aid_id:
            icon = "🏠"
            btn_label = "Demander l'aide logement (CAF)"
        elif "prime" in aid_id or "activit" in aid_id:
            icon = "💼"
            btn_label = "Simuler la Prime d'Activité"
        elif "mobili" in aid_id:
            icon = "🎓"
            btn_label = "Dossier Mobili-Jeune (Action Logement)"
        elif "lep" in aid_id:
            continue  # Traité en action in-app

        cards.append({
            "id": f"card_{aid_id}",
            "type": "external_link",
            "icon": icon,
            "title": nom,
            "description": f"Gain indicatif : {benefit}, à confirmer par simulation. Démarche 100% en ligne.",
            "url": url,
            "button_label": btn_label
        })

    # 2. Carte in-app : Livret d'Épargne Populaire (LEP) - Priorité Baby Step argent dormant & précaution
    idle = audit_summary.get("idle_cash", 0.0)
    lep_rate = f"{LEP_ANNUAL_RATE * 100:.1f}".replace(".", ",") + " %"
    if idle > 200:
        cards.append({
            "id": "card_lep_simulator",
            "type": "in_app_dialog",
            "icon": "📈",
            "title": "Ouvrir un LEP : Placer l'argent dormant",
            "description": f"Placez vos {idle:.0f} € disponibles au-delà des dépenses du mois sur le LEP ({lep_rate} net), toujours disponibles.",
            "action_name": "open_savings_dialog",
            "button_label": "Placer mes liquidités sur le LEP"
        })
    else:
        cards.append({
            "id": "card_lep_simulator",
            "type": "in_app_dialog",
            "icon": "📈",
            "title": "Ouvrir un Livret d'Épargne Populaire (LEP)",
            "description": f"Taux réglementé de {lep_rate} net d'impôt pour bâtir votre coussin de précaution de 3 mois.",
            "action_name": "open_savings_dialog",
            "button_label": "Simuler mon ouverture de livret"
        })

    # 3. Carte in-app : Investissement en Bourse (PEA / CTO) - CONDITIONNÉ AUX 3 MOIS D'ÉPARGNE !
    if audit_summary.get("has_3m_savings", False):
        cards.append({
            "id": "card_stock_investment",
            "type": "in_app_dialog",
            "icon": "📊",
            "title": "Investir en Bourse : PEA ou Compte-Titres (CTO)",
            "description": "Vos 3 mois d'épargne de sécurité sont complets ! Passez au Baby Step suivant et valorisez votre excédent.",
            "action_name": "open_stock_investment_dialog",
            "button_label": "Simuler mon PEA / CTO"
        })

    # 4. Carte in-app : Plafonner la catégorie en surcoût si déficit ou surcoût notable
    gap_cat = audit_summary.get("gap_cat")
    if gap_cat and audit_summary.get("gap_overcost", 0) > 30:
        cards.append({
            "id": "card_ceiling_budget",
            "type": "in_app_dialog",
            "icon": "🎯",
            "title": f"Fixer un plafond d'alerte : {gap_cat}",
            "description": f"Évitez les dérapages sur ce poste qui dépasse de +{audit_summary.get('gap_overcost', 0):.0f} € la moyenne.",
            "action_name": "set_budget_alert",
            "payload": {"category": gap_cat},
            "button_label": f"Plafonner {gap_cat}"
        })

    return cards[:5]


def build_synthesis_prompt(profile: UserProfile, dossier_text: str) -> str:
    """Construit le prompt de synthèse : le LLM rédige à partir d'un dossier entièrement pré-calculé."""
    return f"""Tu es un conseiller financier chaleureux et rigoureux.
Tu t'adresses directement à {profile.name} en le tutoyant.

Voici le dossier vérifié issu de l'audit de ses comptes :

{dossier_text}

CONSIGNES DE RÉDACTION :
1. TON : chaleureux, pédagogique et concret. Tu conseilles, tu n'ordonnes pas : n'emploie pas de mots comme « interdit » ou « obligatoire ». Ne mentionne jamais le dossier, des outils ou ces consignes.

2. CHIFFRES : utilise uniquement les montants écrits dans le dossier, recopiés tels quels. N'additionne, ne soustrais et ne recalcule rien : les totaux, écarts et scénarios utiles sont déjà calculés. Si un chiffre n'est pas dans le dossier, ne le donne pas.

3. POINTS FORTS : ne cite comme point fort que des faits du dossier (postes sous la moyenne des pairs, épargne disponible s'il y en a). Le solde du compte courant n'est pas de l'épargne.

4. AIDES : cite uniquement les aides du dossier. Présente leurs montants comme des fourchettes indicatives à confirmer par une simulation, jamais comme un revenu acquis. N'affirme comme remplies que les « conditions confirmées » ; présente les « conditions à vérifier » comme des points à vérifier.

5. DÉPENSES : nomme le poste en surcoût en distinguant sa dépense totale et son écart avec les pairs. Donne 2 astuces concrètes et sans frustration, dont une appuyée sur une dépense réelle de la liste des plus grosses dépenses. Si tu chiffres l'économie, reprends l'objectif de réduction du dossier.

6. ÉPARGNE : applique la consigne d'épargne du dossier et appuie-toi sur les scénarios calculés pour dire en combien de mois le coussin peut être constitué, en précisant dans quel scénario.

7. CONCISION : le client lit d'abord « L'essentiel » ; les autres sections sont des détails qu'il ouvre s'il le souhaite. Chaque section de détail fait au plus 120 mots, sans tableau, et ne répète pas l'essentiel.

STRUCTURE ATTENDUE (utilise exactement ces 5 titres en markdown, dans cet ordre) :

## L'essentiel
(Exactement 3 puces, sans phrase d'introduction : les 3 actions prioritaires. Chaque puce suit le format « **Titre court de l'action** : détail avec son chiffre clé », en 15 mots maximum.)
## Ton Diagnostic & Tes Points Forts
## Optimisation de tes revenus & aides
## Maîtrise de tes dépenses
## Ta stratégie d'épargne & tes projets
"""


def build_report_kpis(audit_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chiffres clés et sous-titres de sections calculés par le code (jamais par le LLM)
    pour l'en-tête visuel du rapport.
    """
    margin = audit_summary.get("margin", 0.0)
    missing = audit_summary.get("missing_emergency", 0.0)

    if audit_summary.get("has_3m_savings"):
        cushion_value, cushion_hint = "Complet", "3 mois de dépenses de côté"
    else:
        cushion_value, cushion_hint = "En pause", f"il manque {fmt_eur(missing)}"
        for label, monthly in audit_summary.get("scenarios", []):
            if monthly > 0 and math.ceil(missing / monthly) <= 60:
                cushion_value = f"{math.ceil(missing / monthly)} mois"
                if "aides" in label:
                    cushion_hint = "avec économies et aides accordées"
                elif "réduction" in label:
                    cushion_hint = "avec la réduction de dépenses"
                else:
                    cushion_hint = "au rythme actuel"
                break

    sign = "+" if margin >= 0 else "−"
    tiles = [
        {"label": "Bilan du mois", "value": f"{sign}{fmt_eur(abs(margin))}",
         "hint": "excédent" if margin >= 0 else "les dépenses dépassent les revenus",
         "tone": "positive" if margin >= 0 else "negative"},
        {"label": "Épargne disponible", "value": fmt_eur(audit_summary.get("available_savings", 0.0)),
         "hint": "au-delà des dépenses du mois", "tone": "neutral"},
        {"label": "Coussin de sécurité", "value": cushion_value, "hint": cushion_hint,
         "tone": "positive" if audit_summary.get("has_3m_savings") else "neutral"},
    ]

    aids = [a for a in audit_summary.get("matched_aids", []) if a.get("id") != "fr_lep"]
    aids_high = audit_summary.get("aids_high", 0.0)
    subtitles = {
        "diagnostic": f"{fmt_eur(audit_summary.get('spent', 0.0))} dépensés pour {fmt_eur(audit_summary.get('income', 0.0))} de revenus",
        "aides": f"{len(aids)} aide{'s' if len(aids) > 1 else ''} à vérifier"
                 + (f", jusqu'à {fmt_eur(aids_high)} par mois" if aids_high else ""),
        "dépenses": f"{audit_summary.get('gap_cat', '')} : +{fmt_eur(audit_summary.get('gap_overcost', 0.0))} par rapport à tes pairs",
        "épargne": "Coussin de 3 mois complet" if audit_summary.get("has_3m_savings")
                   else f"Il manque {fmt_eur(missing)} pour ton coussin de 3 mois",
    }
    return {"tiles": tiles, "subtitles": subtitles}


def parse_summary_actions(summary: str) -> Tuple[str, List[str]]:
    """Sépare le résumé en une introduction éventuelle et la liste des actions (puces ou numéros)."""
    intro_lines, actions = [], []
    for line in (summary or "").splitlines():
        match = re.match(r"^\s*(?:[-*•]|\d+[.)])\s+(.*\S)", line)
        if match:
            actions.append(match.group(1))
        elif line.strip() and not actions:
            intro_lines.append(line.strip())
    return " ".join(intro_lines), actions


def split_report_sections(report: str) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Découpe le rapport markdown en un résumé (section « L'essentiel ») et des sections de détail
    (titre, contenu) à afficher repliées. Sans résumé identifiable, la première section en tient lieu.
    """
    parts = re.split(r"^##\s+(.+?)\s*$", report or "", flags=re.MULTILINE)
    preamble = parts[0].strip()
    sections = [(parts[i].strip(), parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]
    if not sections:
        return preamble, []

    summary_idx = next((i for i, (title, _) in enumerate(sections) if "essentiel" in title.lower()), 0)
    summary = sections.pop(summary_idx)[1]
    if preamble:
        summary = preamble + "\n\n" + summary
    return summary, sections


def clean_advisor_output(raw_text: str) -> str:
    """Supprime toute fuite de monologue interne ou mention d'outil restante."""
    cleaned = raw_text.strip()

    # Supprime d'éventuels blocs ```actions ou ```tool_call
    cleaned = re.sub(r"```(?:actions|tool_call|json)?[\s\S]*?```", "", cleaned).strip()

    # Supprime d'éventuelles phrases parasites d'outil
    parasites = [
        r"D'après l'outil [a-zA-Z0-9_]+,\s*",
        r"Selon l'outil [a-zA-Z0-9_]+,\s*",
        r"En utilisant l'outil [a-zA-Z0-9_]+,\s*",
        r"Il est important de noter que ces cartes d'actions[\s\S]*"
    ]
    for p in parasites:
        cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE).strip()

    return cleaned


def run_agentic_audit(
    hf_client: HFClient,
    db: BankBackend,
    user_id: str
) -> Generator[Dict[str, Any], None, None]:
    """
    Exécute la pipeline d'audit agentique Fact-Grounded :
    1. Émet les étapes d'investigation réelles pour l'affichage visuel (st.status).
    2. Construit le dossier certifié avec calculs mathématiques vérifiés.
    3. Génère les cartes d'actions en 1 clic garanties.
    4. Fait rédiger au LLM une synthèse chaleureuse, percutante et sans aucune hallucination.
    """
    t0 = time.time()
    profile = db.get_user_profile(user_id)

    if not hf_client.is_configured():
        yield {
            "type": "error",
            "message": "Assistant IA non disponible : clé API Groq non configurée."
        }
        return

    # Construction immédiate du dossier factuel infaillible
    audit_summary, dossier_text = build_fact_grounded_dossier(db, user_id)
    action_cards = build_guaranteed_action_cards(audit_summary)


    # Prompt de synthèse exigeant et élégant
    prompt = build_synthesis_prompt(profile, dossier_text)
    country = getattr(profile, "country", "France")

    messages = [
        ("system", f"Tu es un conseiller financier personnel bienveillant, clair et rigoureux en {country}. Tu t'adresses au client en 'tu' sans jamais parler d'outils informatiques."),
        ("user", prompt)
    ]

    try:
        response = hf_client.client.invoke(messages)
        res_content = getattr(response, "content", response)
        if isinstance(res_content, list):
            raw_text = "\n".join(str(i) for i in res_content)
        else:
            raw_text = str(res_content)
        
        final_report = clean_advisor_output(raw_text)
        hf_client.last_execution_time = time.time() - t0

        yield {
            "type": "done",
            "report": final_report,
            "actions": action_cards,
            "kpis": build_report_kpis(audit_summary),
            "steps": [
                {"tool": "get_budget_overview", "params": {}},
                {"tool": "get_peer_benchmark_comparison", "params": {}},
                {"tool": "get_largest_expenses", "params": {"type": "variable"}},
                {"tool": "detect_recurring_subscriptions", "params": {}},
                {"tool": "search_eligible_public_aids", "params": {}}
            ],
            "execution_time": hf_client.last_execution_time
        }
    except Exception as e:
        # Pas de rapport de secours : un texte non rédigé par l'IA ne doit pas être présenté comme tel
        print(f"[AgentRunner] Échec de l'appel LLM pendant l'audit : {e}")
        yield {
            "type": "error",
            "message": "Coach IA indisponible pour le moment."
        }
