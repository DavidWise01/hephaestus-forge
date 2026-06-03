
import json, hashlib, sqlite3, time, zipfile
from pathlib import Path

def digest(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()

class AssemblyLine:
    BUILDERS = {
        "dashboard": ("builder:dashboard", "Dashboard Builder"),
        "workflow": ("builder:workflow", "Workflow Builder"),
        "report": ("builder:report", "Report Builder"),
        "api": ("builder:api", "API Builder"),
        "generic": ("builder:generic", "Generic Builder")
    }

    def __init__(self, db="assembly.db", out="artifacts", releases="releases"):
        self.out = Path(out); self.out.mkdir(parents=True, exist_ok=True)
        self.releases = Path(releases); self.releases.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(Path(db)); self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS builders(id TEXT PRIMARY KEY,name TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS queue(id TEXT PRIMARY KEY,idea TEXT,builder TEXT,status TEXT,artifact TEXT);
        CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY,name TEXT,type TEXT,builder TEXT,status TEXT,h TEXT,path TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS releases(id TEXT PRIMARY KEY,artifact TEXT,version TEXT,h TEXT,path TEXT);
        CREATE TABLE IF NOT EXISTS checks(id INTEGER PRIMARY KEY,subject TEXT,name TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """)
        self.conn.commit()
        for _, (bid, name) in self.BUILDERS.items():
            self.conn.execute("INSERT OR REPLACE INTO builders VALUES(?,?,?)", (bid, name, "active"))
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

    def select_builder(self, idea):
        low = idea.lower()
        if any(x in low for x in ["dashboard", "portal", "console"]): return self.BUILDERS["dashboard"][0]
        if any(x in low for x in ["workflow", "renewal", "appeal", "process"]): return self.BUILDERS["workflow"][0]
        if any(x in low for x in ["report", "audit", "evidence"]): return self.BUILDERS["report"][0]
        if any(x in low for x in ["api", "server", "service"]): return self.BUILDERS["api"][0]
        return self.BUILDERS["generic"][0]

    def enqueue(self, idea):
        bid = self.select_builder(idea)
        jid = "job:" + digest({"idea": idea, "t": time.time()})[:16]
        self.conn.execute("INSERT INTO queue VALUES(?,?,?,?,?)", (jid, idea, bid, "queued", ""))
        self.receipt("job_queued", jid, {"idea": idea, "builder": bid})
        self.conn.commit()
        return {"job": jid, "idea": idea, "builder": bid, "status": "queued"}

    def run_job(self, jid):
        q = self.conn.execute("SELECT * FROM queue WHERE id=?", (jid,)).fetchone()
        if not q:
            return {"ok": False, "reason": "missing_job"}
        idea = q["idea"]; builder = q["builder"]
        typ = "Application" if "dashboard" in builder else "Workflow" if "workflow" in builder else "Report" if "report" in builder else "Service" if "api" in builder else "Tool"
        payload = {
            "version": "0.4.0",
            "name": idea.title().replace(" ", "_")[:48],
            "idea": idea,
            "type": typ,
            "builder": builder,
            "requirements": ["intent captured", "builder selected", "manifest produced", "verification included"],
            "architecture": ["engine", "storage", "interface", "tests", "release"],
            "tests": ["builder valid", "payload valid", "release hash valid"],
            "created": time.time()
        }
        h = digest(payload); aid = "artifact:" + h[:16]; payload["artifact_id"] = aid
        path = self.out / f"{aid.replace(':','_')}.json"
        path.write_text(json.dumps(payload, indent=2, default=str))
        self.conn.execute("INSERT OR REPLACE INTO artifacts VALUES(?,?,?,?,?,?,?,?)", (aid, payload["name"], typ, builder, "built", h, str(path), json.dumps(payload)))
        self.conn.execute("UPDATE queue SET status='testing', artifact=? WHERE id=?", (aid, jid))
        self.receipt("artifact_built", aid, {"job": jid, "hash": h})
        verified = self.verify_artifact(aid)
        if verified["status"] != "pass":
            self.conn.execute("UPDATE queue SET status='failed' WHERE id=?", (jid,))
            self.conn.commit()
            return {"ok": False, "job": jid, "artifact": aid, "status": "failed"}
        rel = self.release(aid)
        self.conn.execute("UPDATE queue SET status='released' WHERE id=?", (jid,))
        self.conn.commit()
        return {"ok": True, "job": jid, "artifact": aid, "status": "released", "release": rel}

    def verify_artifact(self, aid):
        r = self.conn.execute("SELECT * FROM artifacts WHERE id=?", (aid,)).fetchone()
        payload = json.loads(r["payload"])
        checks = {
            "builder_present": bool(payload.get("builder")),
            "requirements_present": bool(payload.get("requirements")),
            "architecture_present": bool(payload.get("architecture")),
            "tests_present": bool(payload.get("tests"))
        }
        for k, ok in checks.items():
            self.conn.execute("INSERT INTO checks(subject,name,status) VALUES(?,?,?)", (aid, k, "pass" if ok else "fail"))
        status = "pass" if all(checks.values()) else "fail"
        self.conn.execute("UPDATE artifacts SET status=? WHERE id=?", ("verified" if status == "pass" else "failed", aid))
        self.receipt("artifact_verified", aid, {"status": status})
        self.conn.commit()
        return {"artifact": aid, "status": status}

    def release(self, aid):
        r = self.conn.execute("SELECT * FROM artifacts WHERE id=?", (aid,)).fetchone()
        payload = {"artifact": aid, "version": "0.1.0", "artifact_hash": r["h"], "created": time.time()}
        h = digest(payload); rid = "release:" + h[:16]
        path = self.releases / f"{rid.replace(':','_')}.json"
        path.write_text(json.dumps(payload, indent=2))
        self.conn.execute("INSERT OR REPLACE INTO releases VALUES(?,?,?,?,?)", (rid, aid, "0.1.0", h, str(path)))
        self.conn.execute("UPDATE artifacts SET status='released' WHERE id=?", (aid,))
        self.receipt("artifact_released", rid, {"artifact": aid, "hash": h})
        self.conn.commit()
        return {"release": rid, "artifact": aid, "hash": h, "path": str(path)}

    def run_all(self):
        return [self.run_job(r["id"]) for r in self.conn.execute("SELECT id FROM queue WHERE status='queued' ORDER BY id")]

    def dashboard(self):
        return {
            "version": "0.4.0",
            "builders": [dict(r) for r in self.conn.execute("SELECT * FROM builders ORDER BY id")],
            "queue": [dict(r) for r in self.conn.execute("SELECT * FROM queue ORDER BY id")],
            "artifacts": [dict(r) for r in self.conn.execute("SELECT id,name,type,builder,status,h,path FROM artifacts ORDER BY id")],
            "releases": [dict(r) for r in self.conn.execute("SELECT * FROM releases ORDER BY id")],
            "ledger": self.verify_ledger()
        }

    def stats(self):
        return {
            "builders": self.conn.execute("SELECT COUNT(*) n FROM builders").fetchone()["n"],
            "jobs": self.conn.execute("SELECT COUNT(*) n FROM queue").fetchone()["n"],
            "released_jobs": self.conn.execute("SELECT COUNT(*) n FROM queue WHERE status='released'").fetchone()["n"],
            "artifacts": self.conn.execute("SELECT COUNT(*) n FROM artifacts").fetchone()["n"],
            "releases": self.conn.execute("SELECT COUNT(*) n FROM releases").fetchone()["n"],
            "ledger": self.verify_ledger(),
            "db_integrity": self.conn.execute("PRAGMA integrity_check").fetchone()[0]
        }

    def export(self, out):
        out = Path(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("assembly_dashboard.json", json.dumps(self.dashboard(), indent=2, default=str))
            z.writestr("stats.json", json.dumps(self.stats(), indent=2, default=str))
            for t in ["builders", "queue", "artifacts", "releases", "checks", "ledger"]:
                z.writestr(f"{t}.json", json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")], indent=2, default=str))
            for p in sorted(self.out.glob("*.json")):
                z.write(p, arcname=f"artifacts/{p.name}")
            for p in sorted(self.releases.glob("*.json")):
                z.write(p, arcname=f"releases/{p.name}")
        return {"bundle": str(out), "exists": out.exists()}

def seed_demo(td):
    a = AssemblyLine(Path(td)/"assembly.db", Path(td)/"artifacts", Path(td)/"releases")
    jobs = [
        a.enqueue("create mesh monitoring dashboard"),
        a.enqueue("create fraud audit report packet"),
        a.enqueue("create renewal workflow process")
    ]
    results = a.run_all()
    bundle = a.export(Path(td)/"assembly_bundle.zip")
    return {"jobs": jobs, "results": results, "stats": a.stats(), "bundle": bundle}
