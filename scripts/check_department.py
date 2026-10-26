#!/usr/bin/env python3
"""Quality checks for the AI Governance Department.

Checks that every agent file is complete and consistent, that the shared rules
match the project instructions word for word, that every template an agent
names actually exists, that no em dashes slipped in, and (with --full) that the
agents together cover every task in the Hourglass Model 2026 edition.

Usage: python scripts/check_department.py [--full]
"""
import os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "department")
FULL = "--full" in sys.argv
EM_DASH = chr(0x2014)
errors = []

files = sorted(f for f in os.listdir(ROOT) if f.endswith(".md"))
agents = [f for f in files if f.startswith("AGENT AIG")]
templates = {f[len("TEMPLATE - "):-3].lower() for f in files if f.startswith("TEMPLATE - ")}
instructions = open(os.path.join(ROOT, "01 PROJECT INSTRUCTIONS.md"), encoding="utf-8").read()
shared = instructions[instructions.index("Shared rules for every AIG agent:"):].strip()

for root, _, names in os.walk(os.path.join(ROOT, "..")):
    if ".git" in root:
        continue
    for n in names:
        if n.endswith((".md", ".csv", ".txt", ".py", ".yml")):
            p = os.path.join(root, n)
            if EM_DASH in open(p, encoding="utf-8").read():
                errors.append(f"em dash in {os.path.relpath(p, os.path.join(ROOT, '..'))}")

covered = set()
for f in agents:
    s = open(os.path.join(ROOT, f), encoding="utf-8").read()
    for label in ("Hourglass Model 2026:", "Your job:", "Output:", "Hand off to:"):
        if label not in s:
            errors.append(f"{f}: missing '{label}'")
    if shared not in s:
        errors.append(f"{f}: shared rules differ from 01 PROJECT INSTRUCTIONS")
    out = re.search(r"Output: (.*)", s)
    for name in re.findall(r"([A-Z][A-Za-z ]+?) template", out.group(1) if out else ""):
        if name.strip().lower() not in templates:
            errors.append(f"{f}: names template '{name.strip()}' which is not in this folder")
    hg = re.search(r"Hourglass Model 2026: (.*)", s)
    for m in re.finditer(r"([A-G])(\d)(?: to ([A-G])?(\d))?", hg.group(1) if hg else ""):
        L, a, _, b = m.groups()
        for i in range(int(a), int(b or a) + 1):
            covered.add(f"{L}{i}")

if FULL:
    need = {f"{L}{i}" for L, n in zip("ABCDEFG", [6, 9, 8, 7, 8, 5, 6]) for i in range(1, n + 1)}
    missing = sorted(need - covered, key=lambda x: (x[0], int(x[1:])))
    if missing:
        errors.append("Hourglass 2026 tasks not covered by any agent: " + ", ".join(missing))

print(f"{len(agents)} agents, {len(templates)} templates checked")
if FULL:
    print(f"Hourglass 2026 tasks covered: {len(covered)}")
if errors:
    print("\n".join("FAIL " + e for e in errors))
    sys.exit(1)
print("All checks passed")
