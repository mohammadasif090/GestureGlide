"""GestureGlide v0.2 — Full Gesture Vocabulary Mouse Control.

Usage:
    python main.py

Controls:
    - Point (index extended): Glide cursor
    - Pinch (thumb + index): Left click
    - Right pinch (thumb + middle): Right click
    - Open palm + move up/down: Scroll
    - Closed fist: Drag & drop
    - Peace sign (V): Precision mode (fine cursor control)
    - Press ESC or 'q' in debug window or terminal to quit
"""

import time
import cv2

import config
from hand_tracker import HandTracker
from gesture import get_diagnostics
from mouse_control import MouseController
from gesture_engine import GestureEngine, GestureType
from actions import ActionDispatcher


def draw_hud(
    frame,
    status: str,
    cursor_pos: tuple[int, int] | None,
    actions: dict,
    diag: dict | None,
    fps: float,
):
    """Draw rich HUD overlay on the debug frame."""
    h, w = frame.shape[:2]

    # 1. Draw Active Interaction Region Box
    pad_x = int(getattr(config, "CAMERA_PADDING_X", 0.15) * w)
    pad_y = int(getattr(config, "CAMERA_PADDING_Y", 0.15) * h)
    cv2.rectangle(
        frame,
        (pad_x, pad_y),
        (w - pad_x, h - pad_y),
        (180, 180, 180),
        1,
        lineType=cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        "Screen Boundary",
        (pad_x + 6, pad_y + 16),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (180, 180, 180),
        1,
    )

    # 2. Draw Fingertip / Palm Crosshair
    if diag is not None:
        tip_x_px = int(diag["tip_pos"][0] * w)
        tip_y_px = int(diag["tip_pos"][1] * h)
        ring_color = (0, 255, 0)
        if actions.get("precision"):
            ring_color = (255, 200, 0)
        elif status == "FIST":
            ring_color = (0, 140, 255)
        elif status == "PALM":
            ring_color = (255, 255, 0)
        cv2.circle(frame, (tip_x_px, tip_y_px), 14, ring_color, 2, lineType=cv2.LINE_AA)
        cv2.circle(frame, (tip_x_px, tip_y_px), 3, ring_color, -1)

    # 3. Top Status Bar (semi-transparent)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 72), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Status text & color
    if status in ("POINT", "CLICK", "RCLICK", "PALM", "FIST", "PEACE"):
        status_color = (0, 255, 0)
    elif status == "HAND DETECTED":
        status_color = (0, 200, 255)
    else:
        status_color = (0, 0, 255)

    cv2.putText(
        frame,
        f"Gesture: {status}",
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        status_color,
        2,
    )

    # FPS counter
    cv2.putText(
        frame,
        f"FPS: {fps:.0f}",
        (w - 90, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        1,
    )

    # Secondary info line
    if diag is not None:
        fingers_txt = f"Fingers: {diag.get('extended_finger_count', 0)}"
        idx_txt = f"Idx: {diag['index_ratio']:.2f}"
        pinch_txt = f"Pinch: {diag['pinch_dist']:.3f}"
        r_pinch_txt = f"RPinch: {diag.get('right_click_dist', 0.0):.3f}"
        sub_text = f"{fingers_txt} | {idx_txt} | {pinch_txt} | {r_pinch_txt}"
        cv2.putText(
            frame,
            sub_text,
            (12, 54),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (220, 220, 220),
            1,
        )

        if cursor_pos is not None:
            pos_text = f"Cursor: ({cursor_pos[0]}, {cursor_pos[1]})"
            cv2.putText(
                frame,
                pos_text,
                (w - 240, 54),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 255, 255),
                1,
            )

    # Action badge indicators in header
    badge_x = w - 260
    if actions.get("clicked"):
        cv2.circle(frame, (badge_x, 22), 9, (0, 0, 255), -1)
        cv2.putText(frame, "CLICK", (badge_x + 14, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
    elif actions.get("right_clicked"):
        cv2.circle(frame, (badge_x, 22), 9, (255, 0, 255), -1)
        cv2.putText(frame, "R-CLICK", (badge_x + 14, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 255), 2)
    elif actions.get("scrolled"):
        cv2.putText(frame, "SCROLL", (badge_x, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)
    elif actions.get("drag_started") or status == "FIST":
        cv2.putText(frame, "DRAGGING", (badge_x, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 165, 255), 2)
    elif actions.get("precision"):
        cv2.putText(frame, "PRECISION", (badge_x, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 200, 0), 2)


def main():
    print("=" * 65)
    print("  GestureGlide v0.2 — Full Gesture Vocabulary")
    print("=" * 65)
    print("  [Gesture Controls]")
    print("    - Point (Index extended)         -> Glide cursor")
    print("    - Pinch (Thumb + Index)          -> Left Click")
    print("    - Right Pinch (Thumb + Middle)   -> Right Click")
    print("    - Open Palm (Move Up/Down)       -> Scroll")
    print("    - Closed Fist                    -> Drag & Drop")
    print("    - Peace Sign (V)                 -> Precision Mode (0.3x speed)")
    print("    - Press ESC or 'q' in window     -> Quit")
    print("=" * 65)

    tracker = HandTracker()
    mouse = MouseController()
    engine = GestureEngine()
    dispatcher = ActionDispatcher(mouse)

    print(f"Screen resolution: {mouse.screen_size[0]} x {mouse.screen_size[1]}")
    print(f"Opening webcam (Camera Index: {config.CAMERA_INDEX})...")

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)

    if not cap.isOpened():
        print("ERROR: Could not open webcam! Please check CAMERA_INDEX in config.py.")
        return

    # Setup Debug Window
    if config.SHOW_DEBUG_WINDOW:
        cv2.namedWindow(config.DEBUG_WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(config.DEBUG_WINDOW_NAME, config.CAMERA_WIDTH, config.CAMERA_HEIGHT)
        if getattr(config, "DEBUG_WINDOW_TOPMOST", True):
            try:
                cv2.setWindowProperty(config.DEBUG_WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
            except Exception:
                pass
        print(f"\n🖥️  DEBUG HUD WINDOW ACTIVE: '{config.DEBUG_WINDOW_NAME}'")

    print("\nTracking loop started. Live logs appearing below:")
    print("-" * 65)

    last_log_time = 0.0
    frame_count = 0
    fps_start_time = time.time()
    current_fps = 0.0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("WARNING: Dropped frame or webcam disconnected.")
                time.sleep(0.05)
                continue

            now = time.time()

            # Calculate FPS
            frame_count += 1
            if now - fps_start_time >= 1.0:
                current_fps = frame_count / (now - fps_start_time)
                frame_count = 0
                fps_start_time = now

            # Flip frame horizontally for intuitive mirror view
            frame = cv2.flip(frame, 1)

            # Process with MediaPipe HandLandmarker
            results = tracker.process(frame)
            landmarks = tracker.get_landmarks(results)

            status = "NO HAND"
            cursor_pos = None
            diag = None
            actions = {
                "moved": False,
                "clicked": False,
                "right_clicked": False,
                "scrolled": False,
                "drag_started": False,
                "drag_stopped": False,
                "precision": False,
                "cursor_pos": None,
                "gesture_name": "none",
            }

            if landmarks is not None:
                diag = get_diagnostics(landmarks)
                event = engine.update(landmarks)
                actions = dispatcher.dispatch(event, now)

                gesture_name = event.gesture.value.upper()
                status = gesture_name if gesture_name != "NONE" else "HAND DETECTED"
                cursor_pos = actions.get("cursor_pos")
            else:
                event = engine.update(None)
                actions = dispatcher.dispatch(event, now)

            # Periodic Terminal Logging
            if now - last_log_time >= config.TERMINAL_LOG_INTERVAL:
                last_log_time = now
                timestamp = time.strftime("%H:%M:%S")

                if landmarks is None:
                    print(f"[{timestamp}] ❌ [NO HAND] Hand not seen by camera...")
                else:
                    action_str = ""
                    if actions["clicked"]:
                        action_str += " | 🖱️ LEFT CLICK"
                    if actions["right_clicked"]:
                        action_str += " | 🖱️ RIGHT CLICK"
                    if actions["scrolled"]:
                        action_str += " | 📜 SCROLL"
                    if actions["drag_started"]:
                        action_str += " | ✊ DRAG START"
                    if actions["drag_stopped"]:
                        action_str += " | 🖐️ DRAG END"
                    if actions["precision"]:
                        action_str += " | 🎯 PRECISION"

                    fingers_cnt = diag.get("extended_finger_count", 0) if diag else 0
                    print(
                        f"[{timestamp}] 🟢 [{status}] Fingers: {fingers_cnt} "
                        f"-> Cursor: {cursor_pos} | FPS: {current_fps:.0f}{action_str}"
                    )

            # Debug UI HUD
            if config.SHOW_DEBUG_WINDOW:
                tracker.draw_landmarks(frame, results)
                draw_hud(frame, status, cursor_pos, actions, diag, current_fps)
                cv2.imshow(config.DEBUG_WINDOW_NAME, frame)

            # Keyboard commands
            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord("q"):
                print("\nQuit command received.")
                break

    finally:
        cap.release()
        tracker.release()
        cv2.destroyAllWindows()
        print("Webcam released and windows closed. Goodbye!")


if __name__ == "__main__":
    main()
