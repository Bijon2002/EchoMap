"""
tests/test_commands.py - Command & Natural Language Query Tests
"""

import commands


def test_empty_objects():
    res = commands.answer_question("Where are my keys?", [])
    assert "scan" in res.lower() or "empty" in res.lower()


def test_where_is_object():
    objects = [
        {"name": "keys", "x": 0.15, "y": 0.15, "confidence": 0.9},
        {"name": "phone", "x": 0.20, "y": 0.18, "confidence": 0.95},
    ]
    res = commands.answer_question("Where are my keys?", objects)
    assert "keys" in res.lower()
    assert "top-left" in res.lower()


def test_what_is_beside():
    objects = [
        {"name": "phone", "x": 0.50, "y": 0.50, "confidence": 0.9},
        {"name": "coffee mug", "x": 0.55, "y": 0.52, "confidence": 0.9},
    ]
    res = commands.answer_question("What is beside my phone?", objects)
    assert "coffee mug" in res.lower()


def test_what_is_on_my_desk():
    objects = [
        {"name": "phone", "x": 0.50, "y": 0.50, "confidence": 0.9},
        {"name": "notebook", "x": 0.20, "y": 0.20, "confidence": 0.9},
    ]
    res = commands.answer_question("What is on my desk?", objects)
    assert "phone" in res.lower()
    assert "notebook" in res.lower()
