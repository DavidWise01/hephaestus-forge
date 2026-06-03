from pathlib import Path
import tempfile,runpy
from hephaestus.autonomous import seed_demo
with tempfile.TemporaryDirectory() as td:
    r=seed_demo(td)
    assert r["build"]["status"]=="verified"
    assert r["stats"]["plugins"]>=6
    assert r["stats"]["runs"]==1
    assert r["stats"]["steps"]>=6
    assert r["stats"]["files"]>=8
    assert r["stats"]["ledger"]["ok"] is True
    assert r["stats"]["db_integrity"]=="ok"
    assert r["bundle"]["exists"] is True
    runpy.run_path(str(Path(td)/"generated_system/selftest_generated.py"),run_name="__main__")
print("SELFTEST PASS")
