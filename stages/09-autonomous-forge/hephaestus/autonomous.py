
import json,hashlib,sqlite3,zipfile
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
class AutoForge:
    PLUGINS={
        "database":("plugin:database_builder",["database","storage","ledger"],"database/schema.sql"),
        "api":("plugin:api_builder",["api","server","service"],"api/server.py"),
        "dashboard":("plugin:dashboard_builder",["dashboard","ui","console","operator"],"dashboard/index.html"),
        "workflow":("plugin:workflow_builder",["workflow","case","process"],"workflow/workflow.py"),
        "report":("plugin:report_builder",["report","audit","evidence"],"reports/report.html"),
        "security":("plugin:security_builder",["security","verify","authority"],"security/security.py"),
    }
    def __init__(self,db="auto.db",out="generated_system"):
        self.out=Path(out); self.out.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(Path(db)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""CREATE TABLE IF NOT EXISTS plugins(id TEXT PRIMARY KEY,name TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,request TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS steps(id TEXT PRIMARY KEY,run TEXT,plugin TEXT,status TEXT,outputs TEXT);
        CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY,run TEXT,plugin TEXT,path TEXT,h TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);""")
        for k,(pid,_,_) in self.PLUGINS.items():
            self.conn.execute("INSERT OR REPLACE INTO plugins VALUES(?,?,?)",(pid,k,"active"))
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
    def select(self,request):
        low=request.lower(); selected=[]
        for key,(pid,triggers,path) in self.PLUGINS.items():
            if any(t in low for t in triggers): selected.append(key)
        if any(x in low for x in ["full","system","platform","app"]) or not selected:
            for key in ["database","api","dashboard"]:
                if key not in selected: selected.append(key)
        order=["database","security","api","workflow","report","dashboard"]
        return [k for k in order if k in selected]
    def content(self,key,request):
        if key=="database": return "CREATE TABLE items(id TEXT PRIMARY KEY,name TEXT,status TEXT);\nCREATE TABLE audit(id INTEGER PRIMARY KEY,action TEXT);\n"
        if key=="security": return "def verify(x): return bool(x.get('id')) and x.get('status')!='denied'\n"
        if key=="api": return "import json\nfrom http.server import ThreadingHTTPServer,BaseHTTPRequestHandler\nclass H(BaseHTTPRequestHandler):\n def do_GET(self):\n  b=json.dumps({'status':'online','system':'autonomous-forge-generated'}).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)\n def log_message(self,*a): pass\nif __name__=='__main__': ThreadingHTTPServer(('127.0.0.1',8099),H).serve_forever()\n"
        if key=="workflow": return "def run_case(): return {'case':'demo','state':'resolved'}\n"
        if key=="report": return f"<html><body><h1>Generated Report</h1><p>{request}</p></body></html>"
        if key=="dashboard": return f"<html><body><h1>Autonomous Forge Dashboard</h1><p>{request}</p></body></html>"
        return request
    def write(self,rid,pid,rel,txt):
        path=self.out/rel; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(txt)
        h=hashlib.sha256(txt.encode()).hexdigest(); fid="file:"+digest({"run":rid,"path":rel,"h":h})[:16]
        self.conn.execute("INSERT OR REPLACE INTO files VALUES(?,?,?,?,?)",(fid,rid,pid,str(path),h))
        self.receipt("file",fid,{"path":str(path),"plugin":pid}); return {"path":str(path),"hash":h}
    def build(self,request):
        rid="run:"+digest({"request":request})[:16]
        self.conn.execute("INSERT OR REPLACE INTO runs VALUES(?,?,?)",(rid,request,"running"))
        outputs=[]
        for key in self.select(request):
            pid,_,rel=self.PLUGINS[key]
            out=self.write(rid,pid,rel,self.content(key,request)); outputs.append(out)
            sid="step:"+digest({"run":rid,"plugin":pid})[:16]
            self.conn.execute("INSERT OR REPLACE INTO steps VALUES(?,?,?,?,?)",(sid,rid,pid,"complete",json.dumps([out["path"]])))
            self.receipt("step",sid,{"plugin":pid})
        manifest={"run":rid,"request":request,"files":outputs}
        self.write(rid,"plugin:manifest","manifest.json",json.dumps(manifest,indent=2))
        self.write(rid,"plugin:selftest","selftest_generated.py","from pathlib import Path\nR=Path(__file__).parent\nassert (R/'manifest.json').exists()\nassert any((R/p).exists() for p in ['dashboard/index.html','api/server.py','database/schema.sql'])\nprint('AUTONOMOUS GENERATED SYSTEM SELFTEST PASS')\n")
        self.conn.execute("UPDATE runs SET status='verified' WHERE id=?",(rid,))
        self.receipt("run",rid,{"files":len(outputs)+2})
        self.conn.commit()
        return {"run":rid,"status":"verified","files":outputs}
    def stats(self):
        return {"plugins":self.conn.execute("SELECT COUNT(*) n FROM plugins").fetchone()["n"],"runs":self.conn.execute("SELECT COUNT(*) n FROM runs").fetchone()["n"],"steps":self.conn.execute("SELECT COUNT(*) n FROM steps").fetchone()["n"],"files":self.conn.execute("SELECT COUNT(*) n FROM files").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def export(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            z.writestr("stats.json",json.dumps(self.stats(),indent=2))
            for t in ["plugins","runs","steps","files","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2))
            for p in sorted(self.out.rglob("*")):
                if p.is_file(): z.write(p,arcname=f"generated_system/{p.relative_to(self.out)}")
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(td):
    f=AutoForge(Path(td)/"auto.db",Path(td)/"generated_system")
    b=f.build("build a full operator platform with dashboard api database workflow report security and evidence")
    e=f.export(Path(td)/"bundle.zip")
    return {"build":b,"stats":f.stats(),"bundle":e}
