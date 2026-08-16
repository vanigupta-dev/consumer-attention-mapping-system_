import os
# Suppress noisy FFmpeg MJPEG decoder warnings (e.g. "overread N")
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "loglevel;quiet"

import cv2
import time
import threading
import numpy as np
from typing import Dict, Any, Tuple, Optional
from ultralytics import YOLO
from app.core.db import SessionLocal
from app.models.analytics import ShopperDwellLog
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from datetime import datetime, timezone
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode


# WHY zone_bbox is now stored as PERCENTAGES (0.0 to 1.0), not fixed pixel
# coords: your videos are 4K (3840x2160) but the old bboxes maxed at
# x=1100px -- so a person standing at the center of frame had their center
# at (1920, 1080), which was ALWAYS outside the old bbox (max x=1100).
# Result: in_zone was ALWAYS False, so no logs were EVER saved.
#
# With percentages, (0.05, 0.05, 0.90, 0.90) means "cover 85% of the
# frame from each edge" -- works identically for 480p, 1080p, or 4K.
# Actual pixel coords are resolved at runtime from real frame dimensions.
SPATIAL_PARAMS_DB: Dict[Any, Dict[str, Any]] = {
    # --- Local Stock Media Profiles ---
    101: {
        "zone_id": 101,
        "store_name": "Tech World",
        "department": "Electronics",
        "zone_name": "Premium Displays",
        "zone_bbox_pct": (0.05, 0.05, 0.90, 0.90),
        "camera_type": "pre_recorded"
    },
    102: {
        "zone_id": 102,
        "store_name": "Fresh Market",
        "department": "Grocery",
        "zone_name": "Produce & Dwell Shelf",
        "zone_bbox_pct": (0.05, 0.05, 0.90, 0.90),
        "camera_type": "pre_recorded"
    },
    103: {
        "zone_id": 103,
        "store_name": "Style Hub",
        "department": "Apparel",
        "zone_name": "Checkout & Fitting Racks",
        "zone_bbox_pct": (0.05, 0.05, 0.90, 0.90),
        "camera_type": "pre_recorded"
    },
    # --- Live Hardware Profiles ---
    201: {
        "zone_id": 201,
        "store_name": "Live Kiosk",
        "department": "Front Desk / Entrance",
        "zone_name": "Webcam Interactive Display",
        "zone_bbox_pct": (0.10, 0.10, 0.90, 0.90),
        "camera_type": "live_hardware"
    },
    301: {
        "zone_id": 301,
        "store_name": "Flagship Store",
        "department": "Overhead CCTV",
        "zone_name": "Main Aisle Traffic Stream",
        "zone_bbox_pct": (0.05, 0.05, 0.90, 0.90),
        "camera_type": "live_rtsp"
    }
}

SOURCE_TO_ZONE_ID = {
    "electronics": 101,
    "grocery": 102,
    "apparel": 103,
    "0": 201,
    "webcam": 201,
    "rtsp": 301
}

MODEL_POINTS_3D = np.array([
    (0.0, 0.0, 0.0),
    (0.0, -330.0, -65.0),
    (-225.0, 170.0, -135.0),
    (225.0, 170.0, -135.0),
    (-150.0, -150.0, -125.0),
    (150.0, -150.0, -125.0)
], dtype=np.float64)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "face_landmarker.task")


def calculate_engagement_score(dwell_sec: float, gaze_sec: float) -> float:
    """
    Computes engagement score between 0.0 and 1.0.
    Weighted by: 60% gaze-to-dwell ratio + 40% total gaze duration.
    """
    if dwell_sec <= 0:
        return 0.0

    gaze_ratio = min(gaze_sec / dwell_sec, 1.0)
    duration_weight = min(gaze_sec / 10.0, 1.0)

    score = (0.6 * gaze_ratio) + (0.4 * duration_weight)
    return round(score, 2)




def resolve_bbox(zone_config: Dict, frame_w: int, frame_h: int) -> Tuple[int, int, int, int]:
    """
    WHY this function: converts percentage-based zone boundaries into real
    pixel coordinates for THIS specific frame. Called every frame so it
    always matches actual incoming frame dimensions, whether 480p or 4K.
    """
    x1p, y1p, x2p, y2p = zone_config["zone_bbox_pct"]
    return (
        int(x1p * frame_w),
        int(y1p * frame_h),
        int(x2p * frame_w),
        int(y2p * frame_h),
    )


