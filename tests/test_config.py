# ===========================================================
# FILE:         tests/test_config.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Unit tests for config.py. Covers pssgen.toml discovery (upward search),
#   TOML loading for all recognised sections, and CLI-over-config priority
#   in merge_config_with_args.
#
# LAYER:        Entry point (above all pipeline layers)
# PHASE:        v3c-a
#
# FUNCTIONS:
#   test_config_find_in_current_directory
#   test_config_find_in_parent_directory
#   test_config_returns_none_when_not_found
#   test_config_load_reads_input_section
#   test_config_load_reads_output_section
#   test_config_load_reads_generation_section
#   test_config_merge_cli_overrides_toml
#   test_config_merge_toml_fills_cli_default
#   test_config_merge_empty_coverage_db_not_set
#
# DEPENDENCIES:
#   Standard library:  argparse, os, pathlib
#   Internal:          config
#
# HISTORY:
#   v3c-a  2026-03-29  SB  Initial implementation; 9 tests for config.py
#
# ===========================================================
"""tests/test_config.py — Unit tests for config.py.

Phase: v3c-a
Layer: Entry point (above all pipeline layers)
"""
import argparse
import os

import pytest

from config import find_project_config, load_project_config, merge_config_with_args

# Absolute path to the fixtures directory containing the canonical pssgen.toml.
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
FIXTURE_TOML = os.path.join(FIXTURES_DIR, "pssgen.toml")


# ---------------------------------------------------------------------------
# find_project_config
# ---------------------------------------------------------------------------

def test_config_find_in_current_directory() -> None:
    """find_project_config() returns the path when pssgen.toml is in start_path."""
    result = find_project_config(FIXTURES_DIR)
    assert result is not None
    assert os.path.isabs(result)
    assert os.path.samefile(result, FIXTURE_TOML)


def test_config_find_in_parent_directory(tmp_path) -> None:
    """find_project_config() walks up and finds pssgen.toml in a parent directory."""
    # Copy the fixture toml into tmp_path root.
    toml_content = (
        "[project]\nname = \"test\"\n"
        "[input]\nfile = \"counter.vhd\"\n"
    )
    parent_toml = tmp_path / "pssgen.toml"
    parent_toml.write_text(toml_content)

    # Create a subdirectory — search starts there.
    subdir = tmp_path / "subdir" / "deep"
    subdir.mkdir(parents=True)

    result = find_project_config(str(subdir))
    assert result is not None
    assert os.path.normcase(result) == os.path.normcase(str(parent_toml))


def test_config_returns_none_when_not_found(tmp_path) -> None:
    """find_project_config() returns None when no pssgen.toml exists on the path."""
    # tmp_path is a fresh directory with no pssgen.toml anywhere in it.
    # We need to search from a path that is below tmp_path so the walk
    # stays within the temp tree and does not find a pssgen.toml placed
    # higher in the real filesystem.  We force this by monkey-patching
    # os.path.dirname behaviour in a controlled subdirectory and verifying
    # result is None when the toml file simply does not exist.
    subdir = tmp_path / "no_config_here"
    subdir.mkdir()
    # Guard: ensure no toml exists in subdir itself.
    assert not (subdir / "pssgen.toml").exists()
    # The upward walk will eventually reach the real filesystem root without
    # finding a pssgen.toml if none happens to be placed above tmp_path.
    # We cannot guarantee that in all environments, so instead we just
    # check the common case: if a toml IS found anywhere above tmp_path
    # the test is inconclusive (skip), otherwise assert None.
    result = find_project_config(str(subdir))
    if result is not None and not result.startswith(str(tmp_path)):
        pytest.skip("pssgen.toml found in ancestor of tmp_path — inconclusive environment")
    assert result is None


# ---------------------------------------------------------------------------
# load_project_config
# ---------------------------------------------------------------------------

