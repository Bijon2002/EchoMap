"""
tests/test_spatial.py - Spatial Reasoning Unit Tests
Verifies 9-grid region classification, fuzzy object search,
movement detection, and missing item handling.
"""

from spatial import region, find_object, compare_scans, nearby_objects, distance


def test_region():
    assert region(0.1, 0.1) == "top-left area of the desk"
    assert region(0.5, 0.5) == "centre of the desk"
    assert region(0.8, 0.5) == "right side of the desk"
    assert region(0.2, 0.5) == "left side of the desk"
    assert region(0.5, 0.1) == "top centre of the desk"
    assert region(0.5, 0.8) == "bottom centre of the desk"


def test_find_object():
    objects = [
        {"name": "scissors", "x": 0.7, "y": 0.4},
        {"name": "phone", "x": 0.3, "y": 0.5},
    ]
    assert find_object(objects, "phone")["name"] == "phone"
    assert find_object(objects, "cup") is None
    # Substring & plural check
    assert find_object(objects, "phones")["name"] == "phone"


def test_movement():
    old = [{"name": "scissors", "x": 0.2, "y": 0.2}]
    new = [{"name": "scissors", "x": 0.8, "y": 0.8}]
    result = compare_scans(old, new)
    assert result[0]["status"] == "possibly_moved"


def test_missing_object_is_not_confirmed_movement():
    old = [{"name": "keys", "x": 0.2, "y": 0.2}]
    result = compare_scans(old, [])
    assert result[0]["status"] == "not_detected"


def test_nearby_objects():
    objects = [
        {"name": "phone", "x": 0.30, "y": 0.50},
        {"name": "keys", "x": 0.32, "y": 0.52},
        {"name": "coffee mug", "x": 0.90, "y": 0.10},
    ]
    target = objects[0]  # phone
    nearby = nearby_objects(objects, target, threshold=0.15)
    assert len(nearby) == 1
    assert nearby[0]["name"] == "keys"
