import os
import cv2
import time
import threading
import numpy as np
from typing import Dict, Any, Tuple, Optional
from ultralytics import YOLO

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode


# Spatial parameters database mockup
SPATIAL_PARAMS_DB: Dict[int, Dict[str, Any]] = {
    101: {
        "store_name": "Electronics Dept",
        "zone_name": "Premium Displays",
        "zone_bbox": (100, 100, 500, 400)
    }
}

# Standard 3D model points for Head Pose Estimation (in mm)
MODEL_POINTS_3D = np.array([
    (0.0, 0.0, 0.0),             # Nose tip
    (0.0, -330.0, -65.0),        # Chin
    (-225.0, 170.0, -135.0),     # Left eye left corner
    (225.0, 170.0, -135.0),      # Right eye right corner
    (-150.0, -150.0, -125.0),    # Left mouth corner
    (150.0, -150.0, -125.0)      # Right mouth corner
], dtype=np.float64)

# WHY this path: keeps the model file right next to this script, so the
# path works the same regardless of where uvicorn is launched from.
MODEL_PATH = os.path.join(os.path.dirname(__file__), "face_landmarker.task")


def get_camera_matrix(img_w: int, img_h: int) -> Tuple[np.ndarray, np.ndarray]:
    """Generates camera matrix and distortion coefficients based on frame dimensions."""
    focal_length = img_w
    center = (img_w / 2, img_h / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype=np.float64)
    dist_coeffs = np.zeros((4, 1), dtype=np.float64)
    return camera_matrix, dist_coeffs


def estimate_head_pose(landmarks, img_w: int, img_h: int):
    """Calculates pitch, yaw, and roll using solvePnP."""
    landmark_indices = [1, 152, 33, 263, 61, 291]
    image_points = []

    for idx in landmark_indices:
        lm = landmarks[idx]
        image_points.append([lm.x * img_w, lm.y * img_h])

    image_points = np.array(image_points, dtype=np.float64)
    camera_matrix, dist_coeffs = get_camera_matrix(img_w, img_h)

    success, rotation_vec, translation_vec = cv2.solvePnP(
        MODEL_POINTS_3D,
        image_points,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE
    )

    if not success:
        return None, None

    rotation_mat, _ = cv2.Rodrigues(rotation_vec)
    angles, _, _, _, _, _ = cv2.RQDecomp3x3(rotation_mat)

    pitch, yaw, roll = angles[0], angles[1], angles[2]
    return pitch, yaw