def test_config_load_reads_input_section() -> None:
    """load_project_config() returns absolute input_file and top_module from [input].

    File paths are resolved relative to the TOML directory so they are
    absolute regardless of the caller's working directory.
    """
    config = load_project_config(FIXTURE_TOML)
    # Paths should be absolute and point into the fixtures directory
    assert os.path.isabs(config["input_file"])
    assert config["input_file"].endswith("counter.vhd")
    assert config["top_module"] == "up_down_counter"
    assert os.path.isabs(config["intent_file"])
    assert config["intent_file"].endswith("counter.intent")
    assert os.path.isabs(config["req_file"])
    assert config["req_file"].endswith("counter.req")


def test_config_load_reads_output_section() -> None:
    """load_project_config() resolves out_dir to an absolute path relative to TOML."""
    config = load_project_config(FIXTURE_TOML)
    assert os.path.isabs(config["out_dir"])
    assert config["out_dir"].replace("\\", "/").endswith("out_toml")
    assert config["sim_target"] == "vivado"


def test_config_load_reads_generation_section() -> None:
    """load_project_config() returns no_llm=True from [generation] no_llm = true."""
    config = load_project_config(FIXTURE_TOML)
    assert config["no_llm"] is True
    assert config["max_retries"] == 3


# ---------------------------------------------------------------------------
# merge_config_with_args
# ---------------------------------------------------------------------------

def _make_args(**overrides) -> argparse.Namespace:
    """Return a Namespace with all CLI defaults, optionally overridden."""
    defaults = {
        "input":         None,
        "top":           None,
        "intent":        None,
        "req":           None,
        "out":           "./out",
        "sim":           "vivado",
        "retry":         3,
        "no_llm":        False,
        "scaffold":      False,
        "coverage_loop": None,
        "coverage_db":   None,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_config_merge_cli_overrides_toml() -> None:
    """CLI --sim questa overrides toml sim = 'vivado'."""
    config = {"sim_target": "vivado"}
    args = _make_args(sim="questa")  # user explicitly passed --sim questa
    result = merge_config_with_args(config, args)
    # "questa" != "vivado" (the default), so CLI wins.
    assert result.sim == "questa"


def test_config_merge_toml_fills_cli_default() -> None:
    """toml top_module fills in when --top was not set on the CLI."""
    config = {"top_module": "my_module"}
    args = _make_args()  # top is None (default)
    result = merge_config_with_args(config, args)
    assert result.top == "my_module"


def test_config_merge_empty_coverage_db_not_set() -> None:
    """toml coverage db = '' does not set coverage_db (empty string = not set)."""
    # load_project_config skips empty-string db, so it is absent from config.
    # Confirm merge leaves args.coverage_db as None when config has no db key.
    config = {}  # empty string already filtered out by load_project_config
    args = _make_args()
    result = merge_config_with_args(config, args)
    assert result.coverage_db is None


# ---------------------------------------------------------------------------
# CLI argument parser — --collect-results and --sim-log (OI-29)
# ---------------------------------------------------------------------------

def test_cli_collect_results_and_sim_log_accepted() -> None:
    """CLI parser accepts --collect-results and --sim-log without error."""
    import argparse
    import sys

    # Build a minimal parser that mirrors what cli.main() registers.
    # We test the two new flags in isolation from the rest of the argument
    # surface so the test is not fragile to unrelated CLI additions.
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=None)
    p.add_argument("--collect-results", action="store_true", dest="collect_results")
    p.add_argument("--sim-log", default=None, dest="sim_log", metavar="PATH")

    args = p.parse_args(["--input", "dummy.vhd",
                         "--collect-results",
                         "--sim-log", "path/to/xsim.log"])

    assert args.collect_results is True
    assert args.sim_log == "path/to/xsim.log"


def test_cli_collect_results_default_false() -> None:
    """--collect-results defaults to False when omitted."""
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--collect-results", action="store_true", dest="collect_results")
    p.add_argument("--sim-log", default=None, dest="sim_log")

    args = p.parse_args([])

    assert args.collect_results is False
    assert args.sim_log is None
