"""Tests never reach the network: any urllib or httpx request to a non-local host fails the test.
(backend/app.py's demo drafting loads ~/.config/carbon-law/beam.env and would otherwise call the real Beam API.)"""
import os
import sys
import urllib.parse
import urllib.request

import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # carbon_intake

_LOCAL = ("127.0.0.1", "localhost", "::1", "testserver")   # testserver: FastAPI TestClient, in-process
_real_urlopen = urllib.request.urlopen
_real_async_send = httpx.AsyncClient.send
_real_send = httpx.Client.send


def _check(host):
    if host not in _LOCAL:
        raise RuntimeError(f"tests must not call the network: {host}")


def _local_only(url, *args, **kwargs):
    target = url.full_url if isinstance(url, urllib.request.Request) else url
    _check(urllib.parse.urlsplit(target).hostname)
    return _real_urlopen(url, *args, **kwargs)


async def _local_async_send(self, request, *args, **kwargs):
    _check(request.url.host)
    return await _real_async_send(self, request, *args, **kwargs)


def _local_send(self, request, *args, **kwargs):
    _check(request.url.host)
    return _real_send(self, request, *args, **kwargs)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _local_only)
    monkeypatch.setattr(httpx.AsyncClient, "send", _local_async_send)
    monkeypatch.setattr(httpx.Client, "send", _local_send)
