#!/usr/bin/env python3
"""Recorded evaluation of the five public agents on the Havbris Energi test case.

Each step in examples/havbris-energi/TEST-SCRIPT.md runs in its own fresh,
tool-less Claude session (Claude Code CLI in print mode). The session gets:

- the Project Instructions as its custom instructions, and
- as project knowledge, only the files a user would upload: everything in
  department/ except the blank Context File, plus the Havbris Context File and
  case files 01 to 06.

It never sees TEST-SCRIPT.md (the answer key), either README, or the output of
an earlier step. Raw outputs are saved unedited, one file per step, with the
run metadata next to them.

Usage: python scripts/run_havbris_eval.py [--model claude-opus-5-5] [--steps 1,2,3,4,5]
Needs the `claude` CLI, logged in.
"""
import argparse, datetime, hashlib, json, os, subprocess, tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DEPT = os.path.join(REPO, "department")
CASE = os.path.join(REPO, "examples", "havbris-energi")

STEPS = [
    (1, "aig03-mode-a", "Run AIG 03 Mode A on the idea in file 01."),
    (2, "aig07-mode-d", "Run AIG 07 Mode D for ChatNordic using files 02 and 03."),
    (3, "aig07-mode-a-b", "Run AIG 07 Mode A and then Mode B for KundeAssist."),
    (4, "aig11-mode-a", "Run AIG 11 Mode A, pre-deployment gate, for KundeAssist."),
    (5, "aig15-mode-a-b", "Run AIG 15 Mode A for KundeAssist using file 05, then Mode B for file 06."),
]

CASE_FILES = [
    "context-file-havbris.md",
    "01-use-case-idea.md",
    "02-vendor-fact-sheet.md",
    "03-system-notes.md",
    "04-committee-minutes.md",
    "05-monitoring-log.csv",
    "06-incident-raw.md",
]


def upload_set():
    files = [os.path.join(DEPT, f) for f in sorted(os.listdir(DEPT))
             if f.endswith(".md") and f != "AI Governance Context File.md"]
    files += [os.path.join(CASE, f) for f in CASE_FILES]
    return files


def system_prompt(files):
    instructions = open(os.path.join(DEPT, "01 PROJECT INSTRUCTIONS.md"), encoding="utf-8").read()
    docs = "\n\n".join(
        f'<document name="{os.path.basename(p)}">\n{open(p, encoding="utf-8").read().strip()}\n</document>'
        for p in files)
    return ("You are working inside a Claude Project. The project's custom instructions and the files "
            "uploaded to its knowledge follow.\n\n"
            f"<project_instructions>\n{instructions.strip()}\n</project_instructions>\n\n"
            f"<project_knowledge>\n{docs}\n</project_knowledge>\n")


def run_step(model, sp_path, prompt):
    with tempfile.TemporaryDirectory() as empty:
        cmd = ["claude", "-p", prompt, "--restricted", "--system-prompt-file", sp_path,
               "--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
               "--setting-sources", "", "--no-session-persistence",
               "--model", model, "--output-format", "json"]
        p = subprocess.run(cmd, cwd=empty, capture_output=True, text=True, timeout=1500)
    return json.loads(p.stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--steps", default="1,2,3,4,5")
    a = ap.parse_args()
    wanted = {int(s) for s in a.steps.split(",")}

    today = datetime.date.today().isoformat()
    out_dir = os.path.join(CASE, "results", f"{today}-{a.model}")
    os.makedirs(out_dir, exist_ok=True)

    files = upload_set()
    sp = system_prompt(files)
    sp_path = os.path.join(tempfile.mkdtemp(), "project.md")
    open(sp_path, "w", encoding="utf-8").write(sp)

    meta_path = os.path.join(out_dir, "run.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {
        "date": today,
        "model_requested": a.model,
        "cli_version": subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip(),
        "setup": "One fresh print-mode session per step, no tools, no MCP servers, no settings, "
                 "empty working directory. Project Instructions as custom instructions; project "
                 "knowledge = the files below. Answer key and READMEs never included.",
        "project_knowledge": {os.path.relpath(p, REPO): hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
                              for p in files},
        "system_prompt_sha256": hashlib.sha256(sp.encode()).hexdigest()[:16],
        "steps": {},
    }

    for n, slug, prompt in STEPS:
        if n not in wanted:
            continue
        print(f"step {n}: {prompt}", flush=True)
        r = run_step(a.model, sp_path, prompt)
        name = f"step-{n}-{slug}.md"
        open(os.path.join(out_dir, name), "w", encoding="utf-8").write(r.get("result", ""))
        meta["steps"][str(n)] = {
            "prompt": prompt,
            "output_file": name,
            "is_error": r.get("is_error"),
            "models_used": sorted((r.get("modelUsage") or {}).keys()),
            "duration_s": round((r.get("duration_ms") or 0) / 1000, 1),
            "cost_usd": round(r.get("total_cost_usd") or 0, 4),
            "num_turns": r.get("num_turns"),
        }
        json.dump(meta, open(meta_path, "w"), indent=2)
        print(f"  saved {name}", flush=True)


if __name__ == "__main__":
    main()
