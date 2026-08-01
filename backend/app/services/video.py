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


# Spatial parameters database mapping unique Zone IDs & Bounding Boxes
SPATIAL_PARAMS_DB: Dict[Any, Dict[str, Any]] = {
   # --- Local Stock Media Profiles ---
    101: {
        "zone_id": 101,
        "store_name": "Tech World",
        "department": "Electronics",
        "zone_name": "Premium Displays",
        "zone_bbox": (100, 100, 500, 400),  # (x1, y1, x2, y2)
        "camera_type": "pre_recorded"
    },
    102: {
        "zone_id": 102,
        "store_name": "Fresh Market",
        "department": "Grocery",
        "zone_name": "Produce & Dwell Shelf",
        "zone_bbox": (50, 150, 450, 480),
        "camera_type": "pre_recorded"
    },
    103: {
        "zone_id": 103,
        "store_name": "Style Hub",
        "department": "Apparel",
        "zone_name": "Checkout & Fitting Racks",
        "zone_bbox": (200, 80, 600, 420),
        "camera_type": "pre_recorded"
    },

    # --- Live Hardware Profiles ---
    201: {
        "zone_id": 201,
        "store_name": "Live Kiosk",
        "department": "Front Desk / Entrance",
        "zone_name": "Webcam Interactive Display",
        "zone_bbox": (150, 100, 500, 450),
        "camera_type": "live_hardware"
    },
    301: {
        "zone_id": 301,
        "store_name": "Flagship Store",
        "department": "Overhead CCTV",
        "zone_name": "Main Aisle Traffic Stream",
        "zone_bbox": (80, 80, 550, 400),
        "camera_type": "live_rtsp"
    }
}

# Lookup helper mapping source identifiers to Zone IDs
SOURCE_TO_ZONE_ID = {
    "electronics": 101,
    "grocery": 102,
    "apparel": 103,
    "0": 201,        # Laptop webcam
    "webcam": 201,
    "rtsp": 301
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

    def __init__(
            self,
            source: Any = 0,
            fallback_source: Optional[str] = None,
            zone_id: Optional[int] = None,
            max_consecutive_failures: int = 15
            ):

        self.original_source = self._normalize(source)
        self.fallback_source = fallback_source
        self.max_consecutive_failures = max_consecutive_failures

        self.source = self.original_source
        self.is_fallback_active = False
        self.is_live_source = self._looks_like_live_source(self.original_source)

        # Assign active Zone ID based on explicit argument or source lookup
        if zone_id in SPATIAL_PARAMS_DB:
            self.active_zone_id = zone_id
        else:
            source_str = str(self.original_source).lower()
            self.active_zone_id = SOURCE_TO_ZONE_ID.get(source_str, 102) # Default to Grocery (102)

        self.zone_config = SPATIAL_PARAMS_DB.get(self.active_zone_id, SPATIAL_PARAMS_DB[102])


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
        """Converts string digits to int for webcam device indices."""
        if isinstance(source, str) and source.isdigit():
            return int(source)
        return source

    @staticmethod
    def _looks_like_live_source(source: Any) -> bool:
        """Determines if the source is likely a live feed (webcam or RTSP)."""
        if isinstance(source, int):
            return True  # webcam device index
        if isinstance(source, str) and source.lower().startswith(("rtsp://", "http://", "https://")):
            return True
        return False

    def _open_capture(self, source: Any) -> bool:
        """Attempts to open the video capture for the given source."""
        if self.capture is not None:
            self.capture.release()
        self.capture = cv2.VideoCapture(source)
        return self.capture.isOpened()

    def _fail_over_to_fallback(self) -> bool:
        """Attempts to switch to the fallback source if available."""
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
        """Starts the background thread for video ingestion and processing."""
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
           # WHY failover logic: if the primary source fails to open, we should attempt to switch to the fallback source (if configured) before giving up entirely. This is especially important for live sources that may be temporarily unavailable.
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
               # WHY consecutive failure logic: if a live source fails to provide frames repeatedly, it likely indicates a connection issue. We should attempt to switch to the fallback source after a certain number of consecutive failures, rather than immediately giving up on the stream.
                currently_on_live_source = self._looks_like_live_source(self.source)

                if currently_on_live_source and not self.is_fallback_active:
                    # WHY consecutive failure logic: if a live source fails to provide frames repeatedly, it likely indicates a connection issue. We should attempt to switch to the fallback source after a certain number of consecutive failures, rather than immediately giving up on the stream.
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
                   # WHY this is a local video file: if the read fails, it means we've reached the end of the file. Instead of treating it as a failure, we should loop back to the start of the video.
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
            # 1. Draw Mesh Points on Face
                    for lm in face_landmarks:
                          lx, ly = int(lm.x * w), int(lm.y * h)
                          cv2.circle(frame, (lx, ly), 1, (0, 255, 0), -1)

            # 2. Draw Head Pose Pose Text
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
                   "zone_id": self.active_zone_id,
                   "store_name": self.zone_config["store_name"],
                    "department": self.zone_config["department"],
                    "zone_name": self.zone_config["zone_name"],
                    "zone_bbox": self.zone_config["zone_bbox"],
                }

        if self.capture is not None:
            self.capture.release()
        print("[VideoIngest] Capture released. Thread stopping.")

    def get_latest_jpeg(self) -> Optional[bytes]:
        """Returns the most recent JPEG frame, or None if not available."""
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