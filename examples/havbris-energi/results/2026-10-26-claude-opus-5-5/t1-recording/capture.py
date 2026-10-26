import json, os, subprocess, sys, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "scripts"))
import run_havbris_eval as r
sp = r.system_prompt(r.upload_set())
spp = os.path.join(tempfile.mkdtemp(), "project.md"); open(spp, "w").write(sp)
prompt = "Run AIG 07 Mode D for ChatNordic using files 02 and 03."
out = open(sys.argv[1], "w")
with tempfile.TemporaryDirectory() as empty:
    cmd = ["claude", "-p", prompt, "--restricted", "--system-prompt-file", spp, "--tools", "",
           "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--setting-sources", "",
           "--no-session-persistence", "--model", "claude-opus-5-5",
           "--output-format", "stream-json", "--include-partial-messages", "--verbose"]
    t0 = time.time()
    p = subprocess.Popen(cmd, cwd=empty, stdout=subprocess.PIPE, text=True)
    for line in p.stdout:
        try: ev = json.loads(line)
        except Exception: continue
        t = round(time.time() - t0, 3)
        if ev.get("type") == "stream_event":
            e = ev.get("event", {})
            if e.get("type") == "content_block_delta" and e.get("delta", {}).get("type") == "text_delta":
                out.write(json.dumps({"t": t, "text": e["delta"]["text"]}) + "\n"); out.flush()
        elif ev.get("type") == "result":
            out.write(json.dumps({"t": t, "final": ev.get("result"), "is_error": ev.get("is_error"), "cost": ev.get("total_cost_usd"), "models": list((ev.get("modelUsage") or {}).keys())}) + "\n")
    p.wait()
