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
