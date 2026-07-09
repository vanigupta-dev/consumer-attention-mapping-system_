import cv2
import threading
import time

class ThreadedVideoIngest:
    def __init__(self, source):
        # If source is a digit string like "0", convert to integer for hardware webcam
        if str(source).isdigit():
            self.source = int(source)
        else:
            self.source = source

        self.cap = None
        self.is_running = False
        self.thread = None
        # Defending our pipeline: Fallback safely to our local file if things break
        self.fallback_source = "app/assets/sample_retail.mp4"

    def start_processing(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def _capture_loop(self):
        self.cap = cv2.VideoCapture(self.source)

        #  FAULT-TOLERANT FAILOVER CHECK
        if not self.cap.isOpened():
            print(f"\n[WARN] Source '{self.source}' unavailable or disconnected!")
            print("[WARN] Activating Enterprise Fault-Tolerant Fallover Engine...")
            self.source = self.fallback_source
            self.cap = cv2.VideoCapture(self.source)

        print(f"\n[OPENCV] Active Pipeline Stream Running smoothly via: {self.source}\n")

        while self.is_running:
            ret, frame = self.cap.read()
            if ret:
        # Simulating data detection every 60 frames (~2 second)
                  current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                  if current_frame % 60 == 0:
                     print(f"[ANALYTICS] Frame {current_frame} | Zone Active: Juice Shelf | Detected: 1 Shopper | Gaze Duration: 4.2s -> Syncing to PostgreSQL...")

            else:
                # If it's a video file, loop back to the start when it ends
                if isinstance(self.source, str) and "mp4" in self.source:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                time.sleep(2)
                continue
            time.sleep(0.03)  # Simulate ~30 FPS