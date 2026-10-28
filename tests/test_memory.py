"""
tests/test_memory.py - Persistent SQLite Spatial Memory Unit Tests
"""

import tempfile
from pathlib import Path
import memory


def test_memory_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test_echomap.db"
        memory.initialise(test_db)

        # 1. Save scan
        test_objects = [
            {"name": "keys", "x": 0.35, "y": 0.45, "confidence": 0.95, "region_desc": "centre of the desk"},
            {"name": "phone", "x": 0.30, "y": 0.42, "confidence": 0.98, "region_desc": "centre of the desk"},
        ]
        scan_id = memory.save_scan(test_objects, scene="test_desk", summary="Test scan 1", db_path=test_db)
        assert scan_id is not None

        # 2. Retrieve latest
        latest = memory.latest_scan(test_db)
        assert latest is not None
        scan_meta, objs = latest
        assert scan_meta["id"] == scan_id
        assert len(objs) == 2
        assert objs[0]["name"] == "keys"

        # 3. Save correction
        corr_id = memory.save_correction("keys", "beside", "phone", note="User verified", db_path=test_db)
        assert corr_id is not None
        corrs = memory.get_corrections("keys", db_path=test_db)
        assert len(corrs) == 1
        assert corrs[0]["relation_type"] == "beside"

        # 4. Clear memory
        memory.clear_memory(test_db)
        assert memory.latest_scan(test_db) is None
        assert len(memory.get_corrections(db_path=test_db)) == 0
