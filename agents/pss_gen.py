# ===========================================================
# FILE:         agents/pss_gen.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   PSS v3.0 model generation agent. Renders a Jinja2 skeleton from IR and,
#   in production mode, completes it via LLM. When pss_intent is present,
#   the intent text is included in the prompt to produce design-specific
#   constraints and coverage goals. Result stored in ir.pss_model.
#   In v3b, _build_coverage_labels produces a three-tier hierarchy of named
#   covergroup labels from requirement IDs, intent sections, and IR inference.
#
# LAYER:        3 — agents
# PHASE:        v1b
#
# FUNCTIONS:
#   generate_pss(ir, fail_reason, no_llm, intent_result)
#     Generate a PSS v3.0 model from IR; store result in ir.pss_model.
#   _build_coverage_labels(ir, intent_result)
#     Build three-tier coverage label list from req IDs, intent sections, IR ports.
#
# DEPENDENCIES:
#   Standard library:  os, re
#   External:          anthropic, jinja2
#   Internal:          ir
#
# HISTORY:
#   v1b   2026-03-27  SB  Initial implementation; PSS skeleton generation
#   v2a   2026-03-27  SB  Added pss_intent propagation to LLM prompt
#   v3b   2026-03-28  SB  Added _build_coverage_labels, coverage_labels context, intent_result param
#   v4b   2026-04-03  SB  Added register_map to _build_context; PSS template generates register actions
#
# ===========================================================
"""agents/pss_gen.py — PSS model generation agent.

Phase: v1b
Layer: 3 (agents)

Generates a PSS v3.0 model from IR via a Jinja2 skeleton in no-LLM mode or via
LLM completion in production mode.
"""

from __future__ import annotations

import os
import re

import anthropic
from jinja2 import Environment, FileSystemLoader

from ir import IR


TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "pss")
TEMPLATE_NAME = "component.pss.jinja"


def generate_pss(
    ir: IR,
    fail_reason: str | None = None,
    no_llm: bool = False,
    intent_result=None,
) -> str:
    """Generate a PSS v3.0 model from the IR.

    Args:
        ir: Parsed design intermediate representation.
        fail_reason: Optional checker feedback from prior attempt.
        no_llm: If True, return template-rendered output without API usage.
        intent_result: Optional IntentParseResult for coverage label derivation.

    Returns:
        PSS model source text.

    Side Effects:
        Stores generated source in ``ir.pss_model``.
    """
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(TEMPLATE_NAME)
    context = _build_context(ir, intent_result=intent_result)
    skeleton = template.render(**context)

    if no_llm:
        ir.pss_model = skeleton
        return skeleton

    prompt = _build_prompt(ir, skeleton, fail_reason)
    model = _call_llm(prompt)
    ir.pss_model = model
    return model


def _build_context(ir: IR, intent_result=None) -> dict:
    """Build template context groups from IR ports.

    Args:
        ir: Parsed design intermediate representation.
        intent_result: Optional IntentParseResult for coverage label derivation.

    Returns:
        Context dictionary for PSS Jinja2 rendering.
    """
    ports = ir.ports
    coverage_labels = _build_coverage_labels(ir, intent_result)
    return {
        "design_name": ir.design_name,
        "pss_intent": ir.pss_intent,
        "ports": ports,
        "clock_ports": [p for p in ports if p.role == "clock"],
        "reset_ports": [p for p in ports if p.role in {"reset", "reset_n"}],
        "control_ports": [p for p in ports if p.role == "control" and p.direction == "input"],
        "data_ports": [p for p in ports if p.role == "data" and p.direction == "output"],
        "coverage_labels": coverage_labels,
        "register_map": ir.register_map,
    }