def get_camera_matrix(img_w: int, img_h: int) -> Tuple[np.ndarray, np.ndarray]:
    focal_length = img_w
    center = (img_w / 2, img_h / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype=np.float64)
    dist_coeffs = np.zeros((4, 1), dtype=np.float64)
    return camera_matrix, dist_coeffs


def estimate_head_pose(face_landmarks, image_width, image_height):
    if not face_landmarks or len(face_landmarks) < 468:
        return None, None

    landmark_indices = [1, 152, 33, 263, 61, 291]
    image_points = []
    for idx in landmark_indices:
        lm = face_landmarks[idx]
        image_points.append([int(lm.x * image_width), int(lm.y * image_height)])

    image_points = np.array(image_points, dtype=np.float64)
    if len(image_points) < 6:
        return None, None

    camera_matrix, dist_coeffs = get_camera_matrix(image_width, image_height)
    success, rotation_vector, translation_vector = cv2.solvePnP(
        MODEL_POINTS_3D, image_points, camera_matrix, dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE
    )
    if not success:
        return None, None

    rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
    proj_matrix = np.hstack((rotation_matrix, translation_vector))
    _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(proj_matrix)
    return euler_angles[0][0], euler_angles[1][0]


def is_inside_bbox(point: Tuple[int, int], bbox: Tuple[int, int, int, int]) -> bool:
    x, y = point
    x1, y1, x2, y2 = bbox
    return x1 <= x <= x2 and y1 <= y <= y2


