"""Gesture detection — pointing check, pinch-to-click, and diagnostics."""

import math

import config

# MediaPipe landmark indices
WRIST = 0
THUMB_CMC = 1
THUMB_MCP = 2
THUMB_IP = 3
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_PIP = 6
INDEX_DIP = 7
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_DIP = 11
MIDDLE_TIP = 12
RING_MCP = 13
RING_PIP = 14
RING_DIP = 15
RING_TIP = 16
PINKY_MCP = 17
PINKY_PIP = 18
PINKY_DIP = 19
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


def count_extended_fingers(landmarks: list[tuple[float, float, float]]) -> int:
    """Count how many of the 5 fingers are extended."""
    count = 0
    # Thumb: compare thumb tip to thumb IP joint distance from index MCP
    thumb_tip = landmarks[THUMB_TIP]
    thumb_ip = landmarks[THUMB_IP]
    index_mcp = landmarks[INDEX_MCP]
    if distance(thumb_tip, index_mcp) > distance(thumb_ip, index_mcp):
        count += 1

    # Index, Middle, Ring, Pinky
    finger_tips = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
    finger_pips = [INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP]
    for tip_idx, pip_idx in zip(finger_tips, finger_pips):
        ratio = get_finger_ratio(landmarks, tip_idx, pip_idx)
        if ratio >= config.FINGER_EXTENDED_RATIO:
            count += 1
    return count


def is_open_palm(landmarks: list[tuple[float, float, float]]) -> bool:
    """Detect open palm: all or nearly all fingers extended."""
    return count_extended_fingers(landmarks) >= config.SCROLL_PALM_MIN_FINGERS


def is_fist(landmarks: list[tuple[float, float, float]]) -> bool:
    """Detect closed fist: 0 or 1 fingers extended."""
    return count_extended_fingers(landmarks) <= config.DRAG_FIST_MAX_EXTENDED


def is_peace_sign(landmarks: list[tuple[float, float, float]]) -> bool:
    """Detect peace/V sign: index + middle extended, ring + pinky curled."""
    index_ext = get_finger_ratio(landmarks, INDEX_TIP, INDEX_PIP) >= config.FINGER_EXTENDED_RATIO
    middle_ext = get_finger_ratio(landmarks, MIDDLE_TIP, MIDDLE_PIP) >= config.FINGER_EXTENDED_RATIO
    ring_curled = get_finger_ratio(landmarks, RING_TIP, RING_PIP) <= config.FINGER_CURLED_RATIO
    pinky_curled = get_finger_ratio(landmarks, PINKY_TIP, PINKY_PIP) <= config.FINGER_CURLED_RATIO
    return index_ext and middle_ext and ring_curled and pinky_curled


def get_right_click_distance(landmarks: list[tuple[float, float, float]]) -> float:
    """Distance between thumb tip and middle fingertip (for right-click gesture)."""
    return distance(landmarks[THUMB_TIP], landmarks[MIDDLE_TIP])


def is_right_click_pinch(landmarks: list[tuple[float, float, float]]) -> bool:
    """Detect right-click: thumb tip + middle fingertip pinch."""
    return get_right_click_distance(landmarks) < config.RIGHT_CLICK_THRESHOLD


def get_palm_center(landmarks: list[tuple[float, float, float]]) -> tuple[float, float]:
    """Get approximate palm center (average of wrist, index_mcp, middle_mcp, ring_mcp, pinky_mcp)."""
    indices = [WRIST, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]
    x = sum(landmarks[i][0] for i in indices) / len(indices)
    y = sum(landmarks[i][1] for i in indices) / len(indices)
    return (x, y)


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
        "extended_finger_count": count_extended_fingers(landmarks),
        "is_open_palm": is_open_palm(landmarks),
        "is_fist": is_fist(landmarks),
        "is_peace_sign": is_peace_sign(landmarks),
        "right_click_dist": get_right_click_distance(landmarks),
        "is_right_click_pinch": is_right_click_pinch(landmarks),
        "palm_center": get_palm_center(landmarks),
    }
