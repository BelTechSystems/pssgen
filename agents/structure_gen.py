"""
Structure generator agent (v0).
Renders Jinja2 UVM templates then calls the LLM to fill dynamic content.
Returns a list of Artifacts (filename + content string).
"""
from dataclasses import dataclass
from typing import Optional
from jinja2 import Environment, FileSystemLoader
from ir import IR
import os, anthropic


@dataclass
class Artifact:
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
    name = tmpl_name.replace(".jinja", "").replace("interface", f"{design_name}_if")
    for role in ["driver", "monitor", "sequencer", "agent", "test"]:
        name = name.replace(role, f"{design_name}_{role}")
    name = name.replace("build_vivado", "build")
    return name


def _build_prompt(ir: IR, tmpl_name: str, partial: str, fail_reason: Optional[str]) -> str:
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
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
