# Copyright (c) 2026 BelTech Systems LLC and contributors
# SPDX-License-Identifier: MIT
"""tests/test_context.py — Unit tests for parser/context.py.

Phase: v3a
Layer: 1 (parser support)

Tests auto-detection of .intent and .req files by convention, explicit
flag override, --no-intent suppression, and never-overwrite guard.
"""
import os
import tempfile
import pytest
from parser.context import resolve_context_files


def _setup_fixture_dir(files: list[str]) -> tuple[str, str]:
    """Create a temp directory with empty files and an input HDL file.

    Args:
        files: Filenames to create in the temp dir.

    Returns:
        Tuple of (temp_dir_path, input_file_path) where input_file_path
        points to a file named counter.vhd in the temp dir.
    """
    tmp_dir = tempfile.mkdtemp()
    input_file = os.path.join(tmp_dir, "counter.vhd")
    # Create the input file and all side-car files
    for fname in files:
        open(os.path.join(tmp_dir, fname), "w").close()
    return tmp_dir, input_file


def test_context_auto_detects_intent() -> None:
    """<stem>.intent alongside input is auto-detected when no flag is given."""
    tmp_dir, input_file = _setup_fixture_dir(["counter.vhd", "counter.intent"])
    try:
        intent_path, req_path, should_extract = resolve_context_files(input_file)
        assert intent_path is not None
        assert intent_path.endswith("counter.intent")
    finally:
        import shutil
        shutil.rmtree(tmp_dir)


def test_context_auto_detects_req() -> None:
    """<stem>.req alongside input is auto-detected when no flag is given."""
    tmp_dir, input_file = _setup_fixture_dir(
        ["counter.vhd", "counter.intent", "counter.req"]
    )
    try:
        intent_path, req_path, should_extract = resolve_context_files(input_file)
        assert req_path is not None
        assert req_path.endswith("counter.req")
        # should_extract is False when .req exists
        assert should_extract is False
    finally:
        import shutil
        shutil.rmtree(tmp_dir)


def test_context_explicit_flag_overrides_convention() -> None:
    """An explicit --intent flag takes precedence over convention auto-detection."""
    tmp_dir, input_file = _setup_fixture_dir(
        ["counter.vhd", "counter.intent", "explicit.intent"]
    )
    explicit_intent = os.path.join(tmp_dir, "explicit.intent")
    try:
        intent_path, req_path, should_extract = resolve_context_files(
            input_file, intent_flag=explicit_intent
        )
        assert intent_path == explicit_intent
    finally:
        import shutil
        shutil.rmtree(tmp_dir)


def test_context_no_intent_suppresses_detection() -> None:
    """--no-intent prevents auto-loading of <stem>.intent."""
    tmp_dir, input_file = _setup_fixture_dir(["counter.vhd", "counter.intent"])
    try:
        intent_path, req_path, should_extract = resolve_context_files(
            input_file, no_intent=True
        )
        assert intent_path is None
    finally:
        import shutil
        shutil.rmtree(tmp_dir)


def test_context_no_overwrite_when_req_exists() -> None:
    """should_extract is False when a .req file already exists alongside input."""
    tmp_dir, input_file = _setup_fixture_dir(
        ["counter.vhd", "counter.req"]
    )
    try:
        intent_path, req_path, should_extract = resolve_context_files(input_file)
        assert req_path is not None
        assert should_extract is False
    finally:
        import shutil
        shutil.rmtree(tmp_dir)
