from pathlib import Path
import tempfile,runpy
from hephaestus.codegen import CodeGen,seed_demo
with tempfile.TemporaryDirectory() as td:
    r=seed_demo(td)
    assert r["verify"]["status"]=="verified"
    assert r["stats"]["projects"]==1
    assert r["stats"]["files"]>=8
    assert r["stats"]["ledger"]["ok"] is True
    assert r["stats"]["db_integrity"]=="ok"
    assert r["bundle"]["exists"] is True
    g=CodeGen(Path(td)/"codegen2.db",Path(td)/"generated2")
    p=g.gen("test generated runnable files")
    g.verify(p["project"])
    runpy.run_path(str(Path(td)/"generated2/selftest_generated.py"),run_name="__main__")
print("SELFTEST PASS")
