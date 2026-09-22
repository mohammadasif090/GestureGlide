"""Configuration constants for GestureGlide."""

# --- Camera ---
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
# Margin inside camera frame mapped to full screen (0.15 = inner 70% covers full screen)
CAMERA_PADDING_X = 0.15
CAMERA_PADDING_Y = 0.15

# --- MediaPipe Hand Tracking ---
MODEL_PATH = "hand_landmarker.task"
MAX_NUM_HANDS = 1
MIN_DETECTION_CONFIDENCE = 0.6
MIN_TRACKING_CONFIDENCE = 0.5

# --- Tracking & Gesture Detection ---
# When True (recommended for Touchpad mode), the cursor moves whenever a hand is visible.
# When False, requires index finger to satisfy FINGER_EXTENDED_RATIO.
ALWAYS_TRACK_HAND = True

# Minimum ratio of (tip-to-wrist dist) / (pip-to-wrist dist) for index to be "extended"
FINGER_EXTENDED_RATIO = 1.02
# Maximum ratio for other fingers to be considered "curled" (if required)
FINGER_CURLED_RATIO = 1.20
# If True, requires middle, ring, pinky to be curled. If False, only requires index to be extended.
REQUIRE_OTHER_FINGERS_CURLED = False

# --- Logging ---
TERMINAL_LOG_INTERVAL = 0.5  # Seconds between terminal log updates

# --- Calibration ---
CALIBRATION_FILE = "calibration.json"
CALIBRATION_FRAMES = 40
CALIBRATION_MARGIN = 80

# --- Mouse Control ---
# Exponential moving average smoothing factor (0.0 = slow/heavy, 1.0 = raw/instant)
SMOOTHING_ALPHA = 0.35
# Dead-zone radius in pixels — ignore movements smaller than this to eliminate micro-jitter
DEAD_ZONE_RADIUS = 3
# Click gesture: max distance between thumb tip and index tip in normalized space
PINCH_THRESHOLD = 0.055
# Minimum time between clicks in seconds (debounce)
CLICK_COOLDOWN = 0.4

# --- Debug HUD Window ---
SHOW_DEBUG_WINDOW = True
DEBUG_WINDOW_NAME = "GestureGlide Debug"
# Force the debug window to stay on top of other windows
DEBUG_WINDOW_TOPMOST = True
