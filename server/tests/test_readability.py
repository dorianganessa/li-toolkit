"""Tests for the readability metrics module."""

from readability import (
    _count_syllables,
    _emoji_density,
    _hashtag_count,
    _split_sentences,
    compute_readability,
)

# ---------------------------------------------------------------------------
# compute_readability — integration
# ---------------------------------------------------------------------------


class TestComputeReadability:
    def test_empty_string(self):
        result = compute_readability("")
        assert result["flesch_kincaid_grade"] == 0.0
        assert result["word_count"] == 0
        assert result["avg_sentence_length"] == 0.0
        assert result["vocab_richness"] == 0.0

    def test_whitespace_only(self):
        result = compute_readability("   \n\n  ")
        assert result["word_count"] == 0

    def test_simple_sentence(self):
        result = compute_readability("The cat sat on the mat.")
        assert result["word_count"] == 6
        assert result["avg_sentence_length"] == 6.0
        assert result["flesch_kincaid_grade"] >= 0

    def test_two_sentences(self):
        result = compute_readability("Hello world. This is a test.")
        assert result["avg_sentence_length"] == 3.0  # 6 words / 2 sentences

    def test_complex_text(self):
        text = (
            "The implementation of sophisticated algorithms requires "
            "extensive computational resources. Furthermore, optimization "
            "techniques must be carefully considered."
        )
        result = compute_readability(text)
        # Complex multi-syllable text: FK grade should be 10+
        assert result["flesch_kincaid_grade"] >= 10
        assert result["avg_sentence_length"] >= 5

    def test_vocab_richness_all_unique(self):
        result = compute_readability("each word here differs completely")
        assert result["vocab_richness"] == 1.0

    def test_vocab_richness_repetitive(self):
        result = compute_readability("the the the the the")
        assert result["vocab_richness"] < 0.5

    def test_emoji_included(self):
        result = compute_readability("Great post! 🔥🚀")
        assert result["emoji_density"] > 0

    def test_hashtags_counted(self):
        result = compute_readability("Check out #python and #fastapi today")
        assert result["hashtag_count"] == 2

    def test_no_hashtags(self):
        result = compute_readability("No hashtags here")
        assert result["hashtag_count"] == 0

    def test_only_emoji(self):
        result = compute_readability("🔥🚀✨")
        assert result["word_count"] == 0
        assert result["emoji_density"] > 0

    def test_linkedin_style_post(self):
        text = (
            "I just shipped a new feature!\n\n"
            "Here's what I learned:\n\n"
            "1. Start small\n"
            "2. Get feedback early\n"
            "3. Iterate fast\n\n"
            "#startup #engineering"
        )
        result = compute_readability(text)
        assert result["word_count"] > 0
        assert result["hashtag_count"] == 2
        assert result["flesch_kincaid_grade"] >= 0

    def test_fk_grade_not_negative(self):
        result = compute_readability("Hi.")
        assert result["flesch_kincaid_grade"] >= 0


# ---------------------------------------------------------------------------
# _split_sentences
# ---------------------------------------------------------------------------


class TestSplitSentences:
    def test_period(self):
        assert len(_split_sentences("One. Two. Three.")) == 3

    def test_question_mark(self):
        assert len(_split_sentences("What? Really? Yes.")) == 3

    def test_exclamation(self):
        assert len(_split_sentences("Wow! Amazing! Great.")) == 3

    def test_newline_paragraphs(self):
        assert len(_split_sentences("First paragraph\n\nSecond paragraph")) == 2

    def test_no_punctuation(self):
        result = _split_sentences("just a sentence without punctuation")
        assert len(result) == 1


# ---------------------------------------------------------------------------
# _count_syllables
# ---------------------------------------------------------------------------


class TestCountSyllables:
    def test_one_syllable(self):
        assert _count_syllables("cat") == 1
        assert _count_syllables("dog") == 1

    def test_two_syllables(self):
        assert _count_syllables("happy") == 2
        assert _count_syllables("python") == 2

    def test_three_syllables(self):
        assert _count_syllables("beautiful") == 3

    def test_silent_e(self):
        assert _count_syllables("make") == 1
        assert _count_syllables("time") == 1

    def test_short_word(self):
        assert _count_syllables("I") == 1
        assert _count_syllables("an") == 1

    def test_minimum_one(self):
        assert _count_syllables("x") >= 1


# ---------------------------------------------------------------------------
# _emoji_density
# ---------------------------------------------------------------------------


class TestEmojiDensity:
    def test_no_emoji(self):
        assert _emoji_density("hello world") == 0.0

    def test_empty(self):
        assert _emoji_density("") == 0.0

    def test_some_emoji(self):
        # "hello 🔥" = 7 chars, 1 emoji → 1/7 ≈ 0.1429
        density = _emoji_density("hello 🔥")
        assert 0.1 < density < 0.2


# ---------------------------------------------------------------------------
# _hashtag_count
# ---------------------------------------------------------------------------


class TestHashtagCount:
    def test_multiple_hashtags(self):
        assert _hashtag_count("#one #two #three") == 3

    def test_no_hashtags(self):
        assert _hashtag_count("no hashtags") == 0

    def test_hash_without_word(self):
        assert _hashtag_count("# alone") == 0
