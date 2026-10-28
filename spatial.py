"""
spatial.py - Spatial Reasoning Engine for EchoMap
Provides region calculation, distance measurement, relative positioning,
object matching, and scan comparison.
"""

import math
from typing import Any, Dict, List, Optional


def region(x: float, y: float) -> str:
    """
    Computes a human-friendly desk region from normalized (x, y) coordinates.
    x: 0.0 (left) to 1.0 (right)
    y: 0.0 (top/back) to 1.0 (bottom/front)
    """
    horizontal = "left" if x < 1 / 3 else ("right" if x >= 2 / 3 else "centre")
    vertical = "top" if y < 1 / 3 else ("bottom" if y >= 2 / 3 else "middle")

    if vertical == "middle" and horizontal == "centre":
        return "centre of the desk"
    if vertical == "middle":
        return f"{horizontal} side of the desk"
    if horizontal == "centre":
        return f"{vertical} centre of the desk"
    return f"{vertical}-{horizontal} area of the desk"


def distance(obj1: Dict[str, Any], obj2: Dict[str, Any]) -> float:
    """Calculates Euclidean distance between two object coordinates."""
    dx = float(obj1.get("x", 0.0)) - float(obj2.get("x", 0.0))
    dy = float(obj1.get("y", 0.0)) - float(obj2.get("y", 0.0))
    return math.sqrt(dx * dx + dy * dy)


def relative_direction(target: Dict[str, Any], reference: Dict[str, Any]) -> str:
    """
    Describes the relative position of target relative to reference from the user's perspective.
    e.g., 'to the left of', 'to the right of', 'in front of', 'behind'
    """
    dx = float(target.get("x", 0.0)) - float(reference.get("x", 0.0))
    dy = float(target.get("y", 0.0)) - float(reference.get("y", 0.0))

    parts = []
    if abs(dy) > 0.08:
        parts.append("in front of" if dy > 0 else "behind")
    if abs(dx) > 0.08:
        parts.append("to the right of" if dx > 0 else "to the left of")

    if not parts:
        return "right next to"
    return " and ".join(parts)


def find_object(objects: List[Dict[str, Any]], query: str) -> Optional[Dict[str, Any]]:
    """
    Finds an object matching the query name with exact and substring support,
    as well as singular/plural handling.
    """
    if not objects or not query:
        return None

    cleaned = query.strip().lower()

    # Exact match
    for obj in objects:
        if obj.get("name", "").lower() == cleaned:
            return obj

    # Substring match (either query in obj name or obj name in query)
    matches = [
        obj for obj in objects
        if cleaned in obj.get("name", "").lower() or obj.get("name", "").lower() in cleaned
    ]
    if len(matches) == 1:
        return matches[0]

    # Handle basic plurals: 'keys' -> 'key', 'pens' -> 'pen'
    if cleaned.endswith("s"):
        singular = cleaned[:-1]
        for obj in objects:
            if obj.get("name", "").lower() == singular:
                return obj
        sub = [obj for obj in objects if singular in obj.get("name", "").lower()]
        if len(sub) == 1:
            return sub[0]

    # If multiple substring matches, return the one with the highest confidence
    if matches:
        return max(matches, key=lambda o: o.get("confidence", 0.5))

    return None


def nearby_objects(
    objects: List[Dict[str, Any]],
    target: Dict[str, Any],
    threshold: float = 0.28
) -> List[Dict[str, Any]]:
    """
    Returns a list of objects positioned within the threshold distance of the target,
    ordered from nearest to farthest.
    """
    target_id = target.get("id")
    target_name = target.get("name", "").lower()

    candidates = []
    for obj in objects:
        # Avoid matching the object itself
        if target_id is not None and obj.get("id") == target_id:
            continue
        if obj.get("name", "").lower() == target_name and obj.get("x") == target.get("x") and obj.get("y") == target.get("y"):
            continue

        d = distance(target, obj)
        if d <= threshold:
            enriched = dict(obj)
            enriched["distance"] = round(d, 3)
            enriched["relation"] = relative_direction(obj, target)
            candidates.append(enriched)

    candidates.sort(key=lambda o: o["distance"])
    return candidates


def compare_scans(
    old_objects: List[Dict[str, Any]],
    new_objects: List[Dict[str, Any]],
    movement_threshold: float = 0.18
) -> List[Dict[str, Any]]:
    """
    Compares two scans and determines changes.
    Possible statuses:
    - 'same': Object is approximately in the same location
    - 'possibly_moved': Object was detected in a significantly different position
    - 'not_detected': Object from old scan was not found in new scan
    - 'new_object': Object newly appeared in the latest scan
    """
    results = []
    matched_new_indices = set()

    # Check each old object against new scan
    for old_obj in old_objects:
        old_name = old_obj.get("name", "").lower()
        match_idx = None
        best_candidate = None

        # Look for matching object name in new scan
        for idx, new_obj in enumerate(new_objects):
            if idx in matched_new_indices:
                continue
            new_name = new_obj.get("name", "").lower()
            if old_name == new_name or old_name in new_name or new_name in old_name:
                match_idx = idx
                best_candidate = new_obj
                break

        if best_candidate is not None:
            matched_new_indices.add(match_idx)
            dist = distance(old_obj, best_candidate)
            old_region = region(old_obj.get("x", 0.0), old_obj.get("y", 0.0))
            new_region = region(best_candidate.get("x", 0.0), best_candidate.get("y", 0.0))

            if dist > movement_threshold:
                results.append({
                    "name": old_obj.get("name"),
                    "status": "possibly_moved",
                    "distance": round(dist, 2),
                    "old_position": {"x": old_obj.get("x"), "y": old_obj.get("y"), "region": old_region},
                    "new_position": {"x": best_candidate.get("x"), "y": best_candidate.get("y"), "region": new_region},
                    "description": f"{old_obj.get('name')} seems to have moved from the {old_region} to the {new_region}."
                })
            else:
                results.append({
                    "name": old_obj.get("name"),
                    "status": "same",
                    "distance": round(dist, 2),
                    "old_position": {"x": old_obj.get("x"), "y": old_obj.get("y"), "region": old_region},
                    "new_position": {"x": best_candidate.get("x"), "y": best_candidate.get("y"), "region": new_region},
                    "description": f"{old_obj.get('name')} is still in the {new_region}."
                })
        else:
            old_region = region(old_obj.get("x", 0.0), old_obj.get("y", 0.0))
            results.append({
                "name": old_obj.get("name"),
                "status": "not_detected",
                "old_position": {"x": old_obj.get("x"), "y": old_obj.get("y"), "region": old_region},
                "new_position": None,
                "description": f"{old_obj.get('name')} was previously in the {old_region}, but was not detected in this scan."
            })

    # Any new objects in the second scan
    for idx, new_obj in enumerate(new_objects):
        if idx not in matched_new_indices:
            new_region = region(new_obj.get("x", 0.0), new_obj.get("y", 0.0))
            results.append({
                "name": new_obj.get("name"),
                "status": "new_object",
                "old_position": None,
                "new_position": {"x": new_obj.get("x"), "y": new_obj.get("y"), "region": new_region},
                "description": f"New object detected: {new_obj.get('name')} at {new_region}."
            })

    return results
