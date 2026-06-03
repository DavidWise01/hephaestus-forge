
import json, hashlib, time, sqlite3, zipfile
from pathlib import Path

def digest(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()

class Forge:
    CLASSES={"I":"Script","II":"Service","III":"Application","IV":"Federation","V":"Infrastructure","VI":"Civilization Scale"}
    TYPES=["Tool","Weapon","Shield","Machine","Construct"]

    def __init__(self, db="hephaestus.db", out="artifacts"):
        self.out=Path(out); self.out.mkdir(parents=True, exist_ok=True)
        self.conn=sqlite3.connect(Path(db)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY,name TEXT,type TEXT,class TEXT,status TEXT,h TEXT,parent TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS lineage(id INTEGER PRIMARY KEY,artifact TEXT,parent TEXT,relation TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS checks(id INTEGER PRIMARY KEY,artifact TEXT,name TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """)
        self.conn.commit()

    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"

    def receipt(self,k,s,p):
        ph=digest(p); prev=self.last_hash(); eh=digest({"kind":k,"subject":s,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO ledger(kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?)",(k,s,ph,prev,eh))
        self.conn.commit()

    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT * FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"reason":"prev_hash_mismatch","seq":r["seq"]}
            if r["entry_hash"]!=exp: return {"ok":False,"reason":"entry_hash_mismatch","seq":r["seq"]}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}

    def classify(self, idea):
        low=idea.lower()
        typ="Shield" if any(x in low for x in ["protect","shield","audit","verify"]) else "Weapon" if any(x in low for x in ["detect","fraud","hunt","scan"]) else "Machine" if any(x in low for x in ["engine","machine","construct"]) else "Tool"
        cls="VI" if any(x in low for x in ["civilization","government","city"]) else "V" if any(x in low for x in ["infrastructure","cluster","deployment"]) else "IV" if any(x in low for x in ["mesh","federation","distributed"]) else "III" if any(x in low for x in ["dashboard","app","portal"]) else "II" if any(x in low for x in ["api","service","server"]) else "I"
        return typ,cls

    def blueprint(self, idea, name=None, parent=""):
        typ,cls=self.classify(idea)
        return {
            "name": name or idea.title().replace(" ","_")[:48],
            "idea": idea,
            "type": typ,
            "class": cls,
            "class_name": self.CLASSES[cls],
            "blueprint": {"requirements":["capture intent","define inputs/outputs","audit trail","selftest","package"],"architecture":["engine","storage","verification","export"],"database":["artifacts","lineage","checks","ledger"],"api":["compile","verify","export","dashboard"]},
            "materials": {"language":"python","storage":"sqlite","exports":["json","zip"],"dashboard":"static html"},
            "assembly": ["generate blueprint","write manifest","verify","record lineage","export"],
            "verification": ["blueprint exists","sections present","ledger verifies","bundle exports"],
            "deployment": {"mode":"local","run":"python selftest.py"},
            "parent": parent,
            "created": time.time()
        }

    def compile(self, idea, name=None, parent=""):
        bp=self.blueprint(idea,name,parent); h=digest(bp); aid="artifact:"+h[:16]; bp["artifact_id"]=aid
        path=self.out/(aid.replace(":","_")+".json"); path.write_text(json.dumps(bp,indent=2))
        self.conn.execute("INSERT OR REPLACE INTO artifacts VALUES(?,?,?,?,?,?,?,?)",(aid,bp["name"],bp["type"],bp["class"],"compiled",h,parent,json.dumps(bp)))
        self.conn.execute("INSERT INTO lineage(artifact,parent,relation,details) VALUES(?,?,?,?)",(aid,parent,"compiled_from_idea",json.dumps({"idea":idea})))
        self.receipt("compiled",aid,{"hash":h,"type":bp["type"],"class":bp["class"]})
        self.conn.commit(); self.verify(aid)
        return {"artifact":aid,"name":bp["name"],"type":bp["type"],"class":bp["class"],"hash":h,"path":str(path)}

    def verify(self, aid):
        r=self.conn.execute("SELECT payload FROM artifacts WHERE id=?",(aid,)).fetchone()
        if not r: return {"ok":False}
        p=json.loads(r["payload"])
        checks={"blueprint":"blueprint" in p,"materials":"materials" in p,"assembly":"assembly" in p,"verification":"verification" in p,"deployment":"deployment" in p,"class_valid":p.get("class") in self.CLASSES}
        for k,v in checks.items():
            self.conn.execute("INSERT INTO checks(artifact,name,status) VALUES(?,?,?)",(aid,k,"pass" if v else "fail"))
        status="verified" if all(checks.values()) else "failed"
        self.conn.execute("UPDATE artifacts SET status=? WHERE id=?",(status,aid))
        self.receipt("verified",aid,{"status":status,"checks":checks})
        self.conn.commit()
        return {"artifact":aid,"status":status,"checks":checks}

    def dashboard(self):
        arts=[dict(r) for r in self.conn.execute("SELECT id,name,type,class,status,h,parent FROM artifacts ORDER BY id")]
        return {"forge":"hephaestus:root","version":"0.0.0","artifact_count":len(arts),"artifacts":arts,"ledger":self.verify_ledger()}

    def export(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            z.writestr("forge_dashboard.json",json.dumps(self.dashboard(),indent=2))
            for t in ["artifacts","lineage","checks","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2))
            for p in sorted(self.out.glob("*.json")):
                z.write(p,arcname="artifacts/"+p.name)
        return {"bundle":str(out),"exists":out.exists()}

def seed_demo(td):
    f=Forge(Path(td)/"hephaestus.db",Path(td)/"artifacts")
    arts=[
        f.compile("detect fraud across a credential federation","Fraud_Scanner"),
        f.compile("protect authority delegation from scope overreach","Authority_Shield"),
        f.compile("dashboard app for live mesh health","Mesh_Dashboard"),
        f.compile("distributed recovery cluster for failed offices","Recovery_Cluster")
    ]
    return {"artifacts":arts,"dashboard":f.dashboard(),"bundle":f.export(Path(td)/"bundle.zip")}
