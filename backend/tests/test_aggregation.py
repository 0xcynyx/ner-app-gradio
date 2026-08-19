from app.domain.models import RawSpan
from app.services.aggregation import SpanAggregator, hydrate


def build(text, spans, min_score=0.5):
    aggregator = SpanAggregator()
    return hydrate(text, aggregator.build(text, spans, min_score))


def test_bio_prefixes_collapse_to_type():
    text = "Joko Widodo hadir"
    entities = build(text, [RawSpan(0, 4, "B-PER", 0.9), RawSpan(5, 11, "I-PER", 0.9)])
    assert [entity.label for entity in entities] == ["PER"]
    assert entities[0].text == "Joko Widodo"


def test_trailing_punctuation_is_trimmed():
    text = "Ia lahir di Bandung."
    entities = build(text, [RawSpan(12, 20, "LOC", 0.9)])
    assert entities[0].text == "Bandung"


def test_weak_spans_are_filtered():
    text = "Joko hadir"
    assert build(text, [RawSpan(0, 4, "PER", 0.2)], min_score=0.5) == []


def test_duplicates_from_overlapping_windows_merge():
    text = "Joko Widodo hadir"
    spans = [RawSpan(0, 11, "PER", 0.8), RawSpan(0, 11, "PER", 0.95)]
    entities = build(text, spans)
    assert len(entities) == 1
    assert entities[0].score == 0.95


def test_conflicting_labels_keep_the_stronger_span():
    text = "Bandung ramai"
    entities = build(text, [RawSpan(0, 7, "LOC", 0.9), RawSpan(0, 7, "PER", 0.4)])
    assert [entity.label for entity in entities] == ["LOC"]


def test_separate_people_are_not_glued_together():
    text = "Joko dan Prabowo hadir"
    entities = build(text, [RawSpan(0, 4, "PER", 0.9), RawSpan(9, 16, "PER", 0.9)])
    assert [entity.text for entity in entities] == ["Joko", "Prabowo"]


def test_offsets_out_of_range_are_clamped():
    text = "Joko"
    entities = build(text, [RawSpan(0, 99, "PER", 0.9)])
    assert entities[0].end == len(text)


def test_subword_fragments_of_one_word_merge():
    """The model tags each subword with B-, so zero gap pieces must rejoin."""
    text = "Dewi Lestari lahir"
    spans = [RawSpan(0, 4, "B-PER", 0.9), RawSpan(5, 8, "B-PER", 0.9), RawSpan(8, 12, "B-PER", 0.9)]
    entities = build(text, spans)
    assert [e.text for e in entities] == ["Dewi Lestari"]


def test_single_space_joins_a_fragmented_name():
    text = "Joko Widodo hadir"
    spans = [RawSpan(0, 4, "B-PER", 0.9), RawSpan(5, 8, "B-PER", 0.9), RawSpan(8, 11, "B-PER", 0.9)]
    assert [e.text for e in build(text, spans)] == ["Joko Widodo"]


def test_words_between_entities_still_prevent_merging():
    text = "Joko dan Prabowo hadir"
    spans = [RawSpan(0, 4, "B-PER", 0.9), RawSpan(9, 16, "B-PER", 0.9)]
    assert [e.text for e in build(text, spans)] == ["Joko", "Prabowo"]


def test_digit_fragments_of_one_identifier_merge():
    text = "NIK 3175 0405 8800 0012 aktif"
    spans = [
        RawSpan(4, 6, "B-SSN", 0.9), RawSpan(6, 8, "B-SSN", 0.9), RawSpan(9, 13, "B-SSN", 0.9),
        RawSpan(14, 18, "B-SSN", 0.9), RawSpan(19, 23, "B-SSN", 0.9),
    ]
    assert [e.text for e in build(text, spans)] == ["3175 0405 8800 0012"]