class ThreadedVideoIngest:
    """
    WHY a class (not the old plain function): main.py's lifespan needs
    something it can START on server startup and STOP on server shutdown --
    that requires an object that remembers its own state (is it running?
    what was the last frame?) across many separate calls. A single function
    that loops forever with cv2.imshow can't be started/stopped from outside
    and can't run in the background while the API also serves web requests.

    WHY no cv2.imshow here: this code now runs inside a FastAPI background
    thread on a server -- there is no desktop window to draw into. Instead,
    we keep the latest ANNOTATED frame in memory (self.latest_jpeg) so a
    future API endpoint (e.g. GET /api/video/latest-frame) can serve it to
    a browser as an image, without ever popping up a native window.
    """

    def __init__(self, source: Any = 0, fallback_source: Optional[str] = None,
                 max_consecutive_failures: int = 15):
        """
        WHY fallback_source is a SEPARATE argument, not baked into a library
        dict: this class shouldn't need to know about your app's specific
        set of demo videos -- main.py decides what "safe backup video"
        means, and just hands the path in.

        WHY max_consecutive_failures, not "one failed read = dead": a live
        camera (webcam or RTSP) can drop a single frame here and there from
        normal network jitter -- that's not "the camera is gone." Only
        treat the source as truly lost after several reads IN A ROW fail.
        """
        self.original_source = self._normalize(source)
        self.fallback_source = fallback_source
        self.max_consecutive_failures = max_consecutive_failures

        self.source = self.original_source
        self.is_fallback_active = False
        self.is_live_source = self._looks_like_live_source(self.original_source)

        self.capture: Optional[cv2.VideoCapture] = None
        self.model: Optional[YOLO] = None
        self.face_landmarker: Optional[Any] = None

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self.frame_count = 0
        self.latest_jpeg: Optional[bytes] = None
        self.latest_metadata: Dict[str, Any] = {}

    @staticmethod
    def _normalize(source: Any) -> Any:
        """WHY this cast: cv2.VideoCapture needs an int for webcam indices,
        but main.py passes it as the string "0" -- so we convert here."""
        if isinstance(source, str) and source.isdigit():
            return int(source)
        return source

    @staticmethod
    def _looks_like_live_source(source: Any) -> bool:
        """WHY this matters: a webcam or RTSP feed that stops delivering
        frames means 'connection lost' -- fail over. A LOCAL VIDEO FILE
        reaching its end is normal (the file finished playing), not a
        failure -- so it's treated differently (looped) instead."""
        if isinstance(source, int):
            return True  # webcam device index
        if isinstance(source, str) and source.lower().startswith(("rtsp://", "http://", "https://")):
            return True
        return False

    def _open_capture(self, source: Any) -> bool:
        """Attempts to open a video source. Returns True/False instead of
        raising, so callers can decide what to do next (e.g. try a fallback)."""
        if self.capture is not None:
            self.capture.release()
        self.capture = cv2.VideoCapture(source)
        return self.capture.isOpened()

    def _fail_over_to_fallback(self) -> bool:
        """
        WHY this is its own method, called from two places (initial open
        AND mid-stream disconnect): both situations mean the exact same
        thing to the rest of the system -- "the intended source isn't
        available, use the safe backup instead" -- so they should run
        through identical logic rather than duplicating it.
        """
        if not self.fallback_source or self.is_fallback_active:
            return False  # no fallback configured, or already using it

        print(f"[VideoIngest] Attempting fallback source: {self.fallback_source}")
        if self._open_capture(self.fallback_source):
            self.is_fallback_active = True
            self.source = self.fallback_source
            print(f"[VideoIngest] Fallback ACTIVE: now playing {self.fallback_source}")
            return True

        print(f"[VideoIngest] Fallback source also failed to open: {self.fallback_source}")
        return False

    def start_processing(self):
        """WHY separate from __init__: loading YOLO + MediaPipe models takes
        real time (seconds). We don't want that to block FastAPI's startup
        event -- so model loading + the capture loop both happen inside the
        background thread, not in the constructor."""
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        return self

    def _run_loop(self):
        print(f"[VideoIngest] Loading YOLO model...")
        self.model = YOLO("yolov8n.pt")

        print(f"[VideoIngest] Loading MediaPipe FaceLandmarker from {MODEL_PATH}")
        if not os.path.exists(MODEL_PATH):
            print(f"[VideoIngest] WARNING: model file not found at {MODEL_PATH}. "
                  f"Face/attention detection will be skipped. See setup instructions "
                  f"to download face_landmarker.task.")
        else:
            base_options = BaseOptions(model_asset_path=MODEL_PATH)
            options = FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=RunningMode.VIDEO,   # WHY VIDEO mode: we're feeding a
                                                    # continuous sequence of frames,
                                                    # not one-off images -- this mode
                                                    # lets MediaPipe use timestamps to
                                                    # track faces smoothly across frames.
                num_faces=5,
                min_face_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self.face_landmarker = FaceLandmarker.create_from_options(options)

        if not self._open_capture(self.source):
            # WHY try the fallback immediately, right here, instead of just
            # giving up: if the webcam/RTSP camera was never reachable in
            # the first place (unplugged, wrong IP, no internet), there's
            # no point starting a thread that does nothing -- fail over
            # to the safe local video right away, same as a mid-stream drop.
            if not self._fail_over_to_fallback():
                print(f"[VideoIngest] ERROR: could not open source, and no "
                      f"working fallback available. Stopping.")
                self._running = False
                return

        start_time = time.time()
        consecutive_failures = 0

        while self._running:
            if self.capture is None:
                print("[VideoIngest] ERROR: capture is None. Stopping.")
                break

            ret, frame = self.capture.read()

            if not ret:
                # WHY check the CURRENT source's type, not the original: once
                # we've failed over, we're now playing a local file -- it
                # should LOOP when it ends, not trigger another "disconnect"
                # search. Only the source we're ACTUALLY reading from right
                # now matters for this decision.
                currently_on_live_source = self._looks_like_live_source(self.source)

                if currently_on_live_source and not self.is_fallback_active:
                    # WHY count failures instead of failing over on the
                    # very first bad read: a live camera can drop one frame
                    # from normal network jitter -- that's not "the camera
                    # is gone." Only treat it as a real disconnect after
                    # several reads IN A ROW fail.
                    consecutive_failures += 1
                    print(f"[VideoIngest] Frame read failed "
                          f"({consecutive_failures}/{self.max_consecutive_failures})")
                    if consecutive_failures >= self.max_consecutive_failures:
                        print("[VideoIngest] Connection appears LOST. "
                              "Switching to local fallback video...")
                        if self._fail_over_to_fallback():
                            consecutive_failures = 0
                            continue
                        else:
                            print("[VideoIngest] No fallback available. Stopping.")
                            break
                    time.sleep(0.2)  # brief pause before retrying the same source
                    continue

                elif not currently_on_live_source:
                    # WHY loop instead of stopping: a LOCAL VIDEO FILE
                    # reaching its end is normal, expected behavior -- for
                    # a monitoring system that's supposed to run
                    # continuously, looping the same file is more useful
                    # than the whole pipeline going silent.
                    print("[VideoIngest] Local video reached its end -- looping.")
                    self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                else:
                    # Already on fallback and IT also failed -- nothing left to try.
                    print("[VideoIngest] Fallback source also failed. Stopping.")
                    break

            # A good frame was read -- reset the failure counter.
            consecutive_failures = 0

            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # --- YOLO detection & tracking ---
            results = self.model.track(frame, persist=True, verbose=False)
            if results and len(results) > 0 and results[0].boxes is not None:
                for box in results[0].boxes:
                    coords = box.xyxy[0]
                    if hasattr(coords, "cpu"):
                        coords = coords.cpu().numpy()
                    x1, y1, x2, y2 = map(int, coords[:4])
                    track_id = int(box.id[0].item()) if box.id is not None else -1

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, f"ID: {track_id}", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # --- MediaPipe FaceLandmarker (Tasks API) ---
            if self.face_landmarker is not None:
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                timestamp_ms = int((time.time() - start_time) * 1000)
                detection_result = self.face_landmarker.detect_for_video(mp_image, timestamp_ms)

                if detection_result.face_landmarks:
                    for face_landmarks in detection_result.face_landmarks:
                        pitch, yaw = estimate_head_pose(face_landmarks, w, h)
                        if pitch is not None and yaw is not None:
                            cv2.putText(frame, f"Pitch: {pitch:.1f}, Yaw: {yaw:.1f}",
                                        (30, 40), cv2.FONT_HERSHEY_SIMPLEX,
                                        0.7, (255, 255, 0), 2)

            # --- Store the result for the API to serve, instead of imshow() ---
            ok, jpeg_buffer = cv2.imencode(".jpg", frame)
            with self._lock:
                self.frame_count += 1
                if ok:
                    self.latest_jpeg = jpeg_buffer.tobytes()
                self.latest_metadata = {
                    "frame_count": self.frame_count,
                    "resolution": f"{w}x{h}",
                    "timestamp": time.time(),
                    "active_source": str(self.source),
                    "is_fallback_active": self.is_fallback_active,
                }

        if self.capture is not None:
            self.capture.release()
        print("[VideoIngest] Capture released. Thread stopping.")

    def get_latest_jpeg(self) -> Optional[bytes]:
        """WHY a getter with a lock: the background thread writes
        self.latest_jpeg continuously while an API route might read it at
        the exact same instant -- the lock prevents reading a half-written value."""
        with self._lock:
            return self.latest_jpeg

    def get_latest_metadata(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.latest_metadata)

    def stop_processing(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        print("[VideoIngest] Stopped.")