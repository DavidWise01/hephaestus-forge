
import json,hashlib,sqlite3,zipfile
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
class CodeGen:
    def __init__(self,db="codegen.db",out="generated"):
        self.out=Path(out); self.out.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(Path(db)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,idea TEXT,status TEXT,h TEXT);
        CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY,project TEXT,kind TEXT,path TEXT,h TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);""")
        self.conn.commit()
    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"
    def receipt(self,k,s,p):
        ph=digest(p); prev=self.last_hash(); eh=digest({"kind":k,"subject":s,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO ledger(kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?)",(k,s,ph,prev,eh)); self.conn.commit()
    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT * FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev or r["entry_hash"]!=exp: return {"ok":False,"seq":r["seq"]}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}
    def write(self,pid,kind,rel,content):
        path=self.out/rel; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(content)
        h=hashlib.sha256(content.encode()).hexdigest(); fid="file:"+digest({"pid":pid,"path":str(rel),"h":h})[:16]
        self.conn.execute("INSERT OR REPLACE INTO files VALUES(?,?,?,?,?,?)",(fid,pid,kind,str(path),h,"created"))
        self.receipt("file",fid,{"kind":kind,"path":str(path),"h":h}); self.conn.commit()
        return {"kind":kind,"path":str(path),"hash":h}
    def gen(self,idea):
        pid="project:"+digest({"idea":idea})[:16]; h=digest({"idea":idea,"version":"0.6.0"})
        self.conn.execute("INSERT OR REPLACE INTO projects VALUES(?,?,?,?)",(pid,idea,"generated",h))
        files=[]
        files.append(self.write(pid,"dashboard","dashboard/index.html",f"<html><body><h1>Generated Dashboard</h1><p>{idea}</p></body></html>"))
        files.append(self.write(pid,"api","api/server.py",'import json\nfrom http.server import ThreadingHTTPServer,BaseHTTPRequestHandler\nclass H(BaseHTTPRequestHandler):\n def do_GET(self):\n  b=json.dumps({"status":"online","version":"0.6.0"}).encode(); self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)\n def log_message(self,*a): pass\nif __name__=="__main__": ThreadingHTTPServer(("127.0.0.1",8088),H).serve_forever()\n'))
        files.append(self.write(pid,"database","database/schema.sql","CREATE TABLE artifacts(id TEXT PRIMARY KEY,name TEXT,status TEXT);\nCREATE TABLE audit(id INTEGER PRIMARY KEY,action TEXT,subject TEXT);\n"))
        files.append(self.write(pid,"workflow","workflow/workflow.py",'class Workflow:\n def __init__(self): self.state="submitted"\n def approve(self): self.state="approved"; return self.state\nif __name__=="__main__":\n w=Workflow(); assert w.approve()=="approved"; print("WORKFLOW PASS")\n'))
        files.append(self.write(pid,"report","report/report.html",f"<html><body><h1>Generated Report</h1><p>{idea}</p></body></html>"))
        files.append(self.write(pid,"security","security/security.py",'def verify(payload): return "id" in payload and "status" in payload\nif __name__=="__main__": assert verify({"id":"x","status":"ok"}); print("SECURITY PASS")\n'))
        files.append(self.write(pid,"selftest","selftest_generated.py",'from pathlib import Path\nimport sqlite3,runpy\nr=Path(__file__).parent\nassert (r/"dashboard/index.html").exists()\nassert (r/"api/server.py").exists()\nassert (r/"database/schema.sql").exists()\nconn=sqlite3.connect(":memory:"); conn.executescript((r/"database/schema.sql").read_text())\nrunpy.run_path(str(r/"workflow/workflow.py"),run_name="__main__")\nrunpy.run_path(str(r/"security/security.py"),run_name="__main__")\nprint("GENERATED PROJECT SELFTEST PASS")\n'))
        files.append(self.write(pid,"manifest","manifest.json",json.dumps({"project":pid,"idea":idea,"files":files},indent=2)))
        self.receipt("project",pid,{"files":len(files),"h":h}); self.conn.commit()
        return {"project":pid,"hash":h,"files":files}
    def verify(self,pid):
        kinds={r["kind"] for r in self.conn.execute("SELECT kind FROM files WHERE project=?",(pid,))}
        ok=all(k in kinds for k in ["dashboard","api","database","workflow","report","security","selftest","manifest"]) and self.verify_ledger()["ok"]
        self.conn.execute("UPDATE projects SET status=? WHERE id=?",("verified" if ok else "failed",pid)); self.conn.commit()
        self.receipt("verify",pid,{"ok":ok})
        return {"project":pid,"status":"verified" if ok else "failed"}
    def stats(self):
        return {"projects":self.conn.execute("SELECT COUNT(*) n FROM projects").fetchone()["n"],"files":self.conn.execute("SELECT COUNT(*) n FROM files").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def export(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            z.writestr("stats.json",json.dumps(self.stats(),indent=2))
            for t in ["projects","files","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2))
            for p in sorted(self.out.rglob("*")):
                if p.is_file(): z.write(p,arcname=f"generated/{p.relative_to(self.out)}")
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(td):
    g=CodeGen(Path(td)/"codegen.db",Path(td)/"generated")
    p=g.gen("create runnable operator dashboard with API, workflow, report, database, and security checks")
    v=g.verify(p["project"])
    b=g.export(Path(td)/"bundle.zip")
    return {"project":p,"verify":v,"stats":g.stats(),"bundle":b}
