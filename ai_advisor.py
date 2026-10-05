"""
Module Coach Financier IA avec LangChain et Hugging Face.
Analyse objective des finances et déduction autonome d'aides publiques (APL, etc.)
sans biais, ni prompt pré-rempli, ni faux fallback.
"""

import os
import json
import time
import traceback
from typing import Dict, List, Optional, Any
from models import UserProfile

try:
    from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


class BankingAIAdvisor:
    def __init__(self, hf_token: Optional[str] = None):
        self.hf_token = hf_token or os.environ.get("HUGGINGFACEHUB_API_TOKEN") or os.environ.get("HF_TOKEN")
        # Modèle validé
        self.default_model = "meta-llama/Llama-3.1-8B-Instruct"
        self.last_status: str = "idle"
        self.last_error: Optional[str] = None
        self.last_traceback: Optional[str] = None
        self.last_raw_response: Optional[str] = None
        self.last_execution_time: float = 0.0
        self.init_error: Optional[str] = None
        self.aids_reference: Dict[str, List[Dict]] = self._load_public_aids_reference()
        self._init_llm_client()

    def set_token(self, token: str):
        self.hf_token = token.strip() if token else None
        self._init_llm_client()

    def _init_llm_client(self):
        self.client = None
        self.init_error = None
        if LANGCHAIN_AVAILABLE and self.hf_token:
            try:
                os.environ["HF_TOKEN"] = self.hf_token
                
                llm_backend = HuggingFaceEndpoint(
                    repo_id=self.default_model,
                    task="text-generation",
                    max_new_tokens=950,
                    temperature=0.25,
                    timeout=120,
                    streaming=True
                )
                self.client = ChatHuggingFace(llm=llm_backend)
            except Exception as e:
                self.init_error = f"{type(e).__name__}: {str(e)}"
                print(f"[Erreur Init HF LangChain] {e}")
                self.client = None

    def is_hf_configured(self) -> bool:
        return bool(self.client and self.hf_token)

    def _load_public_aids_reference(self) -> Dict[str, List[Dict]]:
        """Charge le catalogue neutre des aides depuis le fichier data/public_aids_reference.json"""
        json_path = os.path.join("data", "public_aids_reference.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[AI Advisor] Erreur chargement public_aids_reference.json : {e}")
        return {}

    def _format_aids_guide(self, country: str, targeted_aids: Optional[List[Dict]] = None) -> str:
        """Formate le référentiel des aides publiques pour le pays sous forme ciblée et neutre."""
        if targeted_aids:
            matched_aids = targeted_aids
        else:
            country_key = country.strip().lower()
            matched_aids = []
            for c_name, aids in self.aids_reference.items():
                if c_name.lower() == country_key:
                    matched_aids = aids
                    break
            if not matched_aids:
                matched_aids = self.aids_reference.get("France", [])

        lines = [f"RÉFÉRENTIEL DES DISPOSITIFS SOCIAUX ANALYSÉS ({country.upper()}) :"]
        for aid in matched_aids:
            lines.append(f"• Dispositif : {aid.get('name', 'N/A')} (Organisme : {aid.get('organism', 'N/A')})")
            lines.append(f"  - Public éligible : {aid.get('target_group', '')}")
            criteria = "; ".join(aid.get('eligibility_criteria', []))
            lines.append(f"  - Critères indicatifs : {criteria}")
            lines.append(f"  - Gain indicatif : {aid.get('typical_benefit', 'Non spécifié')}")
            lines.append(f"  - Démarche : {aid.get('procedure', 'En ligne')}")
            lines.append("")
        return "\n".join(lines)

    # ==========================================
    # GÉNÉRATION DE L'AUDIT BUDGÉTAIRE RÉEL
    # ==========================================

    def generate_financial_audit(
        self,
        profile: UserProfile,
        budget_data: Dict,
        categories: Dict[str, float],
        subcategories: Dict[str, Dict[str, float]],
        peers_benchmark: Dict[str, Dict],
        extra_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Génère un diagnostic financier authentique via LLM :
        - Analyse factuelle et neutre des flux
        - Déduction autonome des aides par le LLM (sans spoiler)
        - AUCUN faux fallback déterministe en cas d'erreur
        """
        if not self.is_hf_configured():
            self.last_status = "error_no_token"
            if not self.hf_token:
                self.last_error = "Aucun token Hugging Face n'a été renseigné."
            else:
                self.last_error = f"Échec d'initialisation du modèle ({self.init_error or 'Erreur de connexion'})."
            return {
                "status": "error",
                "error": self.last_error,
                "has_structured": False,
                "raw_text": ""
            }

        t0 = time.time()
        try:
            country = getattr(profile, "country", "France")
            context = self._format_audit_context(
                profile, budget_data, categories, subcategories, peers_benchmark, extra_context=extra_context
            )
            response_text = self._call_llm_audit(context, country=country)
            self.last_execution_time = time.time() - t0
            self.last_raw_response = response_text

            if not response_text or not response_text.strip():
                self.last_status = "error_empty_response"
                self.last_error = "Le modèle Hugging Face a retourné une réponse vide (possible timeout ou surcharge de l'API)."
                return {
                    "status": "error",
                    "error": self.last_error,
                    "has_structured": False,
                    "raw_text": ""
                }

            parsed = self._parse_audit_response(response_text)
            self.last_status = "llm_success"
            self.last_error = None
            self.last_traceback = None
            parsed["status"] = "success"
            return parsed

        except Exception as e:
            self.last_execution_time = time.time() - t0
            self.last_status = "error_llm_call"
            self.last_error = f"{type(e).__name__}: {str(e)}"
            self.last_traceback = traceback.format_exc()
            print(f"[AI Advisor] Erreur d'inférence LLM Hugging Face : {self.last_error}")
            return {
                "status": "error",
                "error": self.last_error,
                "traceback": self.last_traceback,
                "has_structured": False,
                "raw_text": ""
            }

    def _format_audit_context(
        self,
        profile: UserProfile,
        budget_data: Dict,
        categories: Dict[str, float],
        subcategories: Dict[str, Dict[str, float]],
        peers: Dict[str, Dict],
        extra_context: Optional[Dict] = None
    ) -> str:
        """
        Formate un contexte 100% objectif et factuel pour le modèle :
        - Pas de mention orientée d'aides manquantes (l'absence d'APL se déduit des flux réels)
        - Injections du guide réglementaire neutre du pays
        """
        country_str = getattr(profile, "country", "France")
        custom_notes_str = profile.custom_notes.strip() if profile.custom_notes else "Aucun projet spécifique déclaré."
        
        # Données de flux entrants réels détectés
        detected_incomes = extra_context.get("detected_incomes", []) if extra_context else []
        if detected_incomes:
            incomes_str = "\n".join([f"  * {inc}" for inc in detected_incomes])
        else:
            incomes_str = f"  * Rémunération nette déclarée : {profile.monthly_net_income:.2f} €"

        # Diagnostic budgétaire
        rolling_label = budget_data.get("rolling_label", "Mois glissant (30 jours)")
        rolling_income = budget_data.get("rolling_income", profile.monthly_net_income)
        rolling_spent = budget_data.get("rolling_spent", budget_data.get("total_spent", 0.0))
        rolling_fixed = budget_data.get("rolling_fixed", 0.0)
        rolling_variable = budget_data.get("rolling_variable", 0.0)
        rolling_remaining = budget_data.get("rolling_remaining", 0.0)
        is_over_budget = budget_data.get("is_over_budget", False)
        budget_health = "Dépassement de budget (marge nette négative)" if is_over_budget else "Budget équilibré (marge positive)"

        # Positionnement par rapport aux pairs
        peer_comparison_list = extra_context.get("peer_comparison_summary", []) if extra_context else []
        if peer_comparison_list:
            peer_summary_str = "\n".join(peer_comparison_list)
        else:
            peer_summary_str = "\n".join([f"- {cat}: {spent:.2f} €" for cat, spent in categories.items()])

        # Détail des sous-catégories principales
        subcats_lines = []
        for cat, subs in subcategories.items():
            if subs:
                subs_formatted = ", ".join([f"{k}: {v:.2f} €" for k, v in subs.items()])
                subcats_lines.append(f"  * {cat} : {subs_formatted}")
        subcats_str = "\n".join(subcats_lines) if subcats_lines else "Non ventilé"

        subscriptions_str = ", ".join(extra_context.get("subscriptions", [])) if extra_context and extra_context.get("subscriptions") else "Non détectés"
        largest_expense_str = extra_context.get("largest_expense", "N/A") if extra_context else "N/A"

        # Référentiel des aides neutres ciblées
        targeted_aids = extra_context.get("targeted_aids") if extra_context else None
        aids_guide_str = self._format_aids_guide(country_str, targeted_aids=targeted_aids)

        context = f"""=== PROFIL DU CLIENT ===
- Nom : {profile.name}, {profile.age} ans
- Pays de résidence : {country_str}
- Ville : {profile.city}
- Situation familiale : {getattr(profile, 'family_situation', 'Célibataire')}
- Activité / Emploi : {getattr(profile, 'job_activity', profile.status)} ({profile.school_or_company})
- Logement : {getattr(profile, 'housing_type', 'Colocation')}
- Part de loyer débitée : {profile.rent_amount:.2f} € / mois
- Rémunération déclarée : {profile.monthly_net_income:.2f} € / mois
- Objectifs / Précisions libres du client : "{custom_notes_str}"

=== FLUX DE TRÉSORERIE RÉELS SUR LES 30 DERNIERS JOURS ===
- Entrées d'argent et revenus identifiés sur le compte bancaire :
{incomes_str}
- Dépenses totales sur 30 jours : {rolling_spent:.2f} € (Charges fixes : {rolling_fixed:.2f} €, Dépenses courantes variables : {rolling_variable:.2f} €)
- Reste à vivre actuel sur 30 jours : {rolling_remaining:.2f} €
- Diagnostic d'équilibre budgétaire : {budget_health}
- Abonnements récurrents identifiés : {subscriptions_str}
- Dépense ponctuelle la plus importante : {largest_expense_str}

=== ANALYSE COMPARATIVE AVEC LES PAIRS DU MÊME PROFIL (Île-de-France / Tranche similaire) ===
{peer_summary_str}

Détail des dépenses par sous-catégorie :
{subcats_str}

=== GUIDE DOCUMENTAIRE RÉGLEMENTAIRE (RÉFÉRENCE OFFICIELLE) ===
{aids_guide_str}
"""
        return context

    def _build_audit_prompt(self, context: str, country: str = "France") -> str:
        return f"""Tu es un coach financier bienveillant et expert en budget. Ton but est d'accompagner l'utilisateur pour assainir sa trésorerie sans le culpabiliser. 

Rédige un BILAN PERSONNEL CHALEUREUX ET PERCUTANT, spécialement adapté pour ce profil en {country}. 

{context}

CONSIGNES DE RÉDACTION ET D'EXPERTISE :
1. TON ET STYLE (CRITIQUE) :
   - Adresse-toi DIRECTEMENT à l'utilisateur en utilisant le "tu" (ou le "vous"). Ne parle jamais de lui à la troisième personne.
   - Adopte un ton encourageant, humain et direct.
   - Fais preuve d'empathie face à sa situation.
   - Utilise un format fluide : mets en gras les chiffres clés, utilise des listes à puces aérées, mais rédige des phrases naturelles de transition.

2. OPTIMISATION DES REVENUS :
   - S'il manque des aides publiques dans ses flux récents, explique comment accéder à ces aides. 
   - Donne le gain mensuel estimé en € et les 2-3 démarches exactes à suivre de façon très simple.

3. DIMINUTION DES DÉPENSES :
   - Identifie le poste où ses dépenses s'écartent de la moyenne des profils similaires. 
   - Formule 2 recommandations concrètes et chiffrées en € pour réduire ces frais dans cette catégorie pour revenir dans la moyenne. (ex: dépense mode excessive le mois dernier et livraison de nourriture)

4. ÉPARGNE & PROJETS :
   - Propose une stratégie d'épargne réaliste par rapport à son reste à vivre.
   - Suggère un support adapté et relie cet effort directement à la réussite de ses projets personnels.

STRUCTURE ATTENDUE (utilise ces titres comme trame narrative fluide) :

## Ton Diagnostic & Tes Points Forts
## Optimisation de tes revenus
## Gérer ton budget
## Ta stratégie d'épargne & tes projets
"""

    def _call_llm_audit(self, context: str, country: str = "France") -> str:
        prompt = self._build_audit_prompt(context, country=country)
        if self.client:
            messages = [
                ("system", f"Tu es un conseiller financier expert. Rédige un rapport exécutif d'audit pour un client résidant en {country}."),
                ("user", prompt)
            ]
            response = self.client.invoke(messages)
            content = getattr(response, "content", response)
            if isinstance(content, list):
                return "\n".join(item.get("text", str(item)) if isinstance(item, dict) else str(item) for item in content)
            return str(content)
        return ""

    def stream_financial_audit(
        self,
        profile: UserProfile,
        budget_data: Dict,
        categories: Dict[str, float],
        subcategories: Dict[str, Dict[str, float]],
        peers_benchmark: Dict[str, Dict],
        extra_context: Optional[Dict] = None
    ):
        """
        Générateur de tokens en streaming pour le rapport exécutif de diagnostic.
        Émet les fragments de texte en direct pour affichage via st.write_stream.
        """
        if not self.is_hf_configured():
            self.last_status = "error_no_token"
            if not self.hf_token:
                self.last_error = "Aucun token Hugging Face n'a été renseigné."
            else:
                self.last_error = f"Échec d'initialisation du modèle ({self.init_error or 'Erreur de connexion'})."
            yield f"⚠️ **Assistant IA non disponible :** {self.last_error}\n\nVeuillez renseigner votre token Hugging Face pour lancer l'analyse."
            return

        t0 = time.time()
        country = getattr(profile, "country", "France")
        context = self._format_audit_context(
            profile, budget_data, categories, subcategories, peers_benchmark, extra_context=extra_context
        )
        prompt = self._build_audit_prompt(context, country=country)
        messages = [
            ("system", f"Tu es un conseiller financier expert. Rédige un rapport exécutif d'audit clair et bienveillant pour un client en {country}."),
            ("user", prompt)
        ]

        full_chunks = []
        try:
            for chunk in self.client.stream(messages):
                text_chunk = getattr(chunk, "content", chunk)
                if isinstance(text_chunk, list):
                    text_chunk = "\n".join(item.get("text", str(item)) if isinstance(item, dict) else str(item) for item in text_chunk)
                else:
                    text_chunk = str(text_chunk)
                if text_chunk:
                    full_chunks.append(text_chunk)
                    yield text_chunk

            self.last_execution_time = time.time() - t0
            self.last_raw_response = "".join(full_chunks)
            self.last_status = "llm_success"
            self.last_error = None
        except Exception as e:
            try:
                response = self.client.invoke(messages)
                content = getattr(response, "content", response)
                if isinstance(content, list):
                    res_text = "\n".join(item.get("text", str(item)) if isinstance(item, dict) else str(item) for item in content)
                else:
                    res_text = str(content)
                self.last_execution_time = time.time() - t0
                self.last_raw_response = res_text
                self.last_status = "llm_success"
                self.last_error = None
                yield res_text
            except Exception as e2:
                self.last_execution_time = time.time() - t0
                self.last_status = "error_llm_call"
                self.last_error = f"{type(e2).__name__}: {str(e2)}"
                self.last_traceback = traceback.format_exc()
                yield f"\n\n❌ **Erreur d'inférence LLM Hugging Face :** {self.last_error}"

    def _parse_audit_response(self, text: str) -> Dict[str, Any]:
        """
        Découpe la réponse du modèle de façon souple et résiliente,
        tout en préservant le texte intégral propre.
        """
        results: Dict[str, Any] = {
            "well_managed": "",
            "income_boost": "",
            "expense_reduction": "",
            "savings": "",
            "raw_text": text.strip(),
            "has_structured": False
        }
        if not text or not text.strip():
            return results

        import re
        import unicodedata

        def remove_accents(input_str: str) -> str:
            nfkd = unicodedata.normalize('NFKD', input_str)
            return ''.join([c for c in nfkd if not unicodedata.combining(c)])

        def match_section(line: str) -> Optional[str]:
            s = line.strip()
            if not s or len(s) > 130:
                return None
            if not (s.startswith('#') or s.startswith('**')):
                return None
            norm = remove_accents(re.sub(r'[*#_\[\]:\-0-9.]', ' ', s).strip().lower())
            
            # Reconnaissance des 4 grandes sections
            if any(w in norm for w in ['reconnaissance', 'diagnostic', 'point fort', 'situation', 'bien gere', 'global']):
                return 'well_managed'
            if any(w in norm for w in ['revenu', 'aide', 'allocation', 'gain', 'optimisation des revenus', 'ressource', 'subvention']):
                return 'income_boost'
            if any(w in norm for w in ['depense', 'diminution', 'reduction', 'economie', 'poste prioritaire', 'charge']):
                return 'expense_reduction'
            if any(w in norm for w in ['epargne', 'tresorerie', 'placement', 'livret', 'lep']):
                return 'savings'
            return None

        lines = text.strip().split('\n')
        current_section = None
        buckets = {'well_managed': [], 'income_boost': [], 'expense_reduction': [], 'savings': [], 'intro': []}

        for line in lines:
            sec = match_section(line)
            if sec:
                current_section = sec
            else:
                if current_section:
                    buckets[current_section].append(line)
                else:
                    if line.strip():
                        buckets['intro'].append(line)

        for k in ['well_managed', 'income_boost', 'expense_reduction', 'savings']:
            results[k] = "\n".join(buckets[k]).strip()

        # Si du texte d'intro existe, l'ajouter au premier bloc
        if buckets['intro']:
            intro_txt = "\n".join(buckets['intro']).strip()
            if results['well_managed']:
                results['well_managed'] = intro_txt + "\n\n" + results['well_managed']
            else:
                results['well_managed'] = intro_txt

        has_structured = any(bool(results[k]) for k in ['well_managed', 'income_boost', 'expense_reduction', 'savings'])
        results['has_structured'] = has_structured

        # Rétro-compatibilité des clés
        results["cost_reduction"] = results["expense_reduction"]
        results["public_aids"] = results["income_boost"]
        results["savings_strategy"] = results["savings"]

        return results

    # ==========================================
    # ASSISTANT CONVERSATIONNEL INTERACTIF
    # ==========================================

    def ask_advisor(self, question: str, profile: UserProfile, budget_summary: str = "") -> str:
        """
        Répond aux questions de l'utilisateur via le LLM réel.
        Aucune réponse fictive hardcodée : si non configuré ou échec API, une notification explicite est retournée.
        """
        if not self.is_hf_configured():
            return (
                "⚠️ **Assistant IA non connecté** : Aucun token Hugging Face n'est actuellement configuré. "
                "Veuillez renseigner un token Hugging Face valide dans l'application pour activer le dialogue avec le coach."
            )

        country = getattr(profile, "country", "France")
        family_sit = getattr(profile, "family_situation", "Célibataire")
        job = getattr(profile, "job_activity", profile.status)
        housing = getattr(profile, "housing_type", "Colocation")
        custom_notes = getattr(profile, "custom_notes", "").strip()
        aids_guide = self._format_aids_guide(country)

        system_prompt = f"""Tu es un coach financier expert et bienveillant.
Profil client : {profile.name}, {profile.age} ans.
Pays de résidence : {country}.
Situation familiale : {family_sit}.
Emploi / Formation : {job} ({profile.school_or_company}).
Logement : {housing} à {profile.city} (Loyer : {profile.rent_amount:.0f} € / mois).
Revenu net mensuel déclaré : {profile.monthly_net_income:.0f} € / mois.
Objectifs / Précisions client : "{custom_notes or 'Aucune précision'}".
Contexte bancaire récent : {budget_summary}.

{aids_guide}

Règles de conseil :
- Adapte rigoureusement toutes tes réponses, démarches et conseils aux dispositifs applicables en {country}.
- Réponds à la question de l'utilisateur de façon précise, personnalisée, chiffrée et encourageante.
- Appuies toi sur les informations spécifique du client pour lui répondre de façon personnalisée"""

        try:
            messages = [
                ("system", system_prompt),
                ("user", question)
            ]
            response = self.client.invoke(messages)
            content = getattr(response, "content", response)
            if isinstance(content, list):
                return "\n".join(item.get("text", str(item)) if isinstance(item, dict) else str(item) for item in content)
            return str(content)
        except Exception as e:
            return f"⚠️ **Erreur lors de la communication avec le modèle IA Hugging Face** : {type(e).__name__} - {str(e)}"