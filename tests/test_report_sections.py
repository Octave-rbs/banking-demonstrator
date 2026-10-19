from ai.agent_runner import split_report_sections


def test_summary_is_extracted_and_details_kept_in_order():
    report = (
        "## L'essentiel\nTu es en déficit.\n- Action 1\n\n"
        "## Ton Diagnostic & Tes Points Forts\nDétail A\n\n"
        "## Maîtrise de tes dépenses\nDétail B"
    )
    summary, sections = split_report_sections(report)
    assert summary.startswith("Tu es en déficit.")
    assert [t for t, _ in sections] == ["Ton Diagnostic & Tes Points Forts", "Maîtrise de tes dépenses"]
    assert sections[1][1] == "Détail B"


def test_first_section_is_summary_when_no_essentiel_title():
    summary, sections = split_report_sections("Salut Paul\n## Diagnostic\nA\n## Dépenses\nB")
    assert summary == "Salut Paul\n\nA"
    assert sections == [("Dépenses", "B")]


def test_report_without_titles_is_shown_whole():
    assert split_report_sections("Texte libre") == ("Texte libre", [])


def test_summary_actions_are_parsed_from_bullets_and_numbers():
    from ai.agent_runner import parse_summary_actions
    intro, actions = parse_summary_actions("Petit intro\n- **Réduire** : 84 €\n2. **LEP** : 1 379 €\n* **Aides** : à vérifier")
    assert intro == "Petit intro"
    assert actions == ["**Réduire** : 84 €", "**LEP** : 1 379 €", "**Aides** : à vérifier"]


def test_kpis_come_from_the_dossier(backend):
    from ai.agent_runner import build_fact_grounded_dossier, build_report_kpis
    summary, _ = build_fact_grounded_dossier(backend, "u1")
    kpis = build_report_kpis(summary)
    values = [t["value"] for t in kpis["tiles"]]
    assert values[0] == "−118,55 €"
    assert values[1] == "1 378,77 €"
    assert values[2] == "13 mois"
    assert kpis["subtitles"]["aides"] == "3 aides à vérifier, jusqu'à 560,00 € par mois"
