import cv2
import time
import numpy as np
from typing import Dict, Any, Tuple
from ultralytics import YOLO

# Convenience alias for MediaPipe Face Mesh solution
from mediapipe.solutions import face_mesh as mp_face_mesh # type: ignore

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
    # Selected facial landmark indices corresponding to 3D model points
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


def process_video_stream(video_source: Any = 0):
    """Main execution loop for YOLO tracking + MediaPipe Attention Mapping."""
    model = YOLO("yolov8n.pt")
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=5,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    cap = cv2.VideoCapture(video_source)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Run YOLO detection & tracking
        results = model.track(frame, persist=True, verbose=False)

        if results and len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes

            for box in boxes:
                # Safe handling for bounding box tensor vs numpy array
                coords = box.xyxy[0]
                if hasattr(coords, "cpu"):
                    coords = coords.cpu().numpy()

                x1, y1, x2, y2 = map(int, coords[:4])

                # Get track ID safely if available
                track_id = int(box.id[0].item()) if box.id is not None else -1

                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    f"ID: {track_id}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

        # Run MediaPipe Face Mesh on RGB frame
        mesh_results: Any = face_mesh.process(rgb_frame)
        if mesh_results is not None and getattr(mesh_results, "multi_face_landmarks", None):
            for face_landmarks in mesh_results.multi_face_landmarks:
                pitch, yaw = estimate_head_pose(face_landmarks.landmark, w, h)
                if pitch is not None and yaw is not None:
                    cv2.putText(
                        frame,
                        f"Pitch: {pitch:.1f}, Yaw: {yaw:.1f}",
                        (30, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 255, 0),
                        2
                    )

        cv2.imshow("Consumer Attention Mapping Pipeline", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    process_video_stream()