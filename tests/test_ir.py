"""Unit tests for IR serialization round-trip."""
import json
from ir import IR, Port


def _make_ir():
    return IR(
        design_name="up_down_counter",
        hdl_source="tests/fixtures/counter.v",
        hdl_language="verilog",
        ports=[Port("clk", "input", 1, "clock")],
        parameters={"WIDTH": "8"},
        emission_target="vivado",
        output_dir="./out",
    )


def test_ir_roundtrip():
    ir = _make_ir()
    serialized = json.dumps(ir.__dict__, default=lambda o: o.__dict__)
    data = json.loads(serialized)
    assert data["design_name"] == "up_down_counter"
    assert data["ports"][0]["name"] == "clk"


def test_ir_optional_pss_intent_default():
    ir = _make_ir()
    assert ir.pss_intent is None
