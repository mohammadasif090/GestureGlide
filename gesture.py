"""Gesture detection — pointing check, pinch-to-click, and diagnostics."""

import math

import config

# MediaPipe landmark indices
WRIST = 0
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_PIP = 6
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_TIP = 12
RING_PIP = 14
RING_TIP = 16
PINKY_PIP = 18
PINKY_TIP = 20


def distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    """Euclidean distance between two 3D landmarks."""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def get_finger_ratio(
    landmarks: list[tuple[float, float, float]],
    tip_idx: int,
    pip_idx: int,
) -> float:
    """Compute ratio of (tip-to-wrist dist) / (pip-to-wrist dist)."""
    wrist = landmarks[WRIST]
    tip_dist = distance(landmarks[tip_idx], wrist)
    pip_dist = distance(landmarks[pip_idx], wrist)
    if pip_dist == 0:
        return 0.0
    return tip_dist / pip_dist


def is_pointing(landmarks: list[tuple[float, float, float]]) -> bool:
    """Detect the pointing gesture.

    If config.REQUIRE_OTHER_FINGERS_CURLED is False:
        Only checks if index finger is extended.
    If config.REQUIRE_OTHER_FINGERS_CURLED is True:
        Requires index finger extended AND middle, ring, pinky curled.
    """
    index_ratio = get_finger_ratio(landmarks, INDEX_TIP, INDEX_PIP)
    index_extended = index_ratio >= config.FINGER_EXTENDED_RATIO

    if not index_extended:
        return False

    if not config.REQUIRE_OTHER_FINGERS_CURLED:
        return True

    middle_ratio = get_finger_ratio(landmarks, MIDDLE_TIP, MIDDLE_PIP)
    ring_ratio = get_finger_ratio(landmarks, RING_TIP, RING_PIP)
    pinky_ratio = get_finger_ratio(landmarks, PINKY_TIP, PINKY_PIP)

    middle_curled = middle_ratio <= config.FINGER_CURLED_RATIO
    ring_curled = ring_ratio <= config.FINGER_CURLED_RATIO
    pinky_curled = pinky_ratio <= config.FINGER_CURLED_RATIO

    return middle_curled and ring_curled and pinky_curled


def get_index_tip_position(
    landmarks: list[tuple[float, float, float]],
) -> tuple[float, float]:
    """Get the index fingertip position in normalized coordinates (x, y in [0, 1])."""
    tip = landmarks[INDEX_TIP]
    return (tip[0], tip[1])


def get_pinch_distance(landmarks: list[tuple[float, float, float]]) -> float:
    """Euclidean distance between thumb tip and index tip in normalized space."""
    return distance(landmarks[THUMB_TIP], landmarks[INDEX_TIP])


def is_pinching(landmarks: list[tuple[float, float, float]]) -> bool:
    """Detect pinch gesture (thumb tip close to index tip)."""
    return get_pinch_distance(landmarks) < config.PINCH_THRESHOLD


def get_diagnostics(landmarks: list[tuple[float, float, float]]) -> dict:
    """Detailed diagnostics for debug display and logging."""
    idx_ratio = get_finger_ratio(landmarks, INDEX_TIP, INDEX_PIP)
    mid_ratio = get_finger_ratio(landmarks, MIDDLE_TIP, MIDDLE_PIP)
    ring_ratio = get_finger_ratio(landmarks, RING_TIP, RING_PIP)
    pin_ratio = get_finger_ratio(landmarks, PINKY_TIP, PINKY_PIP)

    pinch_d = get_pinch_distance(landmarks)
    pointing = is_pointing(landmarks)
    pinching = pinch_d < config.PINCH_THRESHOLD
    tip_pos = get_index_tip_position(landmarks)

    return {
        "index_ratio": idx_ratio,
        "index_extended": idx_ratio >= config.FINGER_EXTENDED_RATIO,
        "middle_ratio": mid_ratio,
        "ring_ratio": ring_ratio,
        "pinky_ratio": pin_ratio,
        "is_pointing": pointing,
        "pinch_dist": pinch_d,
        "is_pinching": pinching,
        "tip_pos": tip_pos,
    }
