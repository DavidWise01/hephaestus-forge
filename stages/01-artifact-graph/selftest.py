from pathlib import Path
import tempfile
from hephaestus.graph import seed_demo
with tempfile.TemporaryDirectory() as td:
    r=seed_demo(td)
    assert len(r["artifacts"])==5
    assert len(r["graph"]["edges"])==5
    assert r["verify"]["status"]=="pass"
    assert r["graph"]["ledger"]["ok"] is True
    assert r["impact"]["downstream_count"]>=4
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
