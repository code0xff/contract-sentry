"""Unit tests for the bytecode cache key function."""
from __future__ import annotations

from app.core.cache import make_cache_key


def test_make_cache_key_consistent():
    key1 = make_cache_key("0xdeadbeef", ["slither", "mythril"])
    key2 = make_cache_key("0xdeadbeef", ["slither", "mythril"])
    assert key1 == key2


def test_make_cache_key_tool_order_independent():
    key1 = make_cache_key("0xdeadbeef", ["slither", "mythril"])
    key2 = make_cache_key("0xdeadbeef", ["mythril", "slither"])
    assert key1 == key2


def test_make_cache_key_differs_by_tools():
    key1 = make_cache_key("0xdeadbeef", ["slither"])
    key2 = make_cache_key("0xdeadbeef", ["mythril"])
    assert key1 != key2