def determine_source_mode(source: Any) -> str:
    if isinstance(source, int):
        return "webcam"
    if isinstance(source, str) and source.lower().startswith(("rtsp://", "http://", "https://")):
        return "rtsp"
    return "local_video"


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
        self.source_mode = determine_source_mode(self.original_source)

        if zone_id is not None and zone_id in SPATIAL_PARAMS_DB:
            self.active_zone_id = zone_id
        else:
            source_str = str(self.original_source).lower()
            self.active_zone_id = SOURCE_TO_ZONE_ID.get(source_str, 102)

        self.zone_config = SPATIAL_PARAMS_DB.get(
            self.active_zone_id, SPATIAL_PARAMS_DB[102]
        )

        self.capture: Optional[cv2.VideoCapture] = None
        self.model: Optional[YOLO] = None
        self.face_landmarker: Optional[Any] = None

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self.frame_count = 0
        self.latest_jpeg: Optional[bytes] = None
        self.latest_metadata: Dict[str, Any] = {}
        self.active_tracks: Dict[int, Dict[str, Any]] = {}

    @staticmethod
    def _normalize(source: Any) -> Any:
        if isinstance(source, str) and source.isdigit():
            return int(source)
        return source

    @staticmethod
    def _looks_like_live_source(source: Any) -> bool:
        if isinstance(source, int):
            return True
        if isinstance(source, str) and source.lower().startswith(
            ("rtsp://", "http://", "https://")
        ):
            return True
        return False

    def _open_capture(self, source: Any) -> bool:
        if self.capture is not None:
            self.capture.release()
        self.capture = cv2.VideoCapture(source)
        return self.capture.isOpened()

    def _fail_over_to_fallback(self) -> bool:
        if not self.fallback_source or self.is_fallback_active:
            return False
        print(f"[VideoIngest] Attempting fallback: {self.fallback_source}")
        if self._open_capture(self.fallback_source):
            self.is_fallback_active = True
            self.source = self.fallback_source
            self.source_mode = "local_video"
            print(f"[VideoIngest] Fallback ACTIVE: {self.fallback_source}")
            return True
        return False

    def start_processing(self):
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        return self

    def _run_loop(self):
        print("[VideoIngest] Loading YOLO model...")
        self.model = YOLO("yolov8n.pt")

        if os.path.exists(MODEL_PATH):
            base_options = BaseOptions(model_asset_path=MODEL_PATH)
            options = FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=RunningMode.VIDEO,
                num_faces=5,
                min_face_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self.face_landmarker = FaceLandmarker.create_from_options(options)
            print("[VideoIngest] FaceLandmarker loaded.")
        else:
            print("[VideoIngest] WARNING: face_landmarker.task not found. "
                  "Face detection skipped.")

        if not self._open_capture(self.source):
            if not self._fail_over_to_fallback():
                print("[VideoIngest] ERROR: could not open any source. Stopping.")
                self._running = False
                return

        start_time = time.time()
        consecutive_failures = 0

        while self._running:
            if self.capture is None:
                break

            ret, frame = self.capture.read()

            if not ret:
                currently_on_live = self._looks_like_live_source(self.source)

                if currently_on_live and not self.is_fallback_active:
                    consecutive_failures += 1
                    print(f"[VideoIngest] Frame failed "
                          f"({consecutive_failures}/{self.max_consecutive_failures})")
                    if consecutive_failures >= self.max_consecutive_failures:
                        print("[VideoIngest] Connection LOST. Switching to fallback...")
                        if self._fail_over_to_fallback():
                            consecutive_failures = 0
                            continue
                        else:
                            break
                    time.sleep(0.2)
                    continue

                elif not currently_on_live:
                    self._flush_active_tracks()
                    print("[VideoIngest] Local video reached end -- looping.")
                    self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                else:
                    break

            consecutive_failures = 0
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            now = time.time()

            # WHY resolve_bbox is called here (not once in __init__):
            # frame dimensions are unknown until the capture is open.
            # Also if we fail over to a different-resolution fallback,
            # the bbox correctly adjusts to the new frame size.
            zone_bbox = resolve_bbox(self.zone_config, w, h)
            zx1, zy1, zx2, zy2 = zone_bbox

            # Draw zone boundary on frame
            cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), (255, 0, 0), 2)
            cv2.putText(
                frame,
                f"ZONE:{self.active_zone_id} {self.zone_config['zone_name']}",
                (zx1, zy1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2
            )

            # --- MediaPipe Head Pose / Gaze Detection ---
            has_active_gaze = False
            if self.face_landmarker is not None:
                try:
                    mp_image = mp.Image(
                        image_format=mp.ImageFormat.SRGB, data=rgb_frame
                    )
                    timestamp_ms = int((now - start_time) * 1000)
                    detection_result = self.face_landmarker.detect_for_video(
                        mp_image, timestamp_ms
                    )
                    if detection_result.face_landmarks:
                        for face_landmarks in detection_result.face_landmarks:
                            for lm in face_landmarks:
                                lx = int(lm.x * w)
                                ly = int(lm.y * h)
                                cv2.circle(frame, (lx, ly), 1, (0, 255, 0), -1)
                            pitch, yaw = estimate_head_pose(face_landmarks, w, h)
                            if pitch is not None and yaw is not None:
                                cv2.putText(
                                    frame,
                                    f"Pitch:{pitch:.1f} Yaw:{yaw:.1f}",
                                    (30, 40),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2
                                )
                                # Gaze active when facing camera (yaw within 20 deg)
                                if abs(yaw) < 20.0:
                                    has_active_gaze = True
                except Exception as e:
                    print(f"[VideoIngest] MediaPipe error (skipping frame): {e}")

            # --- YOLO Person Detection & Tracking ---
            current_frame_tracks = set()
            try:
                # WHY classes=[0]: COCO class 0 = 'person'. Without this,
                # YOLO also tracks chairs, bags, bottles etc. We only want
                # to count real people in the retail zone.
                results = self.model.track(
                    frame, persist=True, verbose=False, classes=[0]
                )

                if results and results[0].boxes is not None:
                    for box in results[0].boxes:
                        coords = box.xyxy[0]
                        if hasattr(coords, "cpu"):
                            coords = coords.cpu().numpy()
                        x1, y1, x2, y2 = map(int, coords[:4])
                        track_id = (
                            int(box.id[0].item()) if box.id is not None else -1
                        )
                        if track_id == -1:
                            continue

                        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                        in_zone = is_inside_bbox((cx, cy), zone_bbox)

                        color = (0, 255, 0) if in_zone else (0, 165, 255)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        label = (
                            f"ID:{track_id} [ZONE]" if in_zone
                            else f"ID:{track_id}"
                        )
                        cv2.putText(
                            frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
                        )

                        if in_zone:
                            current_frame_tracks.add(track_id)
                            if track_id not in self.active_tracks:
                                self.active_tracks[track_id] = {
                                    "start_time": now,
                                    "last_seen": now,
                                    "gaze_frames": 1 if has_active_gaze else 0,
                                    "total_frames": 1
                                }
                            else:
                                self.active_tracks[track_id]["last_seen"] = now
                                self.active_tracks[track_id]["total_frames"] += 1
                                if has_active_gaze:
                                    self.active_tracks[track_id]["gaze_frames"] += 1

            except Exception as e:
                print(f"[VideoIngest] YOLO error (skipping frame): {e}")

            # --- Exit Detection: save to DB when person leaves zone ---
            # WHY 2 second grace period: if someone briefly steps out of
            # the bbox (leans to pick up a product), we don't close their
            # session immediately -- we give them 2 seconds to return.
            now = time.time()
            stale_ids = [
                tid for tid, data in self.active_tracks.items()
                if tid not in current_frame_tracks
                and (now - data["last_seen"]) > 2.0
            ]
            for tid in stale_ids:
                data = self.active_tracks.pop(tid)
                dwell_sec = data["last_seen"] - data["start_time"]
                if dwell_sec >= 1.5:
                    gaze_ratio = (
                        data["gaze_frames"] / max(data["total_frames"], 1)
                    )
                    gaze_sec = dwell_sec * gaze_ratio
                    score = min(
                        1.0,
                        (dwell_sec / 10.0) * 0.5 + gaze_ratio * 0.5
                    )
                    self._log_shopper_session(
                        track_id=tid,
                        zone_id=self.active_zone_id,
                        dwell_sec=dwell_sec,
                        gaze_sec=gaze_sec,
                        score=score
                    )

            # Store latest annotated frame for /api/video/stream
            ok, jpeg_buffer = cv2.imencode(".jpg", frame)
            with self._lock:
                self.frame_count += 1
                if ok:
                    self.latest_jpeg = jpeg_buffer.tobytes()
                self.latest_metadata = {
                    "frame_count": self.frame_count,
                    "resolution": f"{w}x{h}",
                    "timestamp": now,
                    "active_source": str(self.source),
                    "source_mode": self.source_mode,
                    "is_fallback_active": self.is_fallback_active,
                    "zone_id": self.active_zone_id,
                    "store_name": self.zone_config["store_name"],
                    "department": self.zone_config["department"],
                    "zone_name": self.zone_config["zone_name"],
                    "active_tracks_in_zone": len(self.active_tracks),
                }

        self._flush_active_tracks()
        if self.capture is not None:
            self.capture.release()
        print("[VideoIngest] Capture released. Thread stopping.")

    def _flush_active_tracks(self):
        """Save any in-progress sessions to DB when video loops or server stops."""
        now = time.time()
        for tid, data in list(self.active_tracks.items()):
            dwell_sec = now - data["start_time"]
            if dwell_sec >= 1.5:
                gaze_ratio = data["gaze_frames"] / max(data["total_frames"], 1)
                gaze_sec = dwell_sec * gaze_ratio
                score = min(1.0, (dwell_sec / 10.0) * 0.5 + gaze_ratio * 0.5)
                self._log_shopper_session(
                    track_id=tid,
                    zone_id=self.active_zone_id,
                    dwell_sec=dwell_sec,
                    gaze_sec=gaze_sec,
                    score=score
                )
        self.active_tracks.clear()

    def _log_shopper_session(
        self,
        track_id: int,
        zone_id: int,
        dwell_sec: float,
        gaze_sec: float,
        score: float
    ):
        if dwell_sec < 1.5:
            return

        # Calculate engagement score
        engagement_score = calculate_engagement_score(dwell_sec, gaze_sec)

        # Save to database
        db = SessionLocal()

        try:
            log_entry = ShopperDwellLog(
                track_id=track_id,
                zone_id=zone_id,
                store_name=self.zone_config.get("store_name"),
                department=self.zone_config.get("department"),
                zone_name=self.zone_config.get("zone_name"),
                source_mode=self.source_mode,
                enter_timestamp=datetime.now(timezone.utc),
                dwell_duration_sec=round(dwell_sec, 2),
                gaze_duration_sec=round(gaze_sec, 2),
                engagement_score=round(engagement_score, 2)
            )
            db.add(log_entry)
            db.commit()
            print(f"[DB LOG SUCCESS] Saved Track #{track_id} | Zone: {zone_id} | Dwell: {dwell_sec:.2f}s | Score: {engagement_score}")

        except Exception as e:
            db.rollback()
            print(f"[DB ERROR] Track#{track_id}: {e}")
        finally:
            db.close()

    def get_latest_jpeg(self) -> Optional[bytes]:
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