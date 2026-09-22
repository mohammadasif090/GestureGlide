"""GestureGlide — Control your mouse cursor by pointing with your finger.

Usage:
    python main.py

Controls:
    - Move index finger to glide cursor across the screen
    - Pinch thumb + index finger together to click
    - Press 't' to toggle between Free Tracking and Strict Pointing
    - Press ESC or 'q' in the debug window or terminal to quit
"""

import time
import cv2

import config
from hand_tracker import HandTracker
from gesture import is_pointing, get_index_tip_position, is_pinching, get_diagnostics
from mouse_control import MouseController


def draw_hud(
    frame,
    status: str,
    cursor_pos: tuple[int, int] | None,
    clicking: bool,
    diag: dict | None,
    fps: float,
    always_track: bool,
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

    # 2. Draw Fingertip Crosshair
    if diag is not None:
        tip_x_px = int(diag["tip_pos"][0] * w)
        tip_y_px = int(diag["tip_pos"][1] * h)
        ring_color = (0, 255, 0) if (diag["is_pointing"] or always_track) else (0, 165, 255)
        cv2.circle(frame, (tip_x_px, tip_y_px), 14, ring_color, 2, lineType=cv2.LINE_AA)
        cv2.circle(frame, (tip_x_px, tip_y_px), 3, ring_color, -1)

    # 3. Top Status Bar (semi-transparent)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 72), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Status text & color
    if status in ("GLIDING", "POINTING"):
        status_color = (0, 255, 0)
    elif status == "HAND DETECTED":
        status_color = (0, 200, 255)
    else:
        status_color = (0, 0, 255)

    mode_label = "FREE" if always_track else "STRICT"
    cv2.putText(
        frame,
        f"Status: {status} [{mode_label}]",
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
        idx_txt = f"IndexRatio: {diag['index_ratio']:.2f}"
        pinch_txt = f"PinchDist: {diag['pinch_dist']:.3f} (click < {config.PINCH_THRESHOLD})"
        sub_text = f"{idx_txt}  |  {pinch_txt}"
        cv2.putText(
            frame,
            sub_text,
            (12, 54),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
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
                0.48,
                (0, 255, 255),
                1,
            )

    # Click indicator
    if clicking:
        cv2.circle(frame, (w - 30, 22), 10, (0, 0, 255), -1)
        cv2.putText(
            frame,
            "CLICK!",
            (w - 110, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 255),
            2,
        )


def main():
    print("=" * 60)
    print("  GestureGlide  —  Finger Mouse Control Prototype")
    print("=" * 60)
    print("  [Controls]")
    print("    - Move index finger in front of camera to glide cursor")
    print("    - Pinch (thumb + index tip) to trigger mouse click")
    print("    - Press 't' to toggle between Free Tracking and Strict Mode")
    print("    - Press ESC or 'q' in debug window to quit")
    print("=" * 60)

    tracker = HandTracker()
    mouse = MouseController()

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
        print(f"\n🖥️  DEBUG HUD WINDOW ACTIVE: Look for '{config.DEBUG_WINDOW_NAME}' on your screen!")
        print("   (It is set to float on top so you can see live tracking & camera feed)")

    print("\nTracking loop started. Live logs appearing below:")
    print("-" * 60)

    last_log_time = 0.0
    frame_count = 0
    fps_start_time = time.time()
    current_fps = 0.0
    always_track = config.ALWAYS_TRACK_HAND

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("WARNING: Dropped frame or webcam disconnected.")
                time.sleep(0.05)
                continue

            # Calculate FPS
            frame_count += 1
            now = time.time()
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
            clicking = False
            diag = None

            if landmarks is not None:
                diag = get_diagnostics(landmarks)
                should_move = always_track or diag["is_pointing"]

                if should_move:
                    status = "GLIDING" if always_track else "POINTING"
                    tip_x, tip_y = diag["tip_pos"]
                    cursor_pos = mouse.move_direct(tip_x, tip_y)

                    if diag["is_pinching"]:
                        clicking = mouse.click()
                else:
                    status = "HAND DETECTED"

            # Periodic Terminal Logging
            if now - last_log_time >= config.TERMINAL_LOG_INTERVAL:
                last_log_time = now
                timestamp = time.strftime("%H:%M:%S")

                if landmarks is None:
                    print(f"[{timestamp}] ❌ [NO HAND] Hand not seen by camera...")
                elif should_move:
                    click_str = " | 💥 CLICK!" if clicking else ""
                    print(
                        f"[{timestamp}] 🟢 [{status}] Finger: ({diag['tip_pos'][0]:.2f}, {diag['tip_pos'][1]:.2f}) "
                        f"-> Cursor: {cursor_pos} | Pinch: {diag['pinch_dist']:.3f} | FPS: {current_fps:.0f}{click_str}"
                    )
                else:
                    print(
                        f"[{timestamp}] 🟡 [HAND DETECTED] IndexRatio: {diag['index_ratio']:.2f} "
                        f"(Strict mode: need >= {config.FINGER_EXTENDED_RATIO} to move)"
                    )

            # Debug UI HUD
            if config.SHOW_DEBUG_WINDOW:
                tracker.draw_landmarks(frame, results)
                draw_hud(frame, status, cursor_pos, clicking, diag, current_fps, always_track)
                cv2.imshow(config.DEBUG_WINDOW_NAME, frame)

            # Keyboard commands
            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord("q"):
                print("\nQuit command received.")
                break
            elif key == ord("t"):
                always_track = not always_track
                mode_str = "Free Tracking (All hand gestures move cursor)" if always_track else "Strict Pointing Mode"
                print(f"\n[MODE TOGGLE] Switched to: {mode_str}\n")

    finally:
        cap.release()
        tracker.release()
        cv2.destroyAllWindows()
        print("Webcam released and windows closed. Goodbye!")


if __name__ == "__main__":
    main()
