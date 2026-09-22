"""Hand tracking wrapper around MediaPipe Tasks HandLandmarker."""

import os
import urllib.request
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import drawing_utils, drawing_styles, HandLandmarksConnections
import numpy as np

import config

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"


class HandTracker:
    """Detects hand landmarks from webcam frames using MediaPipe HandLandmarker."""

    def __init__(self):
        model_path = config.MODEL_PATH
        if not os.path.exists(model_path):
            print(f"Model file '{model_path}' not found. Downloading from {MODEL_URL}...")
            urllib.request.urlretrieve(MODEL_URL, model_path)
            print("Model downloaded successfully.")

        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=config.MAX_NUM_HANDS,
            min_hand_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=config.MIN_TRACKING_CONFIDENCE,
            running_mode=vision.RunningMode.IMAGE,
        )
        self._detector = vision.HandLandmarker.create_from_options(options)

    def process(self, frame_bgr: np.ndarray):
        """Process a BGR frame and return MediaPipe results.

        Returns:
            HandLandmarkerResult object.
        """
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        return self._detector.detect(mp_image)

    def get_landmarks(self, results) -> list[tuple[float, float, float]] | None:
        """Extract normalized (x, y, z) landmarks from results.

        Returns:
            List of 21 (x, y, z) tuples in normalized image coordinates,
            or None if no hand detected.
            x, y are in [0, 1] relative to image dimensions.
            z represents depth relative to the wrist.
        """
        if not results or not results.hand_landmarks or len(results.hand_landmarks) == 0:
            return None

        hand = results.hand_landmarks[0]
        return [(lm.x, lm.y, lm.z) for lm in hand]

    def draw_landmarks(self, frame_bgr: np.ndarray, results) -> np.ndarray:
        """Draw hand landmarks on the frame for debug visualization."""
        if results and results.hand_landmarks:
            for hand_landmarks in results.hand_landmarks:
                drawing_utils.draw_landmarks(
                    frame_bgr,
                    hand_landmarks,
                    HandLandmarksConnections.HAND_CONNECTIONS,
                    drawing_styles.get_default_hand_landmarks_style(),
                    drawing_styles.get_default_hand_connections_style(),
                )
        return frame_bgr

    def release(self):
        """Release MediaPipe resources."""
        self._detector.close()
