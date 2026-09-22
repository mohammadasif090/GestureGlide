"""Mouse cursor control with smoothing, active area scaling, and click support."""

import ctypes
import os
import time

import pyautogui

import config

# Disable pyautogui's fail-safe
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

IS_WINDOWS = os.name == "nt"


class MouseController:
    """Smoothly moves the OS mouse cursor and handles clicks."""

    def __init__(self):
        self._screen_w, self._screen_h = pyautogui.size()
        self._prev_x: float | None = None
        self._prev_y: float | None = None
        self._last_click_time: float = 0.0

    def _set_cursor_position(self, x: int, y: int):
        """Move cursor using native Win32 API on Windows with fallback to pyautogui."""
        success = False
        if IS_WINDOWS:
            try:
                ret = ctypes.windll.user32.SetCursorPos(int(x), int(y))
                if ret != 0:
                    success = True
            except Exception:
                pass
        if not success:
            try:
                pyautogui.moveTo(int(x), int(y))
            except Exception:
                pass

    def move_direct(self, norm_x: float, norm_y: float) -> tuple[int, int]:
        """Move cursor from pre-mirrored normalized coordinates.

        Applies active tracking padding so the user doesn't have to reach
        the extreme edges of the webcam frame to reach screen borders.

        Args:
            norm_x: Fingertip x in [0, 1] (already mirrored).
            norm_y: Fingertip y in [0, 1].

        Returns:
            (screen_x, screen_y) where the cursor was moved to.
        """
        pad_x = getattr(config, "CAMERA_PADDING_X", 0.15)
        pad_y = getattr(config, "CAMERA_PADDING_Y", 0.15)

        # Rescale normalized coordinates to active region
        clamped_norm_x = max(pad_x, min(norm_x, 1.0 - pad_x))
        clamped_norm_y = max(pad_y, min(norm_y, 1.0 - pad_y))

        span_x = max(1.0 - 2 * pad_x, 0.01)
        span_y = max(1.0 - 2 * pad_y, 0.01)

        scaled_x = (clamped_norm_x - pad_x) / span_x
        scaled_y = (clamped_norm_y - pad_y) / span_y

        raw_x = scaled_x * self._screen_w
        raw_y = scaled_y * self._screen_h

        # Apply EMA smoothing
        if self._prev_x is None:
            smooth_x, smooth_y = raw_x, raw_y
        else:
            alpha = config.SMOOTHING_ALPHA
            smooth_x = alpha * raw_x + (1 - alpha) * self._prev_x
            smooth_y = alpha * raw_y + (1 - alpha) * self._prev_y

        # Dead-zone: skip tiny movements to reduce micro-jitter
        if self._prev_x is not None:
            dx = smooth_x - self._prev_x
            dy = smooth_y - self._prev_y
            if (dx * dx + dy * dy) < (config.DEAD_ZONE_RADIUS ** 2):
                return (int(self._prev_x), int(self._prev_y))

        # Clamp to screen bounds
        screen_x = int(max(0, min(smooth_x, self._screen_w - 1)))
        screen_y = int(max(0, min(smooth_y, self._screen_h - 1)))

        self._prev_x = float(screen_x)
        self._prev_y = float(screen_y)

        self._set_cursor_position(screen_x, screen_y)
        return (screen_x, screen_y)

    def click(self) -> bool:
        """Perform a left click if cooldown has elapsed."""
        now = time.time()
        if now - self._last_click_time < config.CLICK_COOLDOWN:
            return False
        self._last_click_time = now
        try:
            pyautogui.click()
            return True
        except Exception:
            return False

    @property
    def screen_size(self) -> tuple[int, int]:
        return (self._screen_w, self._screen_h)
