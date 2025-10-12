"""Utilities for preparing, filtering, and clustering keyword phrases.

These tools operate purely on text data and do not touch network resources.
They are intended to support the workflow described in the project notes:
 - mass ingestion of masks/phrases;
 - combinator generation of phrase variations;
 - normalisation and cleaning (deduplication, stop-words, etc.);
 - light-weight clustering/grouping based on token overlap.

All functions are deterministic and side-effect free so they can be unit-tested
independently of the GUI or worker processes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Callable, Iterable, Iterator, Sequence
import re

__all__ = [
    "NormalizationOptions",
    "FilterOptions",
    "generate_combinations",
    "normalize_phrases",
    "filter_phrases",
    "tokenize",
    "cluster_phrases",
    "Cluster",
    "walk_clusters",
]

# ---------------------------------------------------------------------------
# Normalisation primitives
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class NormalizationOptions:
    """Options that control basic phrase clean-up."""

    lowercase: bool = True
    collapse_whitespace: bool = True
    strip_punctuation: bool = False
    deduplicate: bool = True
    strip_chars: str = "\u00a0\u202f\u2009\u2005"  # common NBSP variants

    def apply(self, phrase: str) -> str:
        if self.strip_chars:
            for ch in self.strip_chars:
                phrase = phrase.replace(ch, " ")
        phrase = phrase.strip()
        if self.collapse_whitespace:
            phrase = re.sub(r"\s+", " ", phrase)
        if self.lowercase:
            phrase = phrase.lower()
        if self.strip_punctuation:
            phrase = re.sub(r'[^\w\s]+', ' ', phrase)
        return phrase


_PUNCT_RE = re.compile(r'[^\w\s]+', flags=re.UNICODE)
_TOKEN_RE = re.compile(r"[\w-]+", flags=re.UNICODE)


@dataclass(slots=True)
class FilterOptions:
    """Business rules for filtering raw phrases."""

    min_length: int = 0
    max_length: int | None = None
    allow_digits: bool = True
    allow_punctuation: bool = True
    include_patterns: Sequence[str] = field(default_factory=tuple)
    exclude_patterns: Sequence[str] = field(default_factory=tuple)
    stopwords: Sequence[str] = field(default_factory=tuple)

    def compile(self) -> "CompiledFilter":
        return CompiledFilter(self)


@dataclass(slots=True)
class CompiledFilter:
    options: FilterOptions

    def __post_init__(self) -> None:
        self._include = [re.compile(p, re.IGNORECASE) for p in self.options.include_patterns]
        self._exclude = [re.compile(p, re.IGNORECASE) for p in self.options.exclude_patterns]
        self._stop = {w.lower() for w in self.options.stopwords}

    def __call__(self, phrase: str) -> bool:
        opts = self.options
        if opts.min_length and len(phrase) < opts.min_length:
            return False
        if opts.max_length and len(phrase) > opts.max_length:
            return False
        if not opts.allow_digits and any(ch.isdigit() for ch in phrase):
            return False
        if not opts.allow_punctuation and _PUNCT_RE.search(phrase):
            return False
        if self._stop and phrase.lower() in self._stop:
            return False
        if self._include and not any(p.search(phrase) for p in self._include):
            return False
        if self._exclude and any(p.search(phrase) for p in self._exclude):
            return False
        return True


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def generate_combinations(
    dictionaries: Sequence[Sequence[str]],
    *,
    glue: str = " ",
    prefix: str = "",
    suffix: str = "",
    template: str | None = None,
    normalization: NormalizationOptions | None = None,
) -> list[str]:
    """Return the cartesian product of word lists as phrases.

    Parameters
    ----------
    dictionaries:
        A sequence of iterables (columns). Empty strings are ignored.
    glue:
        String inserted between dictionary parts when *template* is not provided.
    prefix/suffix:
        Optional strings added around every generated phrase.
    template:
        Custom format string using `{i}` placeholders. When provided, *glue* is ignored.
    normalization:
        Optional :class:`NormalizationOptions` applied to the final phrase.
    """

    if not dictionaries:
        return []
    sequences = [list(col) for col in dictionaries if col]
    if not sequences:
        return []

    normalizer = normalization.apply if normalization else (lambda s: s)
    phrases: list[str] = []
    for parts in product(*sequences):
        if template:
            phrase = template
            for idx, part in enumerate(parts):
                phrase = phrase.replace(f"{{{idx}}}", part)
        else:
            phrase = glue.join(parts)
        phrase = f"{prefix}{phrase}{suffix}" if prefix or suffix else phrase
        phrase = normalizer(phrase)
        if phrase:
            phrases.append(phrase)
    if normalization and normalization.deduplicate:
        phrases = list(dict.fromkeys(phrases))
    return phrases


def normalize_phrases(
    phrases: Iterable[str],
    options: NormalizationOptions | None = None,
) -> list[str]:
    opts = options or NormalizationOptions()
    seen: dict[str, None] = {}
    result: list[str] = []
    for raw in phrases:
        if raw is None:
            continue
        cleaned = opts.apply(str(raw))
        if not cleaned:
            continue
        if opts.deduplicate:
            if cleaned in seen:
                continue
            seen[cleaned] = None
        result.append(cleaned)
    return result


def filter_phrases(
    phrases: Iterable[str],
    options: FilterOptions | CompiledFilter | None = None,
) -> list[str]:
    if options is None:
        return [p for p in phrases]
    compiled = options if isinstance(options, CompiledFilter) else options.compile()
    return [phrase for phrase in phrases if compiled(phrase)]


def tokenize(phrase: str, *, keep_digits: bool = True) -> list[str]:
    """Split a phrase into tokens suitable for clustering.

    The tokenizer is intentionally simple and relies only on the standard library.
    """

    tokens = []
    for match in _TOKEN_RE.finditer(phrase.lower()):
        token = match.group(0)
        if not keep_digits and token.isdigit():
            continue
        tokens.append(token)
    return tokens


@dataclass(slots=True)
class Cluster:
    """Simple phrase cluster based on token overlap."""

    keys: list[str]
    tokens: list[set[str]]

    def add(self, phrase: str, token_set: set[str]) -> None:
        self.keys.append(phrase)
        self.tokens.append(token_set)

    def representative(self) -> str:
        return self.keys[0]

    def size(self) -> int:
        return len(self.keys)


def cluster_phrases(
    phrases: Iterable[str],
    *,
    similarity: float = 0.5,
    tokenizer: Callable[[str], Iterable[str]] | None = None,
) -> list[Cluster]:
    """Group phrases by Jaccard similarity of token sets.

    Parameters
    ----------
    phrases:
        Input phrases (already normalised / filtered if necessary).
    similarity:
        Minimum Jaccard index (0..1) to join the same cluster.
    tokenizer:
        Optional callable to obtain tokens. Defaults to :func:`tokenize`.
    """

    if similarity <= 0:
        similarity = 0.0
    if similarity > 1:
        similarity = 1.0
    get_tokens = tokenizer or tokenize

    clusters: list[Cluster] = []
    for phrase in phrases:
        tokens = set(get_tokens(phrase))
        if not tokens:
            clusters.append(Cluster([phrase], [set()]))
            continue
        placed = False
        for cluster in clusters:
            best = max(_jaccard(tokens, existing) for existing in cluster.tokens or [set()])
            if best >= similarity:
                cluster.add(phrase, tokens)
                placed = True
                break
        if not placed:
            clusters.append(Cluster([phrase], [tokens]))
    return clusters


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------------------
# Convenience iterator
# ---------------------------------------------------------------------------


def walk_clusters(clusters: Iterable[Cluster]) -> Iterator[tuple[int, str, list[str]]]:
    """Yield (size, representative, phrases) for convenience in reports."""

    for cluster in clusters:
        yield cluster.size(), cluster.representative(), list(cluster.keys)

