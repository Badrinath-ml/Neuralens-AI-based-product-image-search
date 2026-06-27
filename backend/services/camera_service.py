import cv2
import httpx
import os
import threading
from pathlib import Path

class CameraService:
    def __init__(self):
        # Establish a clean, dedicated local media directory structure
        self.base_dir = Path(__file__).resolve().parent.parent
        self.storage_dir = self.base_dir / "media_storage" / "snapshots"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Consistent window name matching OS requirements
        self.window_name = "AI Product Lens - Camera Mode"
        
        # Thread safety control configurations
        self.is_active = False
        self._lock = threading.Lock()

    def start_lens_camera(self):
        """
        Opens the camera viewfinder interface. 
        Press [SPACEBAR] to snap and send, or [ESC] to quit.
        """
        with self._lock:
            if self.is_active:
                print("[WARNING] Camera interface is already active.")
                return False
            self.is_active = True

        try:
            # 0 initializes the standard local webcam thread hardware
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

                # Create an isolated text overlay layer to keep the original snapshot pristine
                display_frame = frame.copy()
                cv2.putText(display_frame, "AI Image Search: Press SPACEBAR to Capture", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
                cv2.putText(display_frame, "Press ESC to Quit", (20, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
                
                cv2.imshow(self.window_name, display_frame)

                key = cv2.waitKey(1) & 0xFF
                
                # ESC key pressed to close window safely
                if key == 27:
                    print("[INFO] Viewfinder interface closed by user choice.")
                    break
                    
                # SPACEBAR pressed to capture frame and execute backend lookup
                elif key == 32:
                    img_path = str(self.storage_dir / "lens_capture.png")
                    
                    # Write the pristine raw frame without the green instruction labels baked onto it
                    cv2.imwrite(img_path, frame)
                    print(f"[INFO] Snapshot saved locally to: {img_path}")
                    print("[INFO] Dispatching background payload to AI pipeline router...")
                    
                    # CRITICAL: Cleanly release hardware thread assets BEFORE executing the network call
                    cap.release()
                    cv2.destroyAllWindows()
                    
                    # Pass file off to the endpoint
                    self.upload_snapshot_to_api(img_path)
                    return

            # Fallback resource collection cleanup block if user hits ESC
            cap.release()
            cv2.destroyAllWindows()
        finally:
            with self._lock:
                self.is_active = False

    def upload_snapshot_to_api(self, file_path: str):
        """
        Handles file upload to the running FastAPI backend router.
        """
        api_url = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1/ai/search/upload")
        
        if not os.path.exists(file_path):
            print(f"[ERROR] Targeted image file pointer missing: {file_path}")
            return

        # Open the file inside an HTTP network client context
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "image/png")}
                
                timeout = httpx.Timeout(30.0, connect=10.0)
                response = httpx.post(api_url, files=files, timeout=timeout)
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    print("\n[AI LENS SUCCESS] Product analysis complete!")
                    print(f" - Product ID Created: {result.get('id', 'N/A')}")
                    print(f" - Optimized Search Term: '{result.get('search_query', 'N/A')}'")
                    print(f"\n[INFO] Next Step: Call your `/api/v1/ai/search/results/{result.get('id')}` endpoint to view listings.\n")
                else:
                    print(f"[ERROR] Server Error Pipeline ({response.status_code}): {response.text}")
                    
        except httpx.ConnectError:
            print("\n[ERROR] Connectivity Fault: Could not reach backend gateway. Is your server active on port 8000?")
        except Exception as e:
            print(f"\n[ERROR] Failed to execute network routing cycle: {str(e)}")

# Instantiate instance using modern PEP-8 namespace casing
cam_mode = CameraService()

if __name__ == "__main__":
    cam_mode.start_lens_camera()