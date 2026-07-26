import cv2
import threading
import time

def calculate_box_center(x: int, y: int, width: int, height: int) -> tuple[int, int]:
    """Computes spatial center point (X, Y) of a bounding box."""
    return int(x + (width / 2)), int(y + (height / 2))


class ThreadedVideoIngest:
    # 1. LOCAL ASSET REGISTRY (Sub-choices for local video mode)
    LOCAL_ASSETS = {
        "grocery": "app/assets/grocery_dwell.mp4",
        "electronics": "app/assets/electronics_display.mp4",
        "apparel": "app/assets/apparel_checkout.mp4"
    }

    # Map local sub-choices to their default store IDs
    LOCAL_STORE_MAP = {
        "grocery": 101,
        "electronics": 102,
        "apparel": 103
    }

    # 2. DYNAMIC SPATIAL PARAMETERS (Per Store/Camera ID)
    # In production, these boundaries are fetched from PostgreSQL via FastAPI
    SPATIAL_PARAMS_DB = {
        101: {
            "name": "Grocery Beverage Aisle",
            "resolution": "1920x1080",
            "shelf_zone": {"x_min": 100, "y_min": 100, "x_max": 500, "y_max": 900}
        },
        102: {
            "name": "Electronics High-Value Shelf",
            "resolution": "1920x1080",
            "shelf_zone": {"x_min": 300, "y_min": 200, "x_max": 800, "y_max": 700}
        },
        103: {
            "name": "Apparel Checkout Queue",
            "resolution": "1920x1080",
            "shelf_zone": {"x_min": 50, "y_min": 300, "x_max": 600, "y_max": 1000}
        },
        201: {
            "name": "Overhead Ceiling CCTV (Live RTSP Stream)",
            "resolution": "2560x1440",
            "shelf_zone": {"x_min": 800, "y_min": 400, "x_max": 1800, "y_max": 1200}
        },
        999: {
            "name": "Desk Testing Webcam Sandbox",
            "resolution": "640x480",
            "shelf_zone": {"x_min": 20, "y_min": 50, "x_max": 300, "y_max": 400}
        }
    }

    def __init__(self, mode: str = "local", sub_choice: str = "grocery", rtsp_url: str = "", store_id: int = 0):
        """
        Handles dynamic ingestion binding based on user choices:
        - mode: 'local', 'webcam', or 'live_stream'
        - sub_choice: 'grocery', 'electronics', or 'apparel' (Used when mode='local')
        - rtsp_url: Custom RTSP address string (Used when mode='live_stream')
        - store_id: Optional explicit store override
        """
        self.mode = mode.lower()
        self.sub_choice = sub_choice.lower()

        # Resolve source and store_id based on user selections
        if self.mode == "webcam":
            self.source = 0
            self.store_id = store_id if store_id else 999

        elif self.mode == "live_stream":
            self.source = rtsp_url if rtsp_url else "rtsp://admin:password@192.168.1.50:554/live"
            self.store_id = store_id if store_id else 201

        elif self.mode == "local":
            # Map selected sub-choice (grocery, electronics, apparel)
            self.source = self.LOCAL_ASSETS.get(self.sub_choice, self.LOCAL_ASSETS["grocery"])
            self.store_id = store_id if store_id else self.LOCAL_STORE_MAP.get(self.sub_choice, 101)

        else:
            raise ValueError(f"Invalid mode '{mode}'. Choose from: 'local', 'webcam', 'live_stream'")

        # Fetch spatial parameters matching resolved store_id
        self.active_spatial_zones = self._get_spatial_zones_for_store(self.store_id)

        self.cap = None
        self.is_running = False
        self.thread = None
        self.fallback_source = "app/assets/grocery_dwell.mp4"

    def _get_spatial_zones_for_store(self, store_id: int) -> dict:
        """Retrieves spatial boundary parameters for the active store_id."""
        return self.SPATIAL_PARAMS_DB.get(store_id, self.SPATIAL_PARAMS_DB[101])

    def start_processing(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def _capture_loop(self):
        self.cap = cv2.VideoCapture(self.source)

        # FAULT-TOLERANT FAILOVER
        if not self.cap.isOpened():
            print(f"\n[WARN] Source '{self.source}' unavailable or unreachable!")
            print("[WARN] Activating Enterprise Fault-Tolerant Failover Engine...")
            self.source = self.fallback_source
            self.store_id = 101
            self.active_spatial_zones = self._get_spatial_zones_for_store(101)
            self.cap = cv2.VideoCapture(self.source)

        print(f"\n[OPENCV] Active Pipeline Running | Mode: {self.mode.upper()} | Source: {self.source}")
        print(f"[SPATIAL SETUP] Store ID: {self.store_id} | Zone: {self.active_spatial_zones['name']}")
        print(f"[SPATIAL BOUNDS] Resolution: {self.active_spatial_zones['resolution']} | Coordinates: {self.active_spatial_zones['shelf_zone']}\n")

        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                if isinstance(self.source, str) and ("mp4" in self.source or "assets" in self.source):
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                time.sleep(0.03)
                continue

            current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))

            # Simulated detection bounding box [x, y, w, h]
            sample_bbox = (150, 200, 100, 300)
            center_x, center_y = calculate_box_center(*sample_bbox)

            # 1. DRAW VISUAL FEEDBACK ON FRAME
            cv2.rectangle(frame, (150, 200), (250, 500), (0, 255, 0), 2)
            cv2.circle(frame, (center_x, center_y), 6, (0, 0, 255), -1)
            cv2.putText(frame, f"Center: ({center_x}, {center_y})", (150, 180),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # 2. POP UP LIVE CAMERA WINDOW
            try:
                cv2.imshow(f"Live Ingest - Mode: {self.mode.upper()}", frame)

                # Press 'q' to close the visual window safely
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.is_running = False
                    break
            except cv2.error:
                pass  # Handle cases where the window cannot be displayed (e.g., headless environments)

            # Processing simulated telemetry every 60 frames
            if current_frame % 60 == 0:
                zone = self.active_spatial_zones['shelf_zone']
                is_inside = (zone['x_min'] <= center_x <= zone['x_max']) and (zone['y_min'] <= center_y <= zone['y_max'])

                print(f"[ANALYTICS] Store ID: {self.store_id} ({self.active_spatial_zones['name']}) | Frame: {current_frame}")
                print(f"            Computed Center: ({center_x}, {center_y})")
                print(f"            Inside Monitored Zone? -> {is_inside}\n")

            time.sleep(0.03)

        # Clean up OpenCV windows when loop stops
        self.cap.release()
        cv2.destroyAllWindows()


# ==========================================
# INTERACTIVE CLI DEMO MENU
# ==========================================
if __name__ == "__main__":
    print("===========================================")
    print(" CONSUMER ATTENTION MAPPING - VIDEO INGEST ")
    print("===========================================")
    print("Select Stream Input Mode:")
    print(" 1. Local Video File")
    print(" 2. Live Webcam")
    print(" 3. RTSP Live Stream")

    mode_choice = input("\nEnter choice (1-3) [Default=1]: ").strip()

    if mode_choice == "2":
        ingest = ThreadedVideoIngest(mode="webcam")
    elif mode_choice == "3":
        rtsp = input("Enter RTSP Stream URL (Press Enter for default): ").strip()
        ingest = ThreadedVideoIngest(mode="live_stream", rtsp_url=rtsp if rtsp else "")
    else:
        print("\nSelect Local Video Sub-Choice:")
        print(" a. Grocery Aisle (grocery)")
        print(" b. Electronics Shelf (electronics)")
        print(" c. Apparel Checkout (apparel)")
        sub = input("Enter sub-choice (a/b/c) [Default=a]: ").strip().lower()

        sub_map = {"a": "grocery", "b": "electronics", "c": "apparel"}
        selected_sub = sub_map.get(sub, "grocery")

        ingest = ThreadedVideoIngest(mode="local", sub_choice=selected_sub)

    # Start ingestion thread
    ingest.start_processing()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Stopping Video Ingestion Engine.")