from src.blog.publisher.webflow import _make_slug, _truncate_title


# --- _make_slug ---

def test_make_slug_spaces_to_hyphens():
    assert _make_slug("Hello World") == "hello-world"


def test_make_slug_removes_special_chars():
    assert _make_slug("AI: The Future!") == "ai-the-future"


def test_make_slug_lowercase():
    assert _make_slug("GPT-5 Is Here") == "gpt-5-is-here"


def test_make_slug_truncates_at_60():
    long_title = "word " * 30
    assert len(_make_slug(long_title)) <= 60


def test_make_slug_truncates_at_word_boundary():
    slug = _make_slug("the quick brown fox jumps over the lazy dog and then some more words here")
    assert not slug.endswith("-")
    assert len(slug) <= 60


def test_make_slug_no_leading_trailing_hyphens():
    slug = _make_slug("  ...Leading and trailing...  ")
    assert not slug.startswith("-")
    assert not slug.endswith("-")


# --- _truncate_title ---

def test_truncate_title_under_limit():
    assert _truncate_title("Short title") == "Short title"


def test_truncate_title_at_word_boundary():
    long = "NVIDIA Launches Nemotron 3 Nano Omni Model Unifying Vision Audio and Language"
    result = _truncate_title(long)
    assert len(result) <= 60
    assert not result.endswith(" ")


def test_truncate_title_exact_limit():
    title = "a" * 60
    assert _truncate_title(title) == title
