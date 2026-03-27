# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""parser/dispatch.py — HDL parser selection helpers.

Phase: v1a
Layer: 1 (parser)

Provides shared extension-based parser dispatch for CLI validation and
orchestrator runtime parsing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from ir import IR
from parser.systemverilog import parse as parse_systemverilog
from parser.verilog import parse as parse_verilog
from parser.vhdl import parse as parse_vhdl


ParserFn = Callable[[str, str | None], IR]


def resolve_parser(source_file: str) -> ParserFn:
    """Resolve the parser function for a source-file extension.

    Args:
        source_file: Input HDL source path.

    Returns:
        Parser callable matching the file extension.

    Raises:
        ValueError: If the extension is unsupported.
    """
    ext = Path(source_file).suffix.lower()
    if ext == ".v":
        return parse_verilog
    if ext == ".sv":
        return parse_systemverilog
    if ext in {".vhd", ".vhdl"}:
        return parse_vhdl
    raise ValueError(
        f"Unsupported input extension '{ext}'. Supported extensions: .v, .sv, .vhd, .vhdl"
    )


def parse_source(source_file: str, top_module: str | None) -> IR:
    """Parse an HDL source file using extension-based dispatch.

    Args:
        source_file: Input HDL source path.
        top_module: Optional top-level module/entity override.

    Returns:
        Parsed IR instance.
    """
    parser = resolve_parser(source_file)
    return parser(source_file, top_module)
