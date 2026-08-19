from app.services.chunking import WindowChunker


def test_short_text_is_one_chunk():
    chunks = WindowChunker(window=100, overlap=10).split("halo dunia")
    assert len(chunks) == 1
    assert chunks[0].offset == 0


def test_empty_text_yields_nothing():
    assert WindowChunker().split("") == []


def test_chunks_cover_the_whole_text():
    text = " ".join(f"kata{i}" for i in range(400))
    chunks = WindowChunker(window=200, overlap=40).split(text)
    assert len(chunks) > 1
    for chunk in chunks:
        assert text[chunk.offset : chunk.offset + len(chunk.text)] == chunk.text
    assert chunks[-1].offset + len(chunks[-1].text) == len(text)


def test_windows_overlap_and_advance():
    text = "a" * 50 + " " + "b" * 500
    chunks = WindowChunker(window=200, overlap=50).split(text)
    offsets = [chunk.offset for chunk in chunks]
    assert offsets == sorted(offsets)
    assert len(set(offsets)) == len(offsets)


def test_invalid_overlap_rejected():
    for window, overlap in ((0, 0), (100, 100), (100, -1)):
        try:
            WindowChunker(window=window, overlap=overlap)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {window}/{overlap}")
