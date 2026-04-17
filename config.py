# ===========================================================
# FILE:         config.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Project configuration loader for pssgen.toml files. Searches for a
#   config file by walking up the directory tree, loads and validates its
#   recognised sections, and merges config values with parsed CLI arguments
#   giving CLI flags strict precedence over config file values.
#
# LAYER:        Entry point (above all pipeline layers)
# PHASE:        v3c-a
#
# FUNCTIONS:
#   find_project_config(start_path)
#     Walk directory tree upward from start_path to locate pssgen.toml.
#   load_project_config(config_path)
#     Parse pssgen.toml and return a flat dict of recognised config values.
#   merge_config_with_args(config, args)
#     Merge config values into parsed CLI args; CLI flags always take priority.
#
# DEPENDENCIES:
#   Standard library:  argparse, os, tomllib
#   Internal:          (none)
#
# HISTORY:
#   v3c-a  2026-03-29  SB  Initial implementation; TOML project config support
#   v3c-b  2026-03-29  SB  Resolve TOML file paths relative to TOML directory
#   v4c    2026-04-05  SB  [[register_maps]] array-of-tables multi-file support
#   v5b    2026-04-10  SB  Resolve [output] dir relative to TOML directory
#   v6c    2026-04-16  SB  Read [input] vplan key; wire to vplan_file arg
#   v6d    2026-04-16  SB  [output] dir sets out_dir=toml_dir (IP root) to prevent tb/tb/ nesting
#
# ===========================================================
"""config.py — pssgen.toml project configuration loader.

Phase: v3c-a
Layer: Entry point (above all pipeline layers)

Locates, loads, and merges pssgen.toml project configuration with CLI
arguments. CLI flags always take priority over config file values.
"""
import argparse
import os
import tomllib
from typing import Optional


# Argparse attribute names → their "not explicitly set" default values.
# Used by merge_config_with_args to decide whether to fill from config.
_CLI_DEFAULTS: dict = {
    "input":         None,
    "top":           None,
    "intent":        None,
    "req":           None,
    "vplan":         None,
    "out":           "./out",
    "sim":           "vivado",
    "retry":         3,
    "no_llm":        False,
    "scaffold":      False,
    "coverage_loop": None,
    "coverage_db":   None,
}

# Maps config-dict keys (from load_project_config) to argparse attribute names.
_CONFIG_TO_ARGS: list[tuple[str, str]] = [
    ("input_file",    "input"),
    ("top_module",    "top"),
    ("intent_file",   "intent"),
    ("req_file",      "req"),
    ("vplan_file",    "vplan"),
    ("out_dir",       "out"),
    ("sim_target",    "sim"),
    ("max_retries",   "retry"),
    ("no_llm",        "no_llm"),
    ("scaffold",      "scaffold"),
    ("coverage_loop", "coverage_loop"),
    ("coverage_db",   "coverage_db"),
]


def find_project_config(start_path: Optional[str] = None) -> Optional[str]:
    """Search for pssgen.toml from start_path upward to the filesystem root.

    Searches in order:
      1. start_path (defaults to current working directory)
      2. Each successive parent directory up to the filesystem root

    Args:
        start_path: Directory to begin search. Defaults to ``os.getcwd()``.

    Returns:
        Absolute path to pssgen.toml if found, else None.
    """
    if start_path is None:
        start_path = os.getcwd()

    current = os.path.abspath(start_path)
    while True:
        candidate = os.path.join(current, "pssgen.toml")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            # Reached the filesystem root without finding the file.
            return None
        current = parent


