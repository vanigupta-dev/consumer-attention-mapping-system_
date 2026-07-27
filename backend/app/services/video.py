import cv2
import time
import numpy as np
from typing import Dict, Any, Tuple
from ultralytics import YOLO
import mediapipe as mp

# MediaPipe Setup
mp_face_mesh = mp.solutions.face_mesh

SPATIAL_PARAMS_DB = {
    101: {
        "store_name": "Electronics Dept",
        "zone_name": "Premium Displays",
        "zone_bbox": (100, 100, 500, 400)
    }
}

# Standard 3D model points for Head Pose (in mm)
MODEL_POINTS_3D = np.array([
    (0.0, 0.0, 0.0),             # Nose tip
    (0.0, -330.0, -65.0),        # Chin
    (-225.0, 170.0, -135.0),     # Left eye left corner
    (225.0, 170.0, -135.0),      # Right eye right corner
    (-150.0, -150.0, -125.0),    # Left Mouth corner
    (150.0, -150.0, -125.0)      # Right mouth corner
], dtype=np.float64)


class ShopperTrackerEngine:
    def __init__(self, model_size: str = "yolov8n.pt", store_id: int = 101):
        self.store_id = store_id
        self.spatial_config = SPATIAL_PARAMS_DB.get(store_id, {})

        # 1. Load YOLOv8 Model
        print(f"[INFO] Loading YOLOv8 model ({model_size})...")
        self.model = YOLO(model_size)

        # 2. Load MediaPipe Face Mesh
        self.face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        self.active_shopper_dwells: Dict[int, Dict[str, Any]] = {}

    def is_inside_zone(self, center_x: int, center_y: int, zone_bbox: Tuple[int, int, int, int]) -> bool:
        x_min, y_min, x_max, y_max = zone_bbox
        return x_min <= center_x <= x_max and y_min <= center_y <= y_max

    def estimate_head_pose(self, head_crop) -> str:
        """Runs MediaPipe Face Mesh and returns estimated orientation string (Forward, Left, Right)."""
        h, w, _ = head_crop.shape
        if h < 20 or w < 20:
            return "Unknown"

        rgb_crop = cv2.cvtColor(head_crop, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_crop)

        if not results.multi_face_landmarks:
            return "No Face Detected"

        landmarks = results.multi_face_landmarks[0].landmark

        # Select 2D landmark points matching 3D model
        landmark_indices = [1, 152, 33, 263, 61, 291]
        image_points_2d = np.array([
            (landmarks[idx].x * w, landmarks[idx].y * h)
            for idx in landmark_indices
        ], dtype=np.float64)

        # Camera Intrinsic matrix approximation
        focal_length = w
        center = (w / 2, h / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)

        dist_coeffs = np.zeros((4, 1)) # Assuming zero lens distortion

        # Solve PnP
        success, rotation_vector, translation_vector = cv2.solvePnP(
            MODEL_POINTS_3D, image_points_2d, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not success:
            return "Unknown"

        # Convert Rotation Vector to Euler Angles
        rmat, _ = cv2.Rodrigues(rotation_vector)
        angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
        yaw = angles[1] # Y-axis rotation (Left/Right look)

        if yaw > 12:
            return "Looking Right"
        elif yaw < -12:
            return "Looking Left"
        else:
            return "Looking Forward"

    def process_frame(self, frame):
        results = self.model.track(
            source=frame,
            persist=True,
            classes=[0], # Class 0 = Person
            tracker="bytetrack.yaml",
            verbose=False
        )

        zone_bbox = self.spatial_config.get("zone_bbox")
        zone_name = self.spatial_config.get("zone_name", "Unknown Zone")

        # Draw Zone Boundary
        if zone_bbox:
            cv2.rectangle(frame, (zone_bbox[0], zone_bbox[1]), (zone_bbox[2], zone_bbox[3]), (255, 0, 0), 2)

        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.numpy()
            track_ids = results[0].boxes.id.numpy().astype(int)

            for box, track_id in zip(boxes, track_ids):
                x1, y1, x2, y2 = map(int, box)

                # Spatial Center Calculation
                center_x, center_y = int((x1 + x2) / 2), int((y1 + y2) / 2)
                in_zone = self.is_inside_zone(center_x, center_y, zone_bbox) if zone_bbox else False
                color = (0, 0, 255) if in_zone else (0, 255, 0)

                # --- TASK 3: Crop Upper Bounding Box (Head) & Estimate Gaze ---
                head_height = max(10, int((y2 - y1) * 0.35)) # Top 35% of box
                head_crop = frame[max(0, y1):max(0, y1 + head_height), max(0, x1):max(0, x2)]

                gaze_direction = "Unknown"
                if head_crop.size > 0:
                    gaze_direction = self.estimate_head_pose(head_crop)

                # Visual Overlay
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"Shopper #{track_id} [{gaze_direction}]",
                            (x1, max(15, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                # Dwell Time Logging
                if in_zone:
                    if track_id not in self.active_shopper_dwells:
                        self.active_shopper_dwells[track_id] = {"entry_time": time.time()}
                        print(f"[TRIGGER] Shopper #{track_id} ENTERED zone: {zone_name}")
                    else:
                        dwell_time = round(time.time() - self.active_shopper_dwells[track_id]["entry_time"], 1)
                        cv2.putText(frame, f"Dwell: {dwell_time}s", (x1, y2 + 20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        return frame

def run_pipeline(source=0, store_id=101):
    cap = cv2.VideoCapture(source)
    engine = ShopperTrackerEngine(store_id=store_id)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        processed_frame = engine.process_frame(frame)

        try:
            cv2.imshow("Milestone 2 - Shopper & Gaze Ingest Engine", processed_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        except cv2.error:
            pass

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_pipeline(source=0, store_id=101)