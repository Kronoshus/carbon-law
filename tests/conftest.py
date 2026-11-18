import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
"""Tests never reach the network: any urllib request to a non-local host fails the test.
(backend/app.py's demo drafting loads ~/.config/carbon-law/beam.env and would otherwise call the real Beam API.)"""
import urllib.parse
import urllib.request

import pytest

_real_urlopen = urllib.request.urlopen


def _local_only(url, *args, **kwargs):
    target = url.full_url if isinstance(url, urllib.request.Request) else url
    host = urllib.parse.urlsplit(target).hostname
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise RuntimeError(f"tests must not call the network: {host}")
    return _real_urlopen(url, *args, **kwargs)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _local_only)
