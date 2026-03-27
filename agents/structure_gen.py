# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""agents/structure_gen.py — UVM artifact generation agent.

Phase: v0
Layer: 3 (agents)

Renders Jinja2 UVM templates and, in production mode, asks the LLM to complete
dynamic content. In test/CI mode (`no_llm=True`), returns rendered templates
directly with no API calls.
"""
from dataclasses import dataclass
from typing import Optional
from jinja2 import Environment, FileSystemLoader
from ir import IR
import os, anthropic


@dataclass
class Artifact:
    """Generated file artifact.

    Attributes:
        filename: Output filename for the generated artifact.
        content: Full generated file content.
    """
    filename: str
    content: str


TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "uvm")
TEMPLATES = [
    "interface.sv.jinja",
    "driver.sv.jinja",
    "monitor.sv.jinja",
    "sequencer.sv.jinja",
    "agent.sv.jinja",
    "test.sv.jinja",
    "build_vivado.tcl.jinja",
]


def generate(ir: IR, fail_reason: Optional[str] = None, no_llm: bool = False) -> list[Artifact]:
    """Generate UVM artifacts from templates.

    Args:
        ir: Parsed intermediate representation used for template rendering.
        fail_reason: Optional checker feedback from a previous attempt.
        no_llm: When True, returns rendered templates directly and never calls
            the LLM.

    Returns:
        List of generated artifacts.
    """
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    artifacts = []

    for tmpl_name in TEMPLATES:
        template = env.get_template(tmpl_name)
        partial = template.render(ir=ir)

        if no_llm:
            filled = partial
        else:
            # Build LLM prompt
            prompt = _build_prompt(ir, tmpl_name, partial, fail_reason)
            filled = _call_llm(prompt)

        out_name = _output_filename(ir.design_name, tmpl_name)
        artifacts.append(Artifact(filename=out_name, content=filled))

    return artifacts


def _output_filename(design_name: str, tmpl_name: str) -> str:
    """Map a template filename to its emitted artifact filename.

    Args:
        design_name: Parsed design name used as filename prefix.
        tmpl_name: Template filename under templates/uvm.

    Returns:
        Output artifact filename.
    """
    name = tmpl_name.replace(".jinja", "").replace("interface", f"{design_name}_if")
    for role in ["driver", "monitor", "sequencer", "agent", "test"]:
        name = name.replace(role, f"{design_name}_{role}")
    name = name.replace("build_vivado", "build")
    return name


def _build_prompt(ir: IR, tmpl_name: str, partial: str, fail_reason: Optional[str]) -> str:
    """Build the prompt used for production LLM completion.

    Args:
        ir: Parsed intermediate representation.
        tmpl_name: Source template filename.
        partial: Rendered template text prior to LLM completion.
        fail_reason: Optional checker failure reason from a previous attempt.

    Returns:
        Prompt string sent to the LLM.
    """
    lines = [
        f"You are generating a UVM 1.2 SystemVerilog file for a design named '{ir.design_name}'.",
        f"Design ports: {[p.__dict__ for p in ir.ports]}",
        "",
        "Complete the following template. Fill ALL placeholder markers. "
        "Output ONLY the completed file content — no explanation, no markdown fences.",
        "",
        partial,
    ]
    if fail_reason:
        lines = [
            f"Previous attempt failed with: {fail_reason}",
            "Fix that specific issue in your output.",
            "",
        ] + lines
    return "\n".join(lines)


def _call_llm(prompt: str) -> str:
    """Call Anthropic API and return generated file text.

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
