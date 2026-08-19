import pytest

from app.domain.models import Entity
from app.services.redaction import RedactionService, strategy_names

TEXT = "Joko lahir di Bandung, HP 081234567890, email joko@mail.co"
ENTITIES = [
    Entity(0, 4, "PER", "Joko", 0.99),
    Entity(14, 21, "LOC", "Bandung", 0.95),
    Entity(26, 38, "PHONE", "081234567890", 0.99),
    Entity(46, 58, "EMAIL", "joko@mail.co", 0.99),
]


def test_every_registered_strategy_runs():
    service = RedactionService()
    for name in strategy_names():
        result = service.apply(TEXT, ENTITIES, strategy=name)
        assert result.replaced == len(ENTITIES)
        assert "Joko" not in result.text or name == "partial"


def test_mask_preserves_length_and_removes_values():
    result = RedactionService().apply(TEXT, ENTITIES, strategy="mask")
    assert len(result.text) == len(TEXT)
    assert "081234567890" not in result.text


def test_label_strategy_names_the_types():
    result = RedactionService().apply(TEXT, ENTITIES, strategy="label")
    assert result.text.startswith("[PER] lahir di [LOC]")


def test_partial_keeps_phone_suffix_and_email_domain():
    result = RedactionService().apply(TEXT, ENTITIES, strategy="partial")
    assert "7890" in result.text
    assert "@mail.co" in result.text
    assert "joko@mail.co" not in result.text


def test_pseudonym_is_stable_for_equal_values():
    service = RedactionService(salt="pepper")
    pair = [Entity(0, 4, "PER", "Joko", 0.9), Entity(9, 13, "PER", "Joko", 0.9)]
    first = service.apply("Joko dan Joko", pair, strategy="pseudonym")
    tokens = [part for part in first.text.split() if part.startswith("PER_")]
    assert len(tokens) == 2 and tokens[0] == tokens[1]


def test_salt_changes_the_pseudonym():
    joko = [Entity(0, 4, "PER", "Joko", 0.9)]
    one = RedactionService(salt="a").apply("Joko", joko, strategy="pseudonym")
    two = RedactionService(salt="b").apply("Joko", joko, strategy="pseudonym")
    assert one.text != two.text


def test_sensitivity_filter_keeps_low_risk_text():
    result = RedactionService().apply(TEXT, ENTITIES, strategy="label", min_sensitivity=4)
    assert "Bandung" in result.text
    assert "[PER]" in result.text


def test_mapping_is_opt_in():
    service = RedactionService()
    assert service.apply(TEXT, ENTITIES).mapping == {}
    assert service.apply(TEXT, ENTITIES, include_mapping=True).mapping


def test_unknown_strategy_is_rejected():
    with pytest.raises(ValueError):
        RedactionService().apply(TEXT, ENTITIES, strategy="nope")
