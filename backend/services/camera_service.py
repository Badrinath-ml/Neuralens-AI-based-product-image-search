import cv2
import httpx
import os
import threading


class CameraService:
    def __init__(self):
        # Consistent window name matching OS requirements
        self.window_name = "AI Product Lens - Camera Mode"

        # Thread safety control configurations
        self.is_active = False
        self._lock = threading.Lock()

    def start_lens_camera(self):
        """
        Opens the camera viewfinder interface.
        Press [SPACEBAR] to snap and send, or [ESC] to quit.

        Frames are encoded to PNG bytes in memory via cv2.imencode — no files
        are written to disk, making this safe on read-only cloud filesystems.
        """
        with self._lock:
            if self.is_active:
                print("[WARNING] Camera interface is already active.")
                return False
            self.is_active = True

        try:
            # 0 initialises the standard local webcam thread hardware
            cap = cv2.VideoCapture(0)

            if not cap.isOpened():
                print("[ERROR] Could not access or open webcam device hardware.")
                return

            print("\n[INFO] AI Lens Viewfinder Active... Position your product in frame.")
            print("[INFO] Press [SPACEBAR] to Capture | Press [ESC] to Abort Window.\n")

            while True:
                ret, frame = cap.read()
                if not ret:
                    print("[ERROR] Failed to safely fetch active frame matrix sequence.")
                    break

                # Create an isolated text overlay layer to keep the snapshot pristine
                display_frame = frame.copy()
                cv2.putText(display_frame, "AI Image Search: Press SPACEBAR to Capture", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
                cv2.putText(display_frame, "Press ESC to Quit", (20, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

                cv2.imshow(self.window_name, display_frame)

                key = cv2.waitKey(1) & 0xFF

                # ESC key — close window safely
                if key == 27:
                    print("[INFO] Viewfinder interface closed by user choice.")
                    break

                # SPACEBAR — encode frame to memory and dispatch to API
                elif key == 32:
                    # Encode the pristine raw frame (no overlay text) to PNG bytes in memory
                    success, buffer = cv2.imencode(".png", frame)
                    if not success:
                        print("[ERROR] Failed to encode frame to PNG bytes.")
                        continue

                    image_bytes = buffer.tobytes()
                    print("[INFO] Frame encoded in memory (no disk write).")
                    print("[INFO] Dispatching payload to AI pipeline router...")

                    # Release hardware BEFORE the blocking network call
                    cap.release()
                    cv2.destroyAllWindows()

                    self.upload_snapshot_to_api(image_bytes)
                    return

            # Fallback cleanup if user hits ESC
            cap.release()
            cv2.destroyAllWindows()
        finally:
            with self._lock:
                self.is_active = False

    def upload_snapshot_to_api(self, image_bytes: bytes) -> None:
        """
        POST raw PNG bytes directly to the FastAPI backend via multipart form-data.
        No intermediate file is written — works on read-only cloud filesystems.
        """
        api_url = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1/ai/search/upload")

        try:
            files = {"file": ("snapshot.png", image_bytes, "image/png")}
            timeout = httpx.Timeout(30.0, connect=10.0)
            response = httpx.post(api_url, files=files, timeout=timeout)

            if response.status_code in [200, 201]:
                result = response.json()
                print("\n[AI LENS SUCCESS] Product analysis complete!")
                print(f" - Product ID Created: {result.get('id', 'N/A')}")
                print(f" - Optimized Search Term: '{result.get('search_query', 'N/A')}'")
                print(f"\n[INFO] Next Step: Call `/api/v1/ai/search/results/{result.get('id')}` to view listings.\n")
            else:
                print(f"[ERROR] Server Error Pipeline ({response.status_code}): {response.text}")

        except httpx.ConnectError:
            print("\n[ERROR] Connectivity Fault: Could not reach backend gateway. Is your server active on port 8000?")
        except Exception as e:
            print(f"\n[ERROR] Failed to execute network routing cycle: {str(e)}")


# Module-level instance
cam_mode = CameraService()

if __name__ == "__main__":
    cam_mode.start_lens_camera()