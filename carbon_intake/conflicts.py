"""Conflict-of-interest name matching for carbon_intake."""
import csv, difflib, re, unicodedata


def fold(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def conflict_hits(text, names=None):
    """Names from the firm's conflict list that appear in what the client said.

    `names` is a list of names (one per row of conflicts.csv). Returns the matching
    names, or None when no list was provided (so the caller can distinguish
    "no list" from "no matches").
    """
    if names is None:
        return None
    said = re.findall(r"[a-z]+", fold(text))
    close = lambda w, x: difflib.SequenceMatcher(None, w, x).ratio() >= 0.8
    hits = []
    for name in names:
        name = (name or "").strip()
        words = re.findall(r"[a-z]+", fold(name))
        n = len(words) + 1
        if len(words) >= 2 and name.lower() != "name" and any(
                all(any(close(w, x) for x in said[i:i + n]) for w in words)
                for i in range(max(1, len(said) - n + 1))):
            hits.append(name)
    return hits
