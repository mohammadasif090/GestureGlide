"""Gesture state machine — recognizes gestures with temporal stability."""

import enum
import config
from gesture import (
    is_pointing, is_pinching, is_open_palm, is_fist,
    is_peace_sign, is_right_click_pinch,
    get_index_tip_position, get_palm_center
)


class GestureType(enum.Enum):
    NONE = "none"
    POINT = "point"           # Index extended → move cursor
    PINCH_CLICK = "click"     # Thumb + index pinch → left click
    RIGHT_CLICK = "rclick"    # Thumb + middle pinch → right click
    OPEN_PALM = "palm"        # All fingers open → scroll mode
    FIST = "fist"             # Closed fist → drag mode
    PEACE = "peace"           # Index + middle → precision cursor mode


class GestureEvent:
    """Emitted by the engine each frame."""
    def __init__(self, gesture: GestureType, entered: bool, exited: bool,
                 tip_pos=None, palm_pos=None, palm_delta_y=None):
        self.gesture = gesture
        self.entered = entered       # True on the frame the gesture was first recognized
        self.exited = exited         # True on the frame the gesture was lost
        self.tip_pos = tip_pos       # (x, y) normalized index fingertip
        self.palm_pos = palm_pos     # (x, y) normalized palm center
        self.palm_delta_y = palm_delta_y  # Vertical movement of palm (for scroll)


class GestureEngine:
    """Evaluates landmarks each frame and emits stable gesture events."""

    def __init__(self):
        self._current_gesture = GestureType.NONE
        self._candidate_gesture = GestureType.NONE
        self._candidate_count = 0
        self._release_count = 0
        self._prev_palm_y = None

    def _classify_raw(self, landmarks) -> GestureType:
        """Classify the raw gesture from a single frame of landmarks.
        Priority order matters — more specific gestures checked first.
        """
        # 1. Check pinch-click first (takes priority during pointing)
        if is_pinching(landmarks):
            return GestureType.PINCH_CLICK
        # 2. Right-click (thumb + middle)
        if is_right_click_pinch(landmarks):
            return GestureType.RIGHT_CLICK
        # 3. Fist (drag mode)
        if is_fist(landmarks):
            return GestureType.FIST
        # 4. Peace sign (precision mode)
        if is_peace_sign(landmarks):
            return GestureType.PEACE
        # 5. Open palm (scroll mode)
        if is_open_palm(landmarks):
            return GestureType.OPEN_PALM
        # 6. Pointing (index finger extended)
        if is_pointing(landmarks):
            return GestureType.POINT
        return GestureType.NONE

    def update(self, landmarks) -> GestureEvent:
        """Process one frame of landmarks and return a GestureEvent.

        Uses hysteresis: a new gesture must be held for GESTURE_HOLD_FRAMES
        before activation, and must be absent for GESTURE_RELEASE_FRAMES
        before deactivation.
        """
        raw = self._classify_raw(landmarks) if landmarks else GestureType.NONE

        # Calculate palm tracking data
        tip_pos = get_index_tip_position(landmarks) if landmarks else None
        palm_pos = get_palm_center(landmarks) if landmarks else None
        palm_delta_y = None
        if palm_pos and self._prev_palm_y is not None:
            palm_delta_y = palm_pos[1] - self._prev_palm_y
        if palm_pos:
            self._prev_palm_y = palm_pos[1]
        else:
            self._prev_palm_y = None

        entered = False
        exited = False

        if raw == self._current_gesture:
            # Gesture is stable — reset counters
            self._candidate_gesture = raw
            self._candidate_count = 0
            self._release_count = 0
        elif raw == self._candidate_gesture:
            # Candidate gesture is being held
            self._candidate_count += 1
            hold_threshold = config.GESTURE_HOLD_FRAMES
            if self._candidate_count >= hold_threshold:
                # Transition to new gesture
                if self._current_gesture != GestureType.NONE:
                    exited = True
                self._current_gesture = raw
                entered = True
                self._candidate_count = 0
                self._release_count = 0
        else:
            # New candidate
            self._candidate_gesture = raw
            self._candidate_count = 1
            if raw == GestureType.NONE and self._current_gesture != GestureType.NONE:
                self._release_count += 1
                release_threshold = config.GESTURE_RELEASE_FRAMES
                if self._release_count >= release_threshold:
                    exited = True
                    self._current_gesture = GestureType.NONE
                    self._release_count = 0

        return GestureEvent(
            gesture=self._current_gesture,
            entered=entered,
            exited=exited,
            tip_pos=tip_pos,
            palm_pos=palm_pos,
            palm_delta_y=palm_delta_y,
        )

    @property
    def current_gesture(self) -> GestureType:
        return self._current_gesture
