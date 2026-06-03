
import json,hashlib,sqlite3,zipfile
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
class Harness:
    def __init__(self,db="integration.db",out="generated_app"):
        self.out=Path(out); self.out.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(Path(db)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript('''CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,idea TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY,project TEXT,kind TEXT,path TEXT,h TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);''')
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
    def write(self,pid,kind,rel,txt):
        p=self.out/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(txt)
        h=hashlib.sha256(txt.encode()).hexdigest(); fid="file:"+digest({"pid":pid,"rel":rel,"h":h})[:16]
        self.conn.execute("INSERT OR REPLACE INTO files VALUES(?,?,?,?,?)",(fid,pid,kind,str(p),h))
        self.receipt("file",fid,{"kind":kind,"path":str(p)})
        return {"kind":kind,"path":str(p),"hash":h}
    def build(self,idea):
        pid="project:"+digest({"idea":idea,"v":"0.7.0"})[:16]
        self.conn.execute("INSERT OR REPLACE INTO projects VALUES(?,?,?)",(pid,idea,"generated"))
        files=[]
        files.append(self.write(pid,"schema","database/schema.sql","CREATE TABLE artifacts(id TEXT PRIMARY KEY,name TEXT,status TEXT);\\n"))
        files.append(self.write(pid,"workflow","workflow.py",'def run_workflow(): return {"state":"approved"}\\n'))
        files.append(self.write(pid,"report","report.py",'def generate_report(): return {"status":"ready"}\\n'))
        files.append(self.write(pid,"security","security.py",'def verify(x): return bool(x.get("id"))\\n'))
        app = '''import json,sqlite3
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
ROOT=Path(__file__).parent
DB=ROOT/"app.db"
def init_db():
    conn=sqlite3.connect(DB)
    conn.executescript((ROOT/"database/schema.sql").read_text())
    conn.execute("INSERT OR IGNORE INTO artifacts VALUES(?,?,?)",("a1","demo","active"))
    conn.commit()
    conn.close()
class H(BaseHTTPRequestHandler):
    def j(self,o,c=200):
        b=json.dumps(o).encode()
        self.send_response(c)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def do_GET(self):
        if self.path in ("/","/api/status"): return self.j({"status":"online","version":"0.7.0"})
        if self.path=="/api/workflow": return self.j({"state":"approved"})
        if self.path=="/api/report": return self.j({"status":"ready"})
        if self.path=="/api/security": return self.j({"security":"pass"})
        if self.path=="/dashboard":
            b=(ROOT/"dashboard/index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type","text/html")
            self.send_header("Content-Length",str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        self.j({"error":"not_found"},404)
    def log_message(self,*a): pass
def main():
    init_db()
    ThreadingHTTPServer(("127.0.0.1",8090),H).serve_forever()
if __name__=="__main__": main()
'''
        files.append(self.write(pid,"app","app.py",app))
        files.append(self.write(pid,"run","run_app.py","from app import main\\nmain()\\n"))
        files.append(self.write(pid,"dashboard","dashboard/index.html",f"<html><body><h1>Generated Integrated App</h1><p>{idea}</p></body></html>"))
        test = '''from pathlib import Path
import sqlite3,runpy
R=Path(__file__).parent
for f in ["app.py","run_app.py","dashboard/index.html","database/schema.sql","workflow.py","report.py","security.py"]:
    assert (R/f).exists()
conn=sqlite3.connect(":memory:")
conn.executescript((R/"database/schema.sql").read_text())
wf=runpy.run_path(str(R/"workflow.py"))
rp=runpy.run_path(str(R/"report.py"))
sc=runpy.run_path(str(R/"security.py"))
assert wf["run_workflow"]()["state"]=="approved"
assert rp["generate_report"]()["status"]=="ready"
assert sc["verify"]({"id":"x"})
print("GENERATED INTEGRATION SELFTEST PASS")
'''
        files.append(self.write(pid,"selftest","selftest_generated.py",test))
        files.append(self.write(pid,"manifest","manifest.json",json.dumps({"project":pid,"idea":idea,"files":files},indent=2)))
        self.receipt("project",pid,{"files":len(files)})
        self.conn.commit()
        return {"project":pid,"files":files}
    def verify(self,pid):
        kinds={r["kind"] for r in self.conn.execute("SELECT kind FROM files WHERE project=?",(pid,))}
        req={"schema","workflow","report","security","app","run","dashboard","selftest","manifest"}
        ok=req.issubset(kinds) and self.verify_ledger()["ok"]
        self.conn.execute("UPDATE projects SET status=? WHERE id=?",("verified" if ok else "failed",pid))
        self.conn.commit()
        self.receipt("verify",pid,{"ok":ok})
        return {"project":pid,"status":"verified" if ok else "failed","missing":sorted(req-kinds)}
    def stats(self):
        return {"projects":self.conn.execute("SELECT COUNT(*) n FROM projects").fetchone()["n"],"files":self.conn.execute("SELECT COUNT(*) n FROM files").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def export(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            z.writestr("stats.json",json.dumps(self.stats(),indent=2))
            for t in ["projects","files","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2))
            for p in sorted(self.out.rglob("*")):
                if p.is_file(): z.write(p,arcname=f"generated_app/{p.relative_to(self.out)}")
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(td):
    h=Harness(Path(td)/"integration.db",Path(td)/"generated_app")
    p=h.build("integrated dashboard api database workflow report security app")
    v=h.verify(p["project"])
    b=h.export(Path(td)/"bundle.zip")
    return {"project":p,"verify":v,"stats":h.stats(),"bundle":b}
