from mdsearch.chunking import chunk_text


def test_empty_string_returns_no_chunks():
    assert chunk_text("") == []


def test_short_single_paragraph_is_one_chunk():
    text = "Just a short paragraph with no headings at all."
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_heading_count_drives_chunk_count():
    # Three headings, each followed by enough content to survive the
    # length filter. Only headings after the first start a new chunk, so
    # N headings (each with a body) yields N chunks.
    text = (
        "# Heading One\n"
        "Some body content for the first section.\n"
        "# Heading Two\n"
        "Some body content for the second section.\n"
        "# Heading Three\n"
        "Some body content for the third section.\n"
    )
    chunks = chunk_text(text)
    assert len(chunks) == 3
    assert chunks[0].startswith("# Heading One")
    assert chunks[1].startswith("# Heading Two")
    assert chunks[2].startswith("# Heading Three")


def test_tiny_chunks_are_filtered_out():
    # A heading with only a couple of characters of body text produces a
    # chunk that is <= 5 chars after stripping, and should be dropped.
    text = "# H\na\n# Real Heading\nThis section has plenty of real content in it.\n"
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0].startswith("# Real Heading")


def test_hard_split_without_heading():
    # No '#' anywhere, but the text is much longer than max_chars, so it
    # must be split purely on length.
    line = "word " * 20  # 100 chars per line
    text = "\n".join([line] * 15)  # ~1500 chars, no headings
    chunks = chunk_text(text, max_chars=100)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) > 5
