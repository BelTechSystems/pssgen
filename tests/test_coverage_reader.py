# ===========================================================
# FILE:         tests/test_coverage_reader.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Unit tests for agents/coverage_reader.py. Verifies that the Vivado
#   XML reader correctly identifies hit/missed covergroups, handles missing
#   files, and degrades gracefully on malformed XML — all without raising.
#
# LAYER:        Tests
# PHASE:        v3c-b
#
# HISTORY:
#   v3c-b  2026-03-29  SB  Initial implementation; 4 coverage reader tests
#
# ===========================================================
"""Unit tests for the Vivado XML coverage reader."""

from __future__ import annotations

import os

import pytest

from agents.coverage_reader import read_coverage_xml, CoverageResult

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
COVERAGE_XML = os.path.join(FIXTURES_DIR, "counter_coverage.xml")


def test_coverage_reader_reads_hit_covergroup() -> None:
    """cg_reset_behavior_01 at 100% → True in covergroups dict."""
    result = read_coverage_xml(COVERAGE_XML)

    assert "cg_reset_behavior_01" in result.covergroups
    assert result.covergroups["cg_reset_behavior_01"] is True


def test_coverage_reader_reads_missed_covergroup() -> None:
    """cg_counting_sequences_01 at 0% → False in covergroups dict."""
    result = read_coverage_xml(COVERAGE_XML)

    assert "cg_counting_sequences_01" in result.covergroups
    assert result.covergroups["cg_counting_sequences_01"] is False


def test_coverage_reader_missing_file_returns_empty(tmp_path) -> None:
    """Non-existent path returns empty covergroups with a parse_warning."""
    non_existent = str(tmp_path / "does_not_exist.xml")

    result = read_coverage_xml(non_existent)

    assert result.covergroups == {}
    assert len(result.parse_warnings) >= 1
    assert any("not found" in w.lower() for w in result.parse_warnings)


def test_coverage_reader_malformed_xml_returns_empty(tmp_path) -> None:
    """Invalid XML content returns empty covergroups with a parse_warning."""
    bad_xml = tmp_path / "bad.xml"
    bad_xml.write_text("<this is not valid xml <> &&", encoding="utf-8")

    result = read_coverage_xml(str(bad_xml))

    assert result.covergroups == {}
    assert len(result.parse_warnings) >= 1
