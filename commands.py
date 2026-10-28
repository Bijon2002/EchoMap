"""
commands.py - Command & Natural Language Query Engine for EchoMap
Answers questions directly from saved SQLite spatial memory and user corrections
without incurring unnecessary API vision costs or camera activation.
"""

import re
from typing import Any, Dict, List, Optional
from spatial import region, find_object, nearby_objects, compare_scans
import memory


def parse_target_name(text: str, prefixes: List[str]) -> str:
    """Extracts the object name following known query prefixes."""
    lowered = text.lower()
    for prefix in prefixes:
        if prefix in lowered:
            candidate = lowered.split(prefix, 1)[1]
            # Strip trailing punctuation and common stop words
            cleaned = re.sub(r"[?!.,]", "", candidate).strip()
            # Remove leading articles if present
            for art in ["my ", "the ", "a ", "an "]:
                if cleaned.startswith(art):
                    cleaned = cleaned[len(art):].strip()
            return cleaned
    return ""


def format_scan_time(iso_str: Optional[str]) -> str:
    """Converts an ISO timestamp to a friendly short description."""
    if not iso_str:
        return "the saved scan"
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return f"scan at {dt.strftime('%H:%M')}"
    except Exception:
        return "the last scan"


def answer_question(
    command: str,
    objects: List[Dict[str, Any]],
    scan_meta: Optional[Dict[str, Any]] = None,
    previous_objects: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Evaluates a user voice or text command against the persistent spatial memory
    and user corrections.
    """
    text = command.lower().strip()
    scan_label = format_scan_time(scan_meta.get("created_at") if scan_meta else None)

    # Empty memory guard
    if not objects and not ("hello" in text or "help" in text or "who are you" in text):
        return (
            "I have no saved objects for this workspace yet. "
            "Please select 'Scan Desk' or say 'Remember my desk' to take an initial scan."
        )

    # Greeting / wake / help
    if any(greet in text for greet in ["hey echomap", "hello echomap", "hi echomap", "hello", "hi"]):
        if not text.replace("hey echomap", "").replace("hello echomap", "").strip():
            count = len(objects)
            return (
                f"Hello! EchoMap is ready. I currently remember {count} objects on your desk. "
                "You can ask me where an item is, what is beside it, or ask me to check for changes."
            )

    if any(q in text for q in ["help", "what can you do", "commands", "options"]):
        return (
            "You can ask: 'Where are my keys?', 'What is beside my phone?', 'What is on my desk?', "
            "'Did my coffee mug move?', or 'Scan desk' to capture a fresh memory."
        )

    # Query: What is on my desk / list objects
    if any(q in text for q in ["what is on my desk", "what's on my desk", "list objects", "what do you remember", "what is on the desk"]):
        if not objects:
            return "Your desk memory is currently empty. Please scan your desk first."
        names = [o["name"] for o in objects]
        if len(names) == 1:
            return f"In {scan_label}, I remember only one object: a {names[0]}."
        items_str = ", ".join(names[:-1]) + f", and {names[-1]}"
        return f"According to {scan_label}, you have {len(names)} items on your desk: {items_str}."

    # Query: What is beside / near / next to [object]
    beside_match = parse_target_name(
        text,
        [
            "what is beside ", "what's beside ",
            "what is near ", "what's near ",
            "what is next to ", "what's next to ",
            "what is around ", "what's around ",
            "what objects are near ", "what is close to "
        ]
    )
    if beside_match:
        target = find_object(objects, beside_match)
        # Check user corrections first
        corrections = memory.get_corrections(beside_match)
        correction_note = ""
        if corrections:
            top_corr = corrections[0]
            correction_note = f" Note: You previously taught me that your {top_corr['object_name']} is {top_corr['relation_type']} your {top_corr['reference_object']}."

        if not target:
            if correction_note:
                return f"I didn't visually detect {beside_match} in the last scan.{correction_note}"
            return f"I could not find a remembered {beside_match} on your desk."

        nearby = nearby_objects(objects, target, threshold=0.32)
        if not nearby:
            return f"I didn't find any other objects positioned closely around your {target['name']} in {scan_label}.{correction_note}"

        descriptions = []
        for n in nearby[:3]:
            descriptions.append(f"{n['name']} ({n['relation']})")
        joined = ", ".join(descriptions)
        return f"In {scan_label}, your {target['name']} was near: {joined}.{correction_note}"

    # Query: Where is / Where are [object]
    where_match = parse_target_name(
        text,
        [
            "where are my ", "where is my ",
            "where's my ", "where are the ",
            "where is the ", "where's the ",
            "where are ", "where is "
        ]
    )
    if where_match:
        target = find_object(objects, where_match)
        corrections = memory.get_corrections(where_match)
        correction_note = ""
        if corrections:
            top_corr = corrections[0]
            correction_note = f" (User note: saved as {top_corr['relation_type']} {top_corr['reference_object']})."

        if not target:
            if corrections:
                return (
                    f"I couldn't locate {where_match} in the visual scan, "
                    f"but your recorded note states it is {corrections[0]['relation_type']} {corrections[0]['reference_object']}."
                )
            return (
                f"I could not find {where_match} in {scan_label}. "
                "Would you like to take a fresh scan to see if it is visible now?"
            )

        loc = region(target["x"], target["y"])
        # Check if there are neighboring objects to give richer spatial context
        neighbors = nearby_objects(objects, target, threshold=0.25)
        if neighbors:
            closest = neighbors[0]
            return (
                f"Your {target['name']} was in the {loc}, "
                f"just {closest['relation']} your {closest['name']}.{correction_note}"
            )
        return f"Your {target['name']} was in the {loc}.{correction_note}"

    # Query: Movement / Check if [object] moved
    if any(q in text for q in ["move", "moved", "check whether", "check if", "did my", "has my"]):
        target_name = parse_target_name(
            text,
            [
                "did my ", "has my ", "check whether my ", "check if my ",
                "check whether ", "check if ", "did the ", "has the "
            ]
        )
        if not target_name:
            target_name = text.replace("did", "").replace("moved", "").replace("move", "").strip()

        if previous_objects is not None and len(previous_objects) > 0:
            diffs = compare_scans(previous_objects, objects)
            diff_match = next((d for d in diffs if target_name in d["name"].lower() or d["name"].lower() in target_name), None)
            if diff_match:
                return diff_match["description"]
            return f"I checked the latest scans. There is no confirmed movement for {target_name}."
        else:
            target = find_object(objects, target_name)
            if target:
                loc = region(target["x"], target["y"])
                return (
                    f"Your {target['name']} was recorded in the {loc}. "
                    "To verify if it has moved since, please perform a new scan."
                )
            return f"I don't have enough past scans to confirm movement for {target_name}."

    # Teach / Correction command: "my [object] is beside [other_object]"
    teach_match = re.search(r"(?:my|the)\s+([a-zA-Z\s]+?)\s+(?:is|are)\s+(beside|near|next to|on|left of|right of)\s+(?:my|the|a)?\s*([a-zA-Z\s]+)", text)
    if teach_match:
        obj_a = teach_match.group(1).strip()
        rel = teach_match.group(2).strip()
        obj_b = teach_match.group(3).strip()
        memory.save_correction(obj_a, rel, obj_b, note="Voice user correction")
        return f"Understood. I have remembered that your {obj_a} is {rel} your {obj_b}."

    # Fallback to general object search
    words = [w.strip() for w in re.sub(r"[?!.,]", "", text).split() if len(w) > 2 and w not in ["the", "and", "desk", "look", "find", "can", "you", "tell"]]
    for w in words:
        target = find_object(objects, w)
        if target:
            loc = region(target["x"], target["y"])
            return f"I found your {target['name']} in the {loc} in {scan_label}."

    return (
        f"I'm not sure how to answer '{command}'. "
        "Try asking 'Where is my [item]?' or 'What is on my desk?'."
    )