def _build_coverage_labels(ir: IR, intent_result=None) -> list[dict]:
    """Build a three-tier hierarchy of PSS coverage labels.

    Tier 1 (highest priority): Lines with [REQ-xxx] IDs — labelled by req ID.
    Tier 2: Intent section headings without a req ID — labelled by section.
    Tier 3 (fallback): IR port inference — one entry per data output and reset port
        not already covered by Tier 1 or 2.

    Args:
        ir: Parsed design intermediate representation.
        intent_result: Optional IntentParseResult (IntentParseResult | None).
            Pass None when no intent is loaded.

    Returns:
        List of coverage label dicts with keys: label, display, source,
        req_id, waived, waiver_reason.
    """
    labels: list[dict] = []
    seen_req_ids: set[str] = set()

    # Build set of waived req IDs for quick lookup
    waived_req_ids: set[str] = set()
    waiver_reasons: dict[str, str] = {}
    # Prefer intent_waivers (list[dict]) over waivers (list[str]).
    # VplanParseResult exposes both; .waivers is list[str] (IDs only).
    _waivers_src = (
        intent_result.intent_waivers
        if (intent_result is not None and hasattr(intent_result, "intent_waivers"))
        else (
            intent_result.waivers
            if (intent_result is not None and hasattr(intent_result, "waivers"))
            else []
        )
    )
    for w in _waivers_src:
        if isinstance(w, dict):
            for rid in w.get("req_ids", []):
                waived_req_ids.add(rid)
                waiver_reasons[rid] = w.get("reason", "")
        elif isinstance(w, str):
            waived_req_ids.add(w)

    # --- Tier 1: lines with [REQ-xxx] IDs ---
    if intent_result is not None and hasattr(intent_result, "req_ids"):
        for req_id in intent_result.req_ids:
            if req_id in seen_req_ids:
                continue
            seen_req_ids.add(req_id)
            # PSS-safe: hyphens → underscores, prefix cg_
            safe = "cg_" + req_id.replace("-", "_")
            is_waived = req_id in waived_req_ids
            labels.append({
                "label": safe,
                "display": req_id,
                "source": "requirement",
                "req_id": req_id,
                "waived": is_waived,
                "waiver_reason": waiver_reasons.get(req_id),
            })

    # --- Tier 2: intent sections (no req ID) ---
    _SKIP_SECTIONS = {"intent gaps"}
    if intent_result is not None and hasattr(intent_result, "sections"):
        section_counters: dict[str, int] = {}
        for heading in intent_result.sections:
            if heading.lower() in _SKIP_SECTIONS:
                continue
            # One entry per section (section-level goal)
            base = "cg_" + re.sub(r"[^a-z0-9]+", "_", heading.lower()).strip("_")
            section_counters[base] = section_counters.get(base, 0) + 1
            count = section_counters[base]
            label = f"{base}_{count:02d}"
            labels.append({
                "label": label,
                "display": heading,
                "source": "intent",
                "req_id": None,
                "waived": False,
                "waiver_reason": None,
            })

    # --- Tier 3: IR port inference ---
    # Only for ports NOT already covered by Tier 1 or Tier 2.
    # Data output ports and reset ports get inferred entries.
    # Control inputs do NOT.
    tier12_labels_lower = {lbl["label"].lower() for lbl in labels}
    for port in ir.ports:
        if port.role not in ("data", "reset", "reset_n"):
            continue
        if port.role == "data" and port.direction != "output":
            continue
        inferred_label = f"cg_inferred_{port.name}_01"
        if inferred_label.lower() in tier12_labels_lower:
            continue
        labels.append({
            "label": inferred_label,
            "display": port.name,
            "source": "inferred",
            "req_id": None,
            "waived": False,
            "waiver_reason": None,
        })

    return labels


def _build_prompt(ir: IR, skeleton: str, fail_reason: str | None) -> str:
    """Build the production LLM prompt for PSS completion.

    Args:
        ir: Parsed design intermediate representation.
        skeleton: Template-rendered PSS skeleton.
        fail_reason: Optional checker feedback from prior attempt.

    Returns:
        Prompt string for LLM completion.
    """
    if ir.pss_intent is None:
        lines = [
            "Generate a valid PSS v3.0 model.",
            f"Design name: {ir.design_name}",
            f"Ports: {[p.__dict__ for p in ir.ports]}",
            "Fill the constraints and coverage placeholders with meaningful content.",
            "Return only PSS DSL source code.",
            "",
            skeleton,
        ]
    else:
        lines = [
            "Generate a valid PSS v3.0 model.",
            "Use the provided intent to produce specific, meaningful PSS constraints",
            "and coverage goals instead of generic placeholders.",
            "",
            "PSS skeleton:",
            skeleton,
            "",
            "IR context:",
            f"- Design name: {ir.design_name}",
            f"- Port roles: {[p.__dict__ for p in ir.ports]}",
            "",
            "Structured natural language intent:",
            ir.pss_intent,
            "",
            "Return only PSS DSL source code.",
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
