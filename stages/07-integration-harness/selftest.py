from pathlib import Path
import tempfile,runpy
from hephaestus.integration import seed_demo,Harness
with tempfile.TemporaryDirectory() as td:
    r=seed_demo(td)
    assert r["verify"]["status"]=="verified"
    assert r["stats"]["projects"]==1
    assert r["stats"]["files"]>=9
    assert r["stats"]["ledger"]["ok"] is True
    assert r["stats"]["db_integrity"]=="ok"
    assert r["bundle"]["exists"] is True
    h=Harness(Path(td)/"i2.db",Path(td)/"app2")
    p=h.build("test app")
    h.verify(p["project"])
    runpy.run_path(str(Path(td)/"app2/selftest_generated.py"),run_name="__main__")
print("SELFTEST PASS")
