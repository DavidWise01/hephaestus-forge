
import json, hashlib, sqlite3, time, zipfile
from pathlib import Path

def digest(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()

class ForgeIntelligence:
    BUILDERS = {
        "dashboard": ("builder:dashboard", "Application"),
        "workflow": ("builder:workflow", "Workflow"),
        "report": ("builder:report", "Report"),
        "api": ("builder:api", "Service"),
        "database": ("builder:database", "Storage"),
        "security": ("builder:security", "Shield"),
        "generic": ("builder:generic", "Tool")
    }

    def __init__(self, db="forge_intelligence.db", artifacts="artifacts", releases="releases", plans="plans"):
        self.artifacts = Path(artifacts); self.artifacts.mkdir(parents=True, exist_ok=True)
        self.releases = Path(releases); self.releases.mkdir(parents=True, exist_ok=True)
        self.plans = Path(plans); self.plans.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(Path(db)); self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS builders(id TEXT PRIMARY KEY,type TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS plans(id TEXT PRIMARY KEY,idea TEXT,status TEXT,h TEXT,path TEXT);
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,plan_id TEXT,name TEXT,builder TEXT,status TEXT,depends_on TEXT,artifact TEXT);
        CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY,plan_id TEXT,task_id TEXT,name TEXT,type TEXT,builder TEXT,status TEXT,h TEXT,path TEXT);
        CREATE TABLE IF NOT EXISTS releases(id TEXT PRIMARY KEY,artifact TEXT,version TEXT,h TEXT,path TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """)
        for _, (bid, typ) in self.BUILDERS.items():
            self.conn.execute("INSERT OR REPLACE INTO builders VALUES(?,?,?)", (bid, typ, "active"))
        self.conn.commit()

    def last_hash(self):
        r = self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"

    def receipt(self, kind, subject, payload):
        ph = digest(payload); prev = self.last_hash()
        eh = digest({"kind": kind, "subject": subject, "payload_hash": ph, "prev_hash": prev})
        self.conn.execute("INSERT INTO ledger(kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?)", (kind, subject, ph, prev, eh))
        self.conn.commit()

    def verify_ledger(self):
        prev = "GENESIS"; n = 0
        for r in self.conn.execute("SELECT * FROM ledger ORDER BY seq"):
            exp = digest({"kind": r["kind"], "subject": r["subject"], "payload_hash": r["payload_hash"], "prev_hash": prev})
            if r["prev_hash"] != prev or r["entry_hash"] != exp:
                return {"ok": False, "seq": r["seq"]}
            prev = r["entry_hash"]; n += 1
        return {"ok": True, "entries": n, "head": prev}

    def select(self, text):
        low = text.lower()
        if any(x in low for x in ["dashboard", "console", "portal", "ui"]): return self.BUILDERS["dashboard"]
        if any(x in low for x in ["workflow", "renewal", "appeal", "process", "case"]): return self.BUILDERS["workflow"]
        if any(x in low for x in ["report", "audit", "evidence", "packet"]): return self.BUILDERS["report"]
        if any(x in low for x in ["api", "server", "service", "gateway"]): return self.BUILDERS["api"]
        if any(x in low for x in ["database", "storage", "persistence", "ledger"]): return self.BUILDERS["database"]
        if any(x in low for x in ["security", "auth", "permission", "authority", "verify"]): return self.BUILDERS["security"]
        return self.BUILDERS["generic"]

    def decompose(self, idea):
        low = idea.lower()
        tasks = []
        def add(name, text, deps=None):
            bid, typ = self.select(text)
            tasks.append({"name": name, "intent": text, "builder": bid, "type": typ, "depends_on": deps or []})
        add("core_database", "database storage ledger persistence for " + idea)
        add("core_api", "api service gateway for " + idea, ["core_database"])
        if any(x in low for x in ["dashboard", "console", "monitor", "live", "operator"]):
            add("operator_dashboard", "dashboard console ui for " + idea, ["core_api"])
        if any(x in low for x in ["workflow", "process", "case", "renewal", "appeal"]):
            add("workflow_engine", "workflow process case engine for " + idea, ["core_database", "core_api"])
        if any(x in low for x in ["report", "audit", "evidence", "packet", "compliance"]):
            add("reporting_pack", "report audit evidence packet for " + idea, ["core_database"])
        if any(x in low for x in ["security", "auth", "permission", "authority", "verify"]):
            add("security_shield", "security authority verification shield for " + idea, ["core_api"])
        if len(tasks) < 5:
            add("test_harness", "test verification harness for " + idea, ["core_api"])
            add("release_manifest", "report release manifest audit packet for " + idea, ["core_database"])
        return tasks

    def plan(self, idea):
        tasks = self.decompose(idea)
        payload = {"version": "0.5.0", "idea": idea, "tasks": tasks, "created": time.time()}
        h = digest(payload); pid = "plan:" + h[:16]
        path = self.plans / f"{pid.replace(':','_')}.json"
        path.write_text(json.dumps(payload, indent=2))
        self.conn.execute("INSERT OR REPLACE INTO plans VALUES(?,?,?,?,?)", (pid, idea, "planned", h, str(path)))
        for t in tasks:
            tid = "task:" + digest({"plan": pid, "name": t["name"]})[:16]
            self.conn.execute("INSERT OR REPLACE INTO tasks VALUES(?,?,?,?,?,?,?)", (tid, pid, t["name"], t["builder"], "planned", json.dumps(t["depends_on"]), ""))
        self.receipt("plan_created", pid, {"tasks": len(tasks), "hash": h})
        self.conn.commit()
        return {"plan": pid, "tasks": len(tasks), "hash": h, "path": str(path)}

    def ready(self, pid):
        done = {r["name"] for r in self.conn.execute("SELECT name FROM tasks WHERE plan_id=? AND status='released'", (pid,))}
        rows = [dict(r) for r in self.conn.execute("SELECT * FROM tasks WHERE plan_id=? AND status='planned'", (pid,))]
        return [r for r in rows if all(d in done for d in json.loads(r["depends_on"] or "[]"))]

    def build_task(self, t):
        typ = self.conn.execute("SELECT type FROM builders WHERE id=?", (t["builder"],)).fetchone()["type"]
        payload = {"version": "0.5.0", "plan_id": t["plan_id"], "task_id": t["id"], "name": t["name"], "builder": t["builder"], "type": typ, "dependencies": json.loads(t["depends_on"] or "[]"), "requirements": ["planned", "dependencies resolved", "verified", "released"]}
        h = digest(payload); aid = "artifact:" + h[:16]
        path = self.artifacts / f"{aid.replace(':','_')}.json"
        payload["artifact_id"] = aid
        path.write_text(json.dumps(payload, indent=2))
        self.conn.execute("INSERT OR REPLACE INTO artifacts VALUES(?,?,?,?,?,?,?,?,?)", (aid, t["plan_id"], t["id"], t["name"], typ, t["builder"], "released", h, str(path)))
        rel_payload = {"artifact": aid, "version": "0.1.0", "hash": h, "created": time.time()}
        rh = digest(rel_payload); rid = "release:" + rh[:16]
        rpath = self.releases / f"{rid.replace(':','_')}.json"
        rpath.write_text(json.dumps(rel_payload, indent=2))
        self.conn.execute("INSERT OR REPLACE INTO releases VALUES(?,?,?,?,?)", (rid, aid, "0.1.0", rh, str(rpath)))
        self.conn.execute("UPDATE tasks SET status='released', artifact=? WHERE id=?", (aid, t["id"]))
        self.receipt("artifact_released", rid, {"artifact": aid, "hash": rh})
        self.conn.commit()
        return {"artifact": aid, "release": rid, "task": t["name"]}

    def execute(self, pid):
        released = []
        guard = 0
        while True:
            rdy = self.ready(pid)
            remaining = self.conn.execute("SELECT COUNT(*) n FROM tasks WHERE plan_id=? AND status!='released'", (pid,)).fetchone()["n"]
            if remaining == 0:
                self.conn.execute("UPDATE plans SET status='released' WHERE id=?", (pid,))
                self.receipt("plan_released", pid, {"released": len(released)})
                self.conn.commit()
                return {"plan": pid, "status": "released", "released": released}
            if not rdy:
                guard += 1
                if guard > 3:
                    self.conn.execute("UPDATE plans SET status='stalled' WHERE id=?", (pid,))
                    self.conn.commit()
                    return {"plan": pid, "status": "stalled", "released": released}
            for t in rdy:
                released.append(self.build_task(t))

    def build_system(self, idea):
        p = self.plan(idea)
        result = self.execute(p["plan"])
        return {"plan": p, "result": result, "stats": self.stats()}

    def stats(self):
        return {
            "builders": self.conn.execute("SELECT COUNT(*) n FROM builders").fetchone()["n"],
            "plans": self.conn.execute("SELECT COUNT(*) n FROM plans").fetchone()["n"],
            "tasks": self.conn.execute("SELECT COUNT(*) n FROM tasks").fetchone()["n"],
            "released_tasks": self.conn.execute("SELECT COUNT(*) n FROM tasks WHERE status='released'").fetchone()["n"],
            "artifacts": self.conn.execute("SELECT COUNT(*) n FROM artifacts").fetchone()["n"],
            "releases": self.conn.execute("SELECT COUNT(*) n FROM releases").fetchone()["n"],
            "ledger": self.verify_ledger(),
            "db_integrity": self.conn.execute("PRAGMA integrity_check").fetchone()[0]
        }

    def dashboard(self):
        return {
            "version": "0.5.0",
            "plans": [dict(r) for r in self.conn.execute("SELECT * FROM plans ORDER BY id")],
            "tasks": [dict(r) for r in self.conn.execute("SELECT * FROM tasks ORDER BY id")],
            "artifacts": [dict(r) for r in self.conn.execute("SELECT * FROM artifacts ORDER BY id")],
            "releases": [dict(r) for r in self.conn.execute("SELECT * FROM releases ORDER BY id")],
            "stats": self.stats()
        }

    def export(self, out):
        out = Path(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("forge_intelligence_dashboard.json", json.dumps(self.dashboard(), indent=2))
            for t in ["builders", "plans", "tasks", "artifacts", "releases", "ledger"]:
                z.writestr(f"{t}.json", json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")], indent=2))
            for p in sorted(self.plans.glob("*.json")): z.write(p, arcname=f"plans/{p.name}")
            for p in sorted(self.artifacts.glob("*.json")): z.write(p, arcname=f"artifacts/{p.name}")
            for p in sorted(self.releases.glob("*.json")): z.write(p, arcname=f"releases/{p.name}")
        return {"bundle": str(out), "exists": out.exists()}

def seed_demo(td):
    f = ForgeIntelligence(Path(td)/"forge.db", Path(td)/"artifacts", Path(td)/"releases", Path(td)/"plans")
    build = f.build_system("create live operator dashboard with workflow process, audit evidence packet, security verification, and api service")
    return {"build": build, "dashboard": f.dashboard(), "bundle": f.export(Path(td)/"bundle.zip")}
