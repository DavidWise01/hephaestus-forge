
from pathlib import Path
import tempfile
from hephaestus.forge import seed_demo
with tempfile.TemporaryDirectory() as td:
    r=seed_demo(td)
    assert len(r["artifacts"])==4
    assert r["dashboard"]["artifact_count"]==4
    assert r["dashboard"]["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
