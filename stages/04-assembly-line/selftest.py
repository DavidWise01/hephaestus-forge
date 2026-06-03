
from pathlib import Path
import tempfile
from hephaestus.assembly import seed_demo
with tempfile.TemporaryDirectory() as td:
    r=seed_demo(td)
    assert len(r["jobs"]) == 3
    assert len(r["results"]) == 3
    assert all(x["ok"] for x in r["results"])
    assert r["stats"]["builders"] >= 5
    assert r["stats"]["released_jobs"] == 3
    assert r["stats"]["artifacts"] == 3
    assert r["stats"]["releases"] == 3
    assert r["stats"]["ledger"]["ok"] is True
    assert r["stats"]["db_integrity"] == "ok"
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
