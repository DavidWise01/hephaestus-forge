
import json,hashlib,sqlite3,zipfile
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
class Graph:
    def __init__(self,db="graph.db",out="artifacts"):
        self.out=Path(out); self.out.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(Path(db)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY,name TEXT,type TEXT,class TEXT,status TEXT,h TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS edges(id TEXT PRIMARY KEY,src TEXT,dst TEXT,relation TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS checks(id INTEGER PRIMARY KEY,subject TEXT,name TEXT,status TEXT);
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
    def classify(self,idea):
        low=idea.lower()
        typ="Shield" if any(x in low for x in ["protect","shield","audit"]) else "Weapon" if any(x in low for x in ["detect","fraud","scan"]) else "Machine" if any(x in low for x in ["engine","machine","compiler"]) else "Tool"
        cls="V" if "cluster" in low else "IV" if any(x in low for x in ["mesh","federation","distributed"]) else "III" if "dashboard" in low else "I"
        return typ,cls
    def compile(self,idea,name=None):
        typ,cls=self.classify(idea)
        p={"version":"0.1.0","name":name or idea.title().replace(" ","_")[:48],"idea":idea,"type":typ,"class":cls,"sections":["blueprint","materials","assembly","verification","deployment"]}
        h=digest(p); aid="artifact:"+h[:16]; p["artifact_id"]=aid
        (self.out/(aid.replace(":","_")+".json")).write_text(json.dumps(p,indent=2))
        self.conn.execute("INSERT OR REPLACE INTO artifacts VALUES(?,?,?,?,?,?,?)",(aid,p["name"],typ,cls,"compiled",h,json.dumps(p)))
        self.receipt("compiled",aid,{"hash":h}); self.conn.commit()
        return {"artifact":aid,"name":p["name"],"type":typ,"class":cls,"hash":h}
    def link(self,src,dst,relation="depends_on"):
        eid="edge:"+digest({"src":src,"dst":dst,"relation":relation})[:16]
        self.conn.execute("INSERT OR REPLACE INTO edges VALUES(?,?,?,?,?)",(eid,src,dst,relation,"active"))
        self.receipt("edge",eid,{"src":src,"dst":dst,"relation":relation}); self.conn.commit()
        return {"edge":eid,"src":src,"dst":dst,"relation":relation}
    def graph(self):
        return {"version":"0.1.0","nodes":[dict(r) for r in self.conn.execute("SELECT id,name,type,class,status,h FROM artifacts ORDER BY id")],"edges":[dict(r) for r in self.conn.execute("SELECT * FROM edges ORDER BY id")],"ledger":self.verify_ledger()}
    def verify_graph(self):
        nodes={r["id"] for r in self.conn.execute("SELECT id FROM artifacts")}
        ok=all(r["src"] in nodes and r["dst"] in nodes for r in self.conn.execute("SELECT src,dst FROM edges"))
        self.conn.execute("INSERT INTO checks(subject,name,status) VALUES(?,?,?)",("graph","integrity","pass" if ok else "fail"))
        self.receipt("verify","graph",{"ok":ok}); self.conn.commit()
        return {"status":"pass" if ok else "fail"}
    def impact(self,aid):
        edges=[dict(r) for r in self.conn.execute("SELECT * FROM edges")]
        down=[]; seen=set()
        def walk(x):
            for e in edges:
                if e["src"]==x and e["id"] not in seen:
                    seen.add(e["id"]); down.append(e); walk(e["dst"])
        walk(aid)
        return {"artifact":aid,"downstream_count":len(down),"downstream":down}
    def export(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            z.writestr("artifact_graph.json",json.dumps(self.graph(),indent=2))
            for t in ["artifacts","edges","checks","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2))
            for p in sorted(self.out.glob("*.json")): z.write(p,arcname="artifacts/"+p.name)
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(td):
    g=Graph(Path(td)/"graph.db",Path(td)/"artifacts")
    a=g.compile("artifact compiler that turns ideas into packages","Artifact_Compiler")
    b=g.compile("detect fraud across a credential federation","Fraud_Scanner")
    c=g.compile("protect authority delegation from scope overreach","Authority_Shield")
    d=g.compile("dashboard app for live mesh health","Mesh_Dashboard")
    e=g.compile("distributed recovery cluster for failed offices","Recovery_Cluster")
    g.link(a["artifact"],b["artifact"],"manufactures"); g.link(a["artifact"],c["artifact"],"manufactures"); g.link(b["artifact"],d["artifact"],"feeds"); g.link(e["artifact"],d["artifact"],"feeds"); g.link(c["artifact"],e["artifact"],"protects")
    return {"artifacts":[a,b,c,d,e],"verify":g.verify_graph(),"impact":g.impact(a["artifact"]),"graph":g.graph(),"bundle":g.export(Path(td)/"bundle.zip")}
