"""Readability metrics for individual post texts.

Pure functions, no database dependency. Computes numeric metrics
that help LLMs understand post characteristics without re-analyzing
raw text on every query.
"""

import re
import unicodedata


def compute_readability(text: str) -> dict:
    """Compute readability metrics for a single text.

    Returns a dict with: flesch_kincaid_grade, avg_sentence_length,
    vocab_richness, emoji_density, hashtag_count, word_count.
    """
    if not text or not text.strip():
        return {
            "flesch_kincaid_grade": 0.0,
            "avg_sentence_length": 0.0,
            "vocab_richness": 0.0,
            "emoji_density": 0.0,
            "hashtag_count": 0,
            "word_count": 0,
        }

    words = re.findall(r"[a-zA-ZàèéìòùÀÈÉÌÒÙ'']+", text)
    word_count = len(words)

    if word_count == 0:
        return {
            "flesch_kincaid_grade": 0.0,
            "avg_sentence_length": 0.0,
            "vocab_richness": 0.0,
            "emoji_density": _emoji_density(text),
            "hashtag_count": _hashtag_count(text),
            "word_count": 0,
        }

    sentences = _split_sentences(text)
    sentence_count = max(len(sentences), 1)
    syllable_count = sum(_count_syllables(w) for w in words)

    avg_sentence_length = round(word_count / sentence_count, 1)
    fk_grade = round(
        0.39 * (word_count / sentence_count)
        + 11.8 * (syllable_count / word_count)
        - 15.59,
        1,
    )

    unique_words = len({w.lower() for w in words})
    vocab_richness = round(unique_words / word_count, 3)

    return {
        "flesch_kincaid_grade": max(fk_grade, 0.0),
        "avg_sentence_length": avg_sentence_length,
        "vocab_richness": vocab_richness,
        "emoji_density": _emoji_density(text),
        "hashtag_count": _hashtag_count(text),
        "word_count": word_count,
    }


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using punctuation boundaries."""
    parts = re.split(r"[.!?]+(?:\s|$)|\n\n+", text)
    return [p.strip() for p in parts if p and p.strip()]


def _count_syllables(word: str) -> int:
    """Estimate syllable count using vowel-group heuristic."""
    word = word.lower().strip()
    if len(word) <= 2:
        return 1

    # Remove trailing silent-e
    if word.endswith("e") and not word.endswith("le"):
        word = word[:-1]

    vowel_groups = re.findall(r"[aeiouyàèéìòù]+", word)
    count = len(vowel_groups)

    # Adjust for common patterns
    if word.endswith("ed") and count > 1:
        count -= 1

    return max(count, 1)


def _emoji_density(text: str) -> float:
    """Ratio of emoji characters to total characters."""
    if not text:
        return 0.0
    emoji_count = sum(
        1
        for ch in text
        if unicodedata.category(ch) in ("So", "Sk")
        or "\U0001f300" <= ch <= "\U0001faff"
    )
    return round(emoji_count / len(text), 4)


def _hashtag_count(text: str) -> int:
    """Count hashtags in text."""
    return len(re.findall(r"#\w+", text))
