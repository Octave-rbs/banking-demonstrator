# Démonstrateur Bancaire Intelligent & Partagé

Application bancaire mobile innovante développée avec **Streamlit**, **LangChain** et **Hugging Face**.

## 🌟 Fonctionnalités Clés

1. **Compte Personnel & Opérations** : Visualisation du solde courant, historique dynamique avec recherche, et partage instantané d'une dépense vers un compte commun.
2. **Compte Partagé ("Tricount Intégré")** : Gestion multi-groupes, calcul automatisé des balances nettes, algorithme d'optimisation des flux de remboursement et **virement instantané en 1 clic** soldant les dettes.
3. **Budgétisation & Benchmark Pairs** : Double vue (mois civil vs mois glissant 30 jours), répartition charges fixes vs dépenses variables, et comparateur statistique avec les pairs (Top 10% éco, Top 30% éco, Moyenne, Top 30% dép, Top 10% dép).
4. **Coach Financier IA & Scorecard** : Score de santé budgétaire instantané (/100 sur 3 piliers), rapport d'audit exécutif généré en **streaming** par un LLM (`Llama-3.1-8B-Instruct`), et chat conversationnel contextualisé avec détection d'aides publiques.
5. **Administration** : Gestion des clés API Hugging Face, réinitialisation des jeux de démo et consultation des données de référence.

## 🚀 Lancement Rapide

```bash
# Installation des dépendances
pip install -r requirements.txt

# Démarrage de l'application
streamlit run app.py
```

## 📂 Architecture Modulaire

- `app.py` : Contrôleur et routeur principal
- `models.py` : Modèles de données dataclass
- `ai/` : Services IA découplés (client HF, constructeur de contexte, streaming d'audit, chat)
- `services/` : Logique métier (gestion de compte, catégorisation, dépenses partagées, budget, benchmark, score)
- `views/` : Composants et écrans Streamlit
- `assets/` : Feuilles de style CSS
- `data/` : Jeux de transactions CSV et référentiels JSON
