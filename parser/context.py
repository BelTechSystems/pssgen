# Copyright (c) 2026 BelTech Systems LLC and contributors
# SPDX-License-Identifier: MIT
"""parser/context.py — Context file path resolver for intent and req files.

Phase: v3a
Layer: 1 (parser support)

Resolves .intent and .req file paths by convention (same stem as the HDL
input file) or explicit CLI flag. Explicit flags always take precedence
over convention. The should_extract flag indicates whether a .req file
should be auto-generated from intent req IDs.
"""
import os


def resolve_context_files(
    input_file: str,
    intent_flag: str | None = None,
    req_flag: str | None = None,
    no_intent: bool = False,
    no_req: bool = False,
) -> tuple[str | None, str | None, bool]:
    """Resolve intent and req file paths by convention or explicit flag.

    Convention: look for <stem>.intent and <stem>.req alongside the input
    file. Explicit flags override convention. ``should_extract`` is True
    only when no .req file was found (meaning extraction from intent IDs
    may be appropriate if the caller finds req IDs in the intent).

    Args:
        input_file: Path to the HDL input file (e.g. counter.vhd).
        intent_flag: Explicit path to .intent file from CLI, or None.
        req_flag: Explicit path to .req file from CLI, or None.
        no_intent: If True, suppress auto-detection of <stem>.intent.
        no_req: If True, suppress auto-detection of <stem>.req.

    Returns:
        Tuple of (intent_path, req_path, should_extract) where:
        - intent_path is the resolved intent file path or None.
        - req_path is the resolved req file path or None.
        - should_extract is True when req_path is None (caller should
          decide whether to extract based on intent req ID presence).
    """
    base_dir = os.path.dirname(os.path.abspath(input_file))
    stem = os.path.splitext(os.path.basename(input_file))[0]

    # Resolve intent path
    intent_path: str | None = None
    if intent_flag is not None:
        # Explicit flag always wins regardless of no_intent
        if os.path.isfile(intent_flag):
            intent_path = intent_flag
    elif not no_intent:
        candidate = os.path.join(base_dir, f"{stem}.intent")
        if os.path.isfile(candidate):
            intent_path = candidate

    # Resolve req path
    req_path: str | None = None
    if req_flag is not None:
        # Explicit flag always wins regardless of no_req
        if os.path.isfile(req_flag):
            req_path = req_flag
    elif not no_req:
        candidate = os.path.join(base_dir, f"{stem}.req")
        if os.path.isfile(candidate):
            req_path = candidate

    # should_extract: True when no req file exists
    # (orchestrator checks intent for req IDs before actually extracting)
    should_extract = req_path is None

    return intent_path, req_path, should_extract
