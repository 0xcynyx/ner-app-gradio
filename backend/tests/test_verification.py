from app.domain.models import Entity
from app.services.verification import RegexVerifier


def entity(start, end, label, text, score=0.8):
    return Entity(start, end, label, text, score)


def test_truncated_email_is_repaired_to_full_match():
    text = "email saya cindy.a+test@example.co.id ya"
    found = text.index("cindy")
    repaired = RegexVerifier().verify(text, [entity(found, found + 5, "EMAIL", "cindy")])
    email = next(e for e in repaired if e.label == "EMAIL")
    assert email.text == "cindy.a+test@example.co.id"
    assert email.verified is True


def test_spaced_phone_is_recovered_when_model_misses_it():
    text = "hubungi +62 812-3456-7890 sekarang"
    found = RegexVerifier().verify(text, [])
    assert [e.text for e in found if e.label == "PHONE"] == ["+62 812-3456-7890"]


def test_grouped_national_id_is_recovered():
    text = "NIK 3204 0125 0990 0001 terdaftar"
    found = RegexVerifier().verify(text, [])
    assert [e.text for e in found if e.label == "SSN"] == ["3204 0125 0990 0001"]


def test_unstructured_labels_are_left_alone():
    text = "Joko Widodo hadir"
    original = entity(0, 11, "PER", "Joko Widodo")
    assert RegexVerifier().verify(text, [original])[0] == original


def test_recovery_can_be_disabled():
    text = "email a@b.co"
    assert RegexVerifier(recover_missing=False).verify(text, []) == []


def test_fragments_snapped_to_one_match_are_deduplicated():
    """Repair maps every overlapping fragment onto the same regex match, so copies must collapse."""
    text = "Balasan dari joko@mail.com diterima"
    start = text.index("joko")
    fragments = [
        entity(start, start + 4, "EMAIL", "joko"),
        entity(start + 5, start + 13, "EMAIL", "mail.com"),
    ]
    found = RegexVerifier().verify(text, fragments)
    emails = [e for e in found if e.label == "EMAIL"]
    assert len(emails) == 1
    assert emails[0].text == "joko@mail.com"


def test_contained_duplicate_of_same_label_is_dropped():
    text = "hubungi 081234567890 sekarang"
    inner = entity(8, 12, "PHONE", "0812")
    found = RegexVerifier(recover_missing=False).verify(text, [inner, entity(8, 20, "PHONE", "081234567890")])
    assert len([e for e in found if e.label == "PHONE"]) == 1
