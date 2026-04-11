#!/usr/bin/env bash
# ===========================================================
# FILE:    scripts/hdl_check.sh
# PROJECT: pssgen — AI-Driven PSS + UVM + C Testbench Generator
# PURPOSE: Canonical HDL gate used by the pre-commit hook and CI.
#          Checks syntax, forbidden patterns, and unread-signal warnings.
#
# USAGE:   scripts/hdl_check.sh [file ...]
#          With no arguments, scans all .vhd and .sv files under ip/.
#
# EXIT:    0 if all checks pass, 1 if any failure is detected.
#
# NOTE:    UVM testbench .sv files (those containing `uvm_ macros or
#          'extends uvm_') require the UVM library to parse and are
#          skipped from iverilog syntax checking.  Pattern and
#          unread-signal checks still run on those files.
# ===========================================================

set -euo pipefail

FAIL=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Collect files ────────────────────────────────────────────────────────────
if [ "$#" -gt 0 ]; then
    FILES=("$@")
else
    mapfile -t FILES < <(find "$REPO_ROOT/ip" -type f \( -name "*.vhd" -o -name "*.sv" \))
fi

if [ "${#FILES[@]}" -eq 0 ]; then
    echo "hdl_check.sh: no HDL files found — nothing to check."
    exit 0
fi

# ── Helper: is this a UVM-dependent SV file? ────────────────────────────────
# UVM files use macros/packages that require the UVM library to parse.
# Detection: file contains a backtick-uvm_ macro or 'extends uvm_'.
is_uvm_file() {
    grep -qE '`uvm_|extends[[:space:]]+uvm_|import[[:space:]]+uvm_pkg' "$1" 2>/dev/null
}

# ── A. SYNTAX ────────────────────────────────────────────────────────────────
for f in "${FILES[@]}"; do
    case "$f" in
        *.vhd)
            if ! ghdl -a --std=08 "$f" 2>/dev/null; then
                echo "SYNTAX ERROR: $f"
                FAIL=1
            fi
            ;;
        *.sv)
            if is_uvm_file "$f"; then
                # Cannot syntax-check without UVM library — skip silently.
                # Pattern and unread-signal checks below still apply.
                true
            else
                if ! iverilog -g2012 -t null "$f" 2>/dev/null; then
                    echo "SYNTAX ERROR: $f"
                    FAIL=1
                fi
            fi
            ;;
    esac
done

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
# inside a clocked process/always_ff block but never on the right-hand side
# or inside an if/case condition anywhere in the same file.
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