def load_project_config(config_path: str) -> dict:
    """Load and validate a pssgen.toml file.

    Uses tomllib (Python 3.11+ stdlib). Returns a flat dict with all
    recognised keys mapped to their CLI argument equivalents. Unknown
    keys are silently ignored. Missing keys are absent from the result
    (not set to None) so callers can distinguish "not in config" from
    "explicitly set to a falsy value".

    The recognised sections and their CLI mappings are::

        [input]
        file    → input_file   (--input)
        top     → top_module   (--top)
        intent  → intent_file  (--intent)
        req     → req_file     (--req)
        vplan   → vplan_file   (--vplan)

        [output]
        dir     → out_dir = toml_dir  (IP root; generate_uvm_tb appends /tb/)
        sim     → sim_target   (--sim)

        [generation]
        retries → max_retries  (--retry)
        no_llm  → no_llm       (--no-llm)
        scaffold→ scaffold     (--scaffold)

        [coverage]
        loop    → coverage_loop (--coverage-loop)
        db      → coverage_db   (--coverage-db, empty string = absent)

    File paths (input_file, intent_file, req_file, coverage_db) are resolved
    relative to the directory that contains ``config_path``, so the TOML
    file is self-contained and pssgen can be invoked from any working directory.
    Non-path values (top, sim, retries, etc.) are returned as-is.

    Args:
        config_path: Absolute path to a pssgen.toml file.

    Returns:
        Flat dict of recognised config values keyed by CLI argument name.
        File-path values are absolute.
    """
    with open(config_path, "rb") as fh:
        raw = tomllib.load(fh)

    # File paths in the TOML are relative to the TOML file's directory so that
    # pssgen can be invoked from any working directory while keeping the config
    # self-contained in the project folder.
    toml_dir = os.path.dirname(os.path.abspath(config_path))

    def _resolve(path: str) -> str:
        """Resolve a path from the TOML file to an absolute path."""
        if os.path.isabs(path):
            return path
        return os.path.abspath(os.path.join(toml_dir, path))

    config: dict = {}

    input_sec = raw.get("input", {})
    if "file" in input_sec:
        config["input_file"] = _resolve(input_sec["file"])
    if "top" in input_sec:
        config["top_module"] = input_sec["top"]
    if "intent" in input_sec:
        config["intent_file"] = _resolve(input_sec["intent"])
    if "req" in input_sec:
        config["req_file"] = _resolve(input_sec["req"])
    if "vplan" in input_sec:
        config["vplan_file"] = _resolve(input_sec["vplan"])

    output_sec = raw.get("output", {})
    if "dir" in output_sec:
        # D-032: generate_uvm_tb() always creates out_dir/tb/.
        # The [output] dir value names the TB subdirectory the engineer wants,
        # but the out_dir exposed to the rest of pssgen must be the IP root
        # (the directory containing pssgen.toml) so that generate_uvm_tb()'s
        # out_dir/tb/ suffix lands in the right place.  Using _resolve() here
        # would give toml_dir/dir_value as out_dir, causing a double tb/tb/
        # nesting when dir = "tb".
        config["out_dir"] = toml_dir
    if "sim" in output_sec:
        config["sim_target"] = output_sec["sim"]

    gen_sec = raw.get("generation", {})
    if "retries" in gen_sec:
        config["max_retries"] = gen_sec["retries"]
    if "no_llm" in gen_sec:
        config["no_llm"] = gen_sec["no_llm"]
    if "scaffold" in gen_sec:
        config["scaffold"] = gen_sec["scaffold"]

    cov_sec = raw.get("coverage", {})
    if "loop" in cov_sec:
        loop_val = cov_sec["loop"]
        # 0 means "not enabled" — treat as absent, matching empty-string db behaviour.
        if loop_val:
            config["coverage_loop"] = loop_val
    if "db" in cov_sec:
        db_val = cov_sec["db"]
        # Empty string is treated as "not set" — do not include in config.
        if db_val:
            config["coverage_db"] = db_val

    # [[register_maps]] array-of-tables — multi-file register map support.
    # Each entry: {file = "path", base_address = "0x..."}
    # Single [register_map] (non-list) maps to reg_map_file for back-compat.
    reg_maps_raw = raw.get("register_maps")
    if reg_maps_raw is not None:
        if isinstance(reg_maps_raw, list):
            # [[register_maps]] table-array
            entries = []
            for entry in reg_maps_raw:
                if isinstance(entry, dict) and "file" in entry:
                    resolved_file = _resolve(entry["file"])
                    entries.append({
                        "file": resolved_file,
                        "base_address": entry.get("base_address"),
                    })
            if entries:
                config["register_maps_list"] = entries
        elif isinstance(reg_maps_raw, dict) and "file" in reg_maps_raw:
            # Single [register_maps] section (legacy / single file)
            config["reg_map_file"] = _resolve(reg_maps_raw["file"])
            if "base_address" in reg_maps_raw:
                config["reg_map_base"] = reg_maps_raw["base_address"]

    return config


def merge_config_with_args(
    config: dict,
    args: argparse.Namespace,
) -> argparse.Namespace:
    """Merge config file values into parsed CLI args.

    CLI flags take strict priority over config file values. A config value
    is used only when the corresponding CLI argument is still at its default
    (i.e., the user did not explicitly set it on the command line).

    Default values that indicate "not explicitly set by user":
      input, top, intent, req, coverage_loop, coverage_db → None
      out → "./out"
      sim → "vivado"
      retry → 3
      no_llm, scaffold → False

    Args:
        config: Loaded config dict from :func:`load_project_config`.
        args: Parsed :class:`argparse.Namespace` from the CLI parser.

    Returns:
        Updated Namespace with config values filled in where CLI args are
        at their defaults. The original Namespace is modified in place and
        also returned.
    """
    for config_key, args_attr in _CONFIG_TO_ARGS:
        if config_key not in config:
            continue
        default_val = _CLI_DEFAULTS.get(args_attr)
        current_val = getattr(args, args_attr, default_val)
        if current_val == default_val:
            setattr(args, args_attr, config[config_key])

    return args
