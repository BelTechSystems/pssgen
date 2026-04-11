#!/usr/bin/env bash
# ===========================================================
# FILE:    scripts/hdl_check.sh
# PROJECT: pssgen — AI-Driven PSS + UVM + C Testbench Generator
# PURPOSE: Canonical HDL gate used by the pre-commit hook and CI.
#          Checks syntax, forbidden patterns, and unread-signal warnings.
#
# USAGE:   scripts/hdl_check.sh [file ...]
#          With no arguments, delegates syntax checking to each
#          ip/<block>/syntax/ directory and scans all HDL files
#          under ip/ for pattern and signal checks.
#          With file arguments (pre-commit hook mode), checks those
#          files directly: ghdl/iverilog for DUT files, patterns
#          and warnings for all files.
#
# EXIT:    0 if all checks pass, 1 if any failure is detected.
#
# NOTE:    UVM testbench .sv files are excluded from pre-commit
#          syntax checking. Their syntax is verified by the full
#          simulation flow in tb/scripts/<tool>/ (xvlog --uvm,
#          vlog, etc.) which requires a simulator license. Pattern
#          and unread-signal checks still run on UVM files.
# ===========================================================

set -euo pipefail

FAIL=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Helper: is this a UVM-dependent SV file? ────────────────────────────────
# Detection: file contains a backtick-uvm_ macro or 'extends uvm_'.
is_uvm_file() {
    grep -qE '`uvm_|extends[[:space:]]+uvm_|import[[:space:]]+uvm_pkg' "$1" 2>/dev/null
}

# ── Collect files for pattern and warning checks ─────────────────────────────
if [ "$#" -gt 0 ]; then
    FILES=("$@")
    FILE_MODE=1
else
    mapfile -t FILES < <(find "$REPO_ROOT/ip" -type f \( -name "*.vhd" -o -name "*.sv" \))
    FILE_MODE=0
fi

if [ "${#FILES[@]}" -eq 0 ]; then
    echo "hdl_check.sh: no HDL files found — nothing to check."
    exit 0
fi

# ── A. SYNTAX ────────────────────────────────────────────────────────────────
if [ "$FILE_MODE" -eq 0 ]; then
    # Scan mode: delegate to each IP block's own syntax/ scripts.
    # Each script is self-contained and knows which DUT file to check.
    # This makes hdl_check.sh language-agnostic — new IP blocks with
    # different DUT languages add their own syntax/ scripts.
    for syntax_dir in "$REPO_ROOT"/ip/*/syntax/; do
        [ -d "$syntax_dir" ] || continue
        block=$(basename "$(dirname "$syntax_dir")")

        if [ -x "${syntax_dir}check_vhdl.sh" ]; then
            if ! bash "${syntax_dir}check_vhdl.sh" 2>&1; then
                echo "SYNTAX ERROR: $block check_vhdl.sh failed"
                FAIL=1
            fi
        fi

        if [ -x "${syntax_dir}check_sv.sh" ]; then
            if ! bash "${syntax_dir}check_sv.sh" 2>&1; then
                echo "SYNTAX ERROR: $block check_sv.sh failed"
                FAIL=1
            fi
        fi
    done
else
    # File mode (pre-commit hook): check DUT files directly.
    # UVM testbench files are skipped — they require a full simulator
    # environment and are verified by tb/scripts/<tool>/ flows.
    for f in "${FILES[@]}"; do
        if is_uvm_file "$f"; then
            # Pattern and warning checks still run below — skip syntax only.
            true
        else
            case "$f" in
                *.vhd)
                    if ! ghdl -a --std=08 "$f" 2>/dev/null; then
                        echo "SYNTAX ERROR: $f"
                        FAIL=1
                    fi
                    ;;
                *.sv)
                    if ! iverilog -g2012 -t null "$f" 2>/dev/null; then
                        echo "SYNTAX ERROR: $f"
                        FAIL=1
                    fi
                    ;;
            esac
        fi
    done
fi

# ── B. FORBIDDEN PATTERNS ────────────────────────────────────────────────────
for f in "${FILES[@]}"; do
    # Bare null statement (stub body) — VHDL only.
    # Excludes legitimate case-default: "when others => null;"
    # by skipping any null; whose preceding non-blank line ends with '=>'.
    if [[ "$f" == *.vhd ]]; then
        null_hits=$(python3 -c "
import sys, re
path = sys.argv[1]
lines = open(path, encoding='utf-8', errors='replace').splitlines()
prev = ''
for i, line in enumerate(lines, 1):
    s = line.strip()
    if re.match(r'^null;\s*$', s) and not re.search(r'=>\s*$', prev):
        print(i)
    if s:
        prev = s
" "$f" 2>/dev/null || true)
        if [ -n "$null_hits" ]; then
            while IFS= read -r lineno; do
                echo "$f:$lineno: STUB: bare null statement"
                FAIL=1
            done <<< "$null_hits"
        fi
    fi

    # TODO / FIXME / STUB markers — both languages
    while IFS= read -r match; do
        lineno="${match%%:*}"
        echo "$f:$lineno: INCOMPLETE: TODO/FIXME/STUB marker"
        FAIL=1
    done < <(grep -nE '\b(TODO|FIXME|STUB)\b' "$f" 2>/dev/null || true)
done

# ── C. UNREAD WRITE WARNING (stderr, not a failure) ─────────────────────────
# For each *_s signal: warn if it appears on the left-hand side of <= or =
# but never on the right-hand side or in a condition anywhere in the same file.
# Uses a single-pass Python scan — not a full HDL parser.

python3 - "${FILES[@]}" <<'PYEOF'
import sys, re

files = sys.argv[1:]

for path in files:
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        continue

    lines = text.splitlines()

    # Collect all *_s identifiers that appear on the LHS of <= or =
    lhs_signals = set()
    for line in lines:
        for m in re.finditer(r'\b(\w+_s)\b\s*(?:<=|(?<![=<>!])=(?!=))', line):
            lhs_signals.add(m.group(1))

    for sig in sorted(lhs_signals):
        rhs_count = 0
        for line in lines:
            stripped = line.strip()
            # Skip lines that are pure LHS assignments
            if re.match(rf'^{re.escape(sig)}\s*(?:<=|=(?!=))', stripped):
                continue
            if re.search(rf'\b{re.escape(sig)}\b', line):
                rhs_count += 1

        if rhs_count == 0:
            print(f"WARNING: {sig} written but never read in {path}",
                  file=sys.stderr)
PYEOF

# ── Result ───────────────────────────────────────────────────────────────────
if [ "$FAIL" -eq 1 ]; then
    echo "hdl_check.sh: one or more checks FAILED."
    exit 1
fi

echo "hdl_check.sh: all checks passed."
exit 0
