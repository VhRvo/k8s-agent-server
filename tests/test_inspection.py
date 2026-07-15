import os
import tempfile

from k8s_agent.models.inspection import InspectionStore


def test_insert_and_get():
    with tempfile.TemporaryDirectory() as d:
        store = InspectionStore(db_path=os.path.join(d, "test.db"), max_records=10)
        store.init()
        rid = store.insert("2026-01-01 00:00:00", "manual")
        r = store.get(rid)
        assert r["status"] == "running"
        assert r["trigger"] == "manual"


def test_update():
    with tempfile.TemporaryDirectory() as d:
        store = InspectionStore(db_path=os.path.join(d, "test.db"), max_records=10)
        store.init()
        rid = store.insert("2026-01-01 00:00:00", "scheduled")
        store.update(rid, status="completed", response="all good")
        r = store.get(rid)
        assert r["status"] == "completed"
        assert r["response"] == "all good"


def test_list_order_and_limit():
    with tempfile.TemporaryDirectory() as d:
        store = InspectionStore(db_path=os.path.join(d, "test.db"), max_records=3)
        store.init()
        for i in range(5):
            store.insert(f"2026-01-0{i+1} 00:00:00", "scheduled")
        rows = store.list()
        assert len(rows) == 3


def test_inspector_user_id_isolated():
    from k8s_agent.services.inspector import INSPECTOR_USER_ID
    assert INSPECTOR_USER_ID == "inspector"
    assert INSPECTOR_USER_ID != "default"
