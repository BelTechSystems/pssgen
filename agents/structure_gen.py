# ===========================================================
# FILE:         agents/structure_gen.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   UVM artifact generation agent. Delegates to scaffold_gen.generate_uvm_tb()
#   for Python-string-based UVM file generation per D-032. Returns list of
#   Artifact objects for downstream checker and emitter consumption. The
#   Jinja2 template-based generation path has been retired.
#
# LAYER:        3 — agents
# PHASE:        v0 / D-032
#
# FUNCTIONS:
#   generate(ir, fail_reason, no_llm)
#     Generate UVM artifacts by delegating to scaffold_gen.generate_uvm_tb().
#
# DEPENDENCIES:
#   Standard library:  dataclasses, typing
#   External:          anthropic
#   Internal:          ir, agents.scaffold_gen
#
# HISTORY:
#   v0     2026-03-27  SB  Initial implementation; Jinja2 + LLM UVM generation
#   D-032  2026-04-14  SB  Replace Jinja2 rendering with scaffold_gen.generate_uvm_tb()
#                          delegation; retire jinja2 dependency from this module
#
# ===========================================================
"""agents/structure_gen.py — UVM artifact generation agent.

Phase: v0 / D-032
Layer: 3 (agents)

Delegates UVM file generation to scaffold_gen.generate_uvm_tb() and returns
Artifact objects for checker and emitter consumption. The fail_reason and
no_llm parameters are retained for interface stability; fail_reason is
currently unused at this delegation layer.
"""
from dataclasses import dataclass
from typing import Optional
from ir import IR
from agents.scaffold_gen import _gen_all_content
import anthropic


@dataclass
class Artifact:
    """Generated file artifact.

    Attributes:
        filename: Output filename for the generated artifact.
        content: Full generated file content.
    """
    filename: str
    content: str


def generate(ir: IR, fail_reason: Optional[str] = None, no_llm: bool = False) -> list[Artifact]:
    """Generate UVM artifacts from Python string generation.

    Delegates to scaffold_gen._gen_all_content() to produce all STD-003B
    UVM file content. Returns Artifact objects with flat filenames for
    compatibility with the checker and emitter layers.

    The fail_reason parameter is accepted for interface stability but is
    not currently propagated to the Python string generation path.
    The no_llm parameter is accepted for interface stability; this
    implementation never calls the LLM.

    Args:
        ir: Parsed intermediate representation used for generation.
        fail_reason: Optional checker feedback from a previous attempt.
            Reserved for future LLM integration.
        no_llm: When True, returns generated content directly and never
            calls the LLM. Currently all generation is template-free Python.

    Returns:
        List of generated artifacts with flat filenames.
    """
    all_content = _gen_all_content(ir, None)
    return [Artifact(filename=fname, content=content)
            for fname, content in all_content.items()]


def _call_llm(prompt: str) -> str:
    """Call Anthropic API and return generated file text.

    Retained for potential future LLM-augmented generation.

    Args:
        prompt: Prompt text requesting completed artifact content.

    Returns:
        Generated artifact content as plain text.
    """
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
