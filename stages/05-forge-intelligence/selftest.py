from pathlib import Path
import tempfile
from hephaestus.intelligence import seed_demo
with tempfile.TemporaryDirectory() as td:
    r=seed_demo(td); stats=r["build"]["stats"]
    assert stats["plans"]==1
    assert stats["tasks"]>=5
    assert stats["released_tasks"]==stats["tasks"]
    assert stats["artifacts"]==stats["tasks"]
    assert stats["releases"]==stats["tasks"]
    assert stats["ledger"]["ok"] is True
    assert stats["db_integrity"]=="ok"
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
