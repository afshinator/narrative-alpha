"""Tests for narrative/backtest.py — historical back-test worker (Task 7 stub)."""

import pytest

from narrative.backtest import execute_historical_backtest


class TestExecuteHistoricalBacktest:
    def test_importable_and_callable(self):
        assert callable(execute_historical_backtest)

    def test_accepts_domain_and_vertical(self):
        result = execute_historical_backtest("example.com", "TECHNOLOGY")
        assert result is None

    def test_accepts_empty_strings(self):
        result = execute_historical_backtest("", "")
        assert result is None

    def test_has_docstring(self):
        doc = execute_historical_backtest.__doc__
        assert doc is not None
        assert "historical" in doc
        assert "consensus-supported" in doc
        assert "consensus-isolated" in doc
