# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""agents/pss_gen.py — PSS model generation agent.

Phase: v1b
Layer: 3 (agents)

Generates a PSS v3.0 model from IR via a Jinja2 skeleton in no-LLM mode or via
LLM completion in production mode.
"""

from __future__ import annotations

import os

import anthropic
from jinja2 import Environment, FileSystemLoader

from ir import IR


TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "pss")
TEMPLATE_NAME = "component.pss.jinja"


def generate_pss(
    ir: IR,
    fail_reason: str | None = None,
    no_llm: bool = False,
) -> str:
    """Generate a PSS v3.0 model from the IR.

    Args:
        ir: Parsed design intermediate representation.
        fail_reason: Optional checker feedback from prior attempt.
        no_llm: If True, return template-rendered output without API usage.

    Returns:
        PSS model source text.

    Side Effects:
        Stores generated source in ``ir.pss_model``.
    """
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(TEMPLATE_NAME)
    context = _build_context(ir)
    skeleton = template.render(**context)

    if no_llm:
        ir.pss_model = skeleton
        return skeleton

    prompt = _build_prompt(ir, skeleton, fail_reason)
    model = _call_llm(prompt)
    ir.pss_model = model
    return model


def _build_context(ir: IR) -> dict:
    """Build template context groups from IR ports.

    Args:
        ir: Parsed design intermediate representation.

    Returns:
        Context dictionary for PSS Jinja2 rendering.
    """
    ports = ir.ports
    return {
        "design_name": ir.design_name,
        "ports": ports,
        "clock_ports": [p for p in ports if p.role == "clock"],
        "reset_ports": [p for p in ports if p.role in {"reset", "reset_n"}],
        "control_ports": [p for p in ports if p.role == "control" and p.direction == "input"],
        "data_ports": [p for p in ports if p.role == "data" and p.direction == "output"],
    }


def _build_prompt(ir: IR, skeleton: str, fail_reason: str | None) -> str:
    """Build the production LLM prompt for PSS completion.

    Args:
        ir: Parsed design intermediate representation.
        skeleton: Template-rendered PSS skeleton.
        fail_reason: Optional checker feedback from prior attempt.

    Returns:
        Prompt string for LLM completion.
    """
    lines = [
        "Generate a valid PSS v3.0 model.",
        f"Design name: {ir.design_name}",
        f"Ports: {[p.__dict__ for p in ir.ports]}",
        "Fill the constraints and coverage placeholders with meaningful content.",
        "Return only PSS DSL source code.",
        "",
        skeleton,
    ]
    if fail_reason:
        lines = [
            f"Previous attempt failed with: {fail_reason}",
            "Fix that issue while keeping valid PSS v3.0 syntax.",
            "",
        ] + lines
    return "\n".join(lines)


def _call_llm(prompt: str) -> str:
    """Call Anthropic to complete the PSS skeleton.

    Args:
        prompt: Prompt text with skeleton and IR context.

    Returns:
        Completed PSS model source.
    """
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
