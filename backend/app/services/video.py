import cv2
import time
import threading

class ThreadedVideoIngest:
    """
    Asynchronous, decoupled OpenCV ingest mechanism built to process high-throughput
    video channels safely without causing threading blockages on our async API cores.
    """
    def __init__(self, source: str = "0"):
        self.source = int(source) if source.isdigit() else source
        self.cap = cv2.VideoCapture(self.source)
        self.running = False
        self.frame_count = 0

    def start_processing(self):
        if not self.cap.isOpened():
            print(f"[ERROR] Failed to tap data connection on: {self.source}")
            return False

        self.running = True
        self.thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.thread.start()
        print(f"[OK] Spun async analytics extraction pipeline thread for stream target.")
        return True

    def _stream_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                print("[INFO] Video pipeline terminated or buffer stream dropped.")
                self.running = False
                break

            self.frame_count += 1

            # Isolated Down-scaling Frame Footprint to conserve low system RAM
            optimized_frame = cv2.resize(frame, (640, 480))

            if self.frame_count % 30 == 0:
                print(f"[ANALYTICS ENGINE METADATA] Frame Index: {self.frame_count} | Epoch Tracking: {time.time()} | Ingest Resolution: {optimized_frame.shape}")

            # Internal safety circuit breaker during milestone testing
            if self.frame_count >= 300:
                print("[INFO] Ingestion benchmark criteria satisfied safely.")
                self.running = False

        self.cap.release()

    def stop_processing(self):
        self.running = False