from app.adapters.memory_cache import LruCache
from app.services.aggregation import SpanAggregator
from app.services.analyzer import AnalyzerService
from app.services.chunking import WindowChunker
from app.services.verification import RegexVerifier
from tests.stubs import MarkerClassifier


def make(classifier, window=1200, overlap=200, cache=None, max_characters=50_000):
    return AnalyzerService(
        classifier=classifier,
        chunker=WindowChunker(window=window, overlap=overlap),
        aggregator=SpanAggregator(min_score=0.5),
        verifier=RegexVerifier(),
        cache=cache,
        max_characters=max_characters,
    )


def test_entity_offsets_point_at_the_right_characters():
    text = "Joko lahir di Bandung"
    analysis = make(MarkerClassifier({"Joko": "PER", "Bandung": "LOC"})).analyze(text)
    for entity in analysis.entities:
        assert text[entity.start : entity.end] == entity.text


def test_offsets_stay_absolute_across_windows():
    """A marker far into a long document must keep its true document offset."""
    filler = "kata " * 600
    text = f"{filler}Joko"
    analysis = make(MarkerClassifier({"Joko": "PER"}), window=300, overlap=60).analyze(text)
    people = [e for e in analysis.entities if e.label == "PER"]
    assert len(people) == 1
    assert people[0].start == text.index("Joko")
    assert text[people[0].start : people[0].end] == "Joko"
    assert analysis.stats.chunks > 1


def test_entity_repeated_in_overlap_is_not_double_counted():
    filler = "x " * 200
    text = f"{filler}Bandung{filler}"
    classifier = MarkerClassifier({"Bandung": "LOC"})
    analysis = make(classifier, window=120, overlap=60).analyze(text)
    assert len([e for e in analysis.entities if e.label == "LOC"]) == 1


def test_blank_text_returns_empty_analysis():
    analysis = make(MarkerClassifier({"Joko": "PER"})).analyze("   ")
    assert analysis.entities == []
    assert analysis.stats.total == 0
    assert analysis.stats.risk == 0


def test_text_over_the_limit_is_flagged_truncated():
    analysis = make(MarkerClassifier({}), max_characters=10).analyze("a" * 50)
    assert analysis.truncated is True
    assert analysis.stats.characters == 10


def test_cache_prevents_a_second_inference_pass():
    classifier = MarkerClassifier({"Joko": "PER"})
    service = make(classifier, cache=LruCache(8))
    service.analyze("Joko hadir")
    first = len(classifier.calls)
    service.analyze("Joko hadir")
    assert len(classifier.calls) == first


def test_threshold_is_part_of_the_cache_key():
    classifier = MarkerClassifier({"Joko": "PER"})
    service = make(classifier, cache=LruCache(8))
    service.analyze("Joko hadir", min_score=0.5)
    before = len(classifier.calls)
    service.analyze("Joko hadir", min_score=0.95)
    assert len(classifier.calls) > before


def test_risk_rises_with_a_national_id_present():
    low = make(MarkerClassifier({"pria": "GENDER"})).analyze("pria")
    high = make(MarkerClassifier({})).analyze("NIK 3204012509900001")
    assert high.stats.risk > low.stats.risk
