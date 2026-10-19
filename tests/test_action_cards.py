import pytest

pytest.importorskip("streamlit")

from ai.agent_runner import extract_action_cards  # noqa: E402
from ai.tools import OFFICIAL_AID_URLS  # noqa: E402


def test_llm_urls_are_replaced_by_official_ones():
    text = 'Conseil\n```actions\n[{"id": "fr_apl", "type": "external_link", "url": "https://phishing.example"}]\n```'
    cleaned, cards = extract_action_cards(text)
    assert cleaned == "Conseil"
    assert cards[0]["url"] == OFFICIAL_AID_URLS["fr_apl"]


def test_unknown_cards_are_dropped():
    text = ('```actions\n['
            '{"id": "inconnu", "type": "external_link", "url": "https://phishing.example"},'
            '{"type": "in_app_dialog", "action_name": "wire_money"},'
            '{"type": "in_app_dialog", "action_name": "open_savings_dialog"}'
            ']\n```')
    _, cards = extract_action_cards(text)
    assert cards == [{"type": "in_app_dialog", "action_name": "open_savings_dialog"}]
