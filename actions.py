"""Maps gesture events to OS-level actions (mouse, keyboard, scroll)."""

import pyautogui
import config
from gesture_engine import GestureType, GestureEvent
from mouse_control import MouseController

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0


class ActionDispatcher:
    """Receives GestureEvents and executes corresponding OS actions."""

    def __init__(self, mouse: MouseController):
        self.mouse = mouse
        self._dragging = False
        self._last_right_click = 0.0
        self._precision_mode = False

    def dispatch(self, event: GestureEvent, now: float) -> dict:
        """Process a gesture event and perform OS actions.

        Returns a dict of actions taken this frame for logging/HUD display.
        """
        actions = {
            "moved": False,
            "clicked": False,
            "right_clicked": False,
            "scrolled": False,
            "drag_started": False,
            "drag_stopped": False,
            "precision": False,
            "cursor_pos": None,
            "gesture_name": event.gesture.value,
        }

        # --- POINT: Move cursor ---
        if event.gesture == GestureType.POINT and event.tip_pos:
            actions["cursor_pos"] = self.mouse.move_direct(event.tip_pos[0], event.tip_pos[1])
            actions["moved"] = True

        # --- PINCH CLICK: Left click ---
        elif event.gesture == GestureType.PINCH_CLICK:
            if event.entered:
                actions["clicked"] = self.mouse.click()

        # --- RIGHT CLICK: Thumb + middle pinch ---
        elif event.gesture == GestureType.RIGHT_CLICK:
            if event.entered:
                if now - self._last_right_click >= config.RIGHT_CLICK_COOLDOWN:
                    self._last_right_click = now
                    actions["right_clicked"] = self.mouse.right_click()

        # --- OPEN PALM: Scroll mode ---
        elif event.gesture == GestureType.OPEN_PALM:
            if event.palm_delta_y is not None:
                if abs(event.palm_delta_y) > config.SCROLL_MIN_MOVEMENT:
                    # palm_delta_y > 0 means hand moved down in frame → scroll down
                    scroll_amount = int(-event.palm_delta_y * config.SCROLL_SPEED * 100)
                    if scroll_amount != 0:
                        pyautogui.scroll(scroll_amount)
                        actions["scrolled"] = True

        # --- FIST: Drag mode ---
        elif event.gesture == GestureType.FIST:
            if event.entered and not self._dragging:
                pyautogui.mouseDown()
                self._dragging = True
                actions["drag_started"] = True
            # Continue moving while in fist using palm center
            if event.palm_pos and self._dragging:
                actions["cursor_pos"] = self.mouse.move_direct(
                    event.palm_pos[0], event.palm_pos[1]
                )
                actions["moved"] = True

        # --- PEACE: Precision mode (slow cursor) ---
        elif event.gesture == GestureType.PEACE and event.tip_pos:
            self._precision_mode = True
            actions["precision"] = True
            # Temporarily reduce smoothing alpha for finer control
            original_alpha = config.SMOOTHING_ALPHA
            config.SMOOTHING_ALPHA = original_alpha * config.PRECISION_SPEED_FACTOR
            actions["cursor_pos"] = self.mouse.move_direct(
                event.tip_pos[0], event.tip_pos[1]
            )
            config.SMOOTHING_ALPHA = original_alpha
            actions["moved"] = True

        # --- Handle drag release when leaving fist gesture ---
        if event.exited and self._dragging and event.gesture != GestureType.FIST:
            pyautogui.mouseUp()
            self._dragging = False
            actions["drag_stopped"] = True

        # Also release drag if current gesture changed away from FIST
        if self._dragging and event.gesture != GestureType.FIST:
            pyautogui.mouseUp()
            self._dragging = False
            actions["drag_stopped"] = True

        return actions
