# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""emitters/generic_c.py — Generic C test case emitter.

Phase: v2b
Layer: 5 (emitters)

Generates C test functions from the PSS model stored in ir.pss_model.
Extracts PSS action names via regex, renders a Jinja2 template, and writes
<design_name>_pss_tests.c alongside all other pipeline artifacts.
Activated by --sim generic.
"""
import os
import re

from jinja2 import Environment, FileSystemLoader

from agents.structure_gen import Artifact
from ir import IR


_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "c")
_TEMPLATE_NAME = "test_functions.c.jinja"
_ACTION_PATTERN = re.compile(r"action\s+(\w+)\s*\{")


def emit(ir: IR, artifacts: list[Artifact], out_dir: str) -> list[str]:
    """Emit C test cases derived from the PSS model.

    Extracts action names from ir.pss_model using regex, renders the C
    template, and writes <design_name>_pss_tests.c to out_dir.  Also writes
    all other artifacts to out_dir, consistent with other emitters.

    If ir.pss_model is None or contains no action declarations, writes a C
    file with only the header comment and an empty run_all_pss_tests() stub.

    Args:
        ir: Parsed design IR including optional pss_model source.
        artifacts: Generated artifacts from prior pipeline stages.
        out_dir: Destination directory path.

    Returns:
        List of paths that were written.
    """
    os.makedirs(out_dir, exist_ok=True)

    # Write all existing artifacts (consistent with vivado emitter).
    written: list[str] = []
    for artifact in artifacts:
        path = os.path.join(out_dir, artifact.filename)
        with open(path, "w") as fh:
            fh.write(artifact.content)
        written.append(path)

    # Extract PSS action names from ir.pss_model (empty list if absent).
    actions: list[str] = []
    if ir.pss_model:
        actions = _ACTION_PATTERN.findall(ir.pss_model)

    # Render C test template.
    env = Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        keep_trailing_newline=True,
    )
    template = env.get_template(_TEMPLATE_NAME)
    c_content = template.render(design_name=ir.design_name, actions=actions)

    # Write C output file.
    c_filename = f"{ir.design_name}_pss_tests.c"
    c_path = os.path.join(out_dir, c_filename)
    with open(c_path, "w") as fh:
        fh.write(c_content)
    written.append(c_path)

    return written
