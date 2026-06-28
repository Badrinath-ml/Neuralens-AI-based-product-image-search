import cv2
import httpx
import os
import threading
import time
import numpy as np

# Global variables shared across threads
current_api_data = None
is_processing = False
running = False
is_active = False
lock = threading.Lock()

last_analysis_time = 0

# PRODUCTION HYBRID TRACKING STATES
tracked_box = None         # Active [x, y, w, h] coordinates
prev_roi_gray = None       # Previous grayscale snippet of the object for localized structural matching

def start_realtime_lens():
    global current_api_data, is_processing, running, last_analysis_time, tracked_box, prev_roi_gray, is_active
    with lock:
        if is_active:
            print("[WARNING] Realtime Lens is already active.")
            return False
        is_active = True
        running = True
        
    try:
        tracked_box = None
        prev_roi_gray = None
        last_analysis_time = 0
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[ERROR] Could not open webcam stream.")
            return

        window_name = "AI Product Lens - Live Stream Mode"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        print("[INFO] Production AR Lens Active! Hybrid Region-Locked Tracking Engaged.")

        while running:
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                running = False
                break

            ret, frame = cap.read()
            if not ret:
                break

            frame_height, frame_width, _ = frame.shape
            current_time = time.time()

            # 🎯 1. PRODUCTION STATE: BOUNDARY INITIALIZATION / OVERFLOW PROTECTION
            sidebar_w = int(frame_width * 0.32)
            bottom_h = int(frame_height * 0.20)
            max_track_width = frame_width - sidebar_w

            if tracked_box is None:
                # Cold-start target box focused in the live viewport center region
                tw, th = 220, 220
                tx = (max_track_width - tw) // 2
                ty = (frame_height - bottom_h - th) // 2
                tracked_box = [tx, ty, tw, th]
                prev_roi_gray = None

            # 🎯 2. LOCALIZED HYBRID OPTICAL DEFLECTION ENGINE
            bx, by, bw, bh = tracked_box
            
            # Ensure the active local tracking box coordinates stay within valid video stream boundaries
            bx = max(0, min(bx, max_track_width - bw))
            by = max(0, min(by, frame_height - bottom_h - bh))
            tracked_box = [bx, by, bw, bh]

            # Extract localized grayscale matrix slices to accurately pinpoint shifts
            roi = frame[by:by+bh, bx:bx+bw]
            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            roi_gray = cv2.GaussianBlur(roi_gray, (5, 5), 0)

            if prev_roi_gray is not None and prev_roi_gray.shape == roi_gray.shape:
                # Calculate pixel differences purely within the object's tracking area
                diff = cv2.absdiff(prev_roi_gray, roi_gray)
                _, thresh = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)
                
                # Isolate movement contours exclusively inside our tracking matrix bounds
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    # Find the center of mass of internal structural changes
                    large_contours = [c for c in contours if cv2.contourArea(c) > 50]
                    if large_contours:
                        # Combine coordinates to calculate a targeted directional vector shift
                        all_pts = np.vstack(large_contours)
                        mx, my, mw, mh = cv2.boundingRect(all_pts)
                        
                        # Compute vector offsets relative to the tracking bounding box center
                        cx_local = mx + mw // 2
                        cy_local = my + mh // 2
                        dx = cx_local - (bw // 2)
                        dy = cy_local - (bh // 2)
                        
                        # Apply linear relaxation smoothing to ignore background jitter
                        if abs(dx) > 4 or abs(dy) > 4:
                            tracked_box[0] = int(max(0, min(tracked_box[0] + dx * 0.25, max_track_width - bw)))
                            tracked_box[1] = int(max(0, min(tracked_box[1] + dy * 0.25, frame_height - bottom_h - bh)))

            # Update our tracking structural baseline for the next upcoming frame calculation
            # Re-extract slicing masks to prevent dimensional drift errors
            bx, by, bw, bh = tracked_box
            prev_roi = frame[by:by+bh, bx:bx+bw]
            prev_roi_gray = cv2.cvtColor(prev_roi, cv2.COLOR_BGR2GRAY)
            prev_roi_gray = cv2.GaussianBlur(prev_roi_gray, (5, 5), 0)

            # 🤖 3. ASYNC BACKGROUND AI COGNITION LAYER
            if not is_processing and (current_time - last_analysis_time) > 4.5:
                last_analysis_time = current_time
                is_processing = True

                # Encode the current frame to PNG bytes in memory (no disk write)
                success, buffer = cv2.imencode(".png", frame)
                if success:
                    image_bytes = buffer.tobytes()
                    worker = threading.Thread(
                        target=async_network_worker, args=(image_bytes, frame_width, frame_height)
                    )
                    worker.daemon = True
                    worker.start()
                else:
                    is_processing = False

            # 🎨 4. PAINT LIGHTWEIGHT HIGH-TECH HUD OVERLAYS
            with lock:
                draw_production_hud(frame, current_api_data, frame_width, frame_height)

            cv2.imshow(window_name, frame)

            if (cv2.waitKey(1) & 0xFF) == 27:  # Press ESC to cleanly shut down
                running = False
                break

        cap.release()
        cv2.destroyAllWindows()
    finally:
        with lock:
            is_active = False
            running = False


def async_network_worker(image_bytes: bytes, width: int, height: int):
    global current_api_data, is_processing, running, tracked_box, prev_roi_gray
    api_url = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1/ai/search/upload")

    if not running:
        is_processing = False
        return

    try:
        files = {"file": ("realtime_snapshot.png", image_bytes, "image/png")}
        response = httpx.post(api_url, files=files, timeout=15.0)

        if response.status_code in [200, 201] and running:
            new_data = response.json()
            with lock:
                current_api_data = new_data

                # Pull precise object coordinates from the API return, safely handling None values
                box_data = new_data.get("bounding_box") or {"ymin": 250, "xmin": 200, "ymax": 750, "xmax": 600}
                sidebar_w = int(width * 0.32)
                max_track_width = width - sidebar_w

                ymin = int((box_data["ymin"] / 1000) * height)
                xmin = int((box_data["xmin"] / 1000) * width)
                ymax = int((box_data["ymax"] / 1000) * height)
                xmax = int((box_data["xmax"] / 1000) * width)

                # Snap the tracking box directly to the validated object borders
                target_w = max(xmax - xmin, 50)
                target_h = max(ymax - ymin, 50)
                target_x = max(0, min(xmin, max_track_width - target_w))
                target_y = max(0, min(ymin, height - int(height * 0.20) - target_h))

                tracked_box = [target_x, target_y, target_w, target_h]
                prev_roi_gray = None  # Force tracking refresh on next loop step
    except Exception:
        pass
    finally:
        is_processing = False


def draw_production_hud(frame, data, width, height):
    global tracked_box
    
    sidebar_w = int(width * 0.32)
    bottom_h = int(height * 0.20)

    # 🔴 1. RENDER AR INTERACTION LOCK-ON FRAME
    if tracked_box is not None:
        bx, by, bw, bh = tracked_box
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 0, 255), 2)
        
        # High-end futuristic camera crosshair bracket marks
        d = 14
        cv2.line(frame, (bx, by), (bx + d, by), (0, 255, 255), 2)
        cv2.line(frame, (bx, by), (bx, by + d), (0, 255, 255), 2)
        cv2.line(frame, (bx+bw, by), (bx+bw - d, by), (0, 255, 255), 2)
        cv2.line(frame, (bx+bw, by), (bx+bw, by + d), (0, 255, 255), 2)
        cv2.line(frame, (bx, by+bh), (bx + d, by+bh), (0, 255, 255), 2)
        cv2.line(frame, (bx, by+bh), (bx, by+bh - d), (0, 255, 255), 2)
        cv2.line(frame, (bx+bw, by+bh), (bx+bw - d, by+bh), (0, 255, 255), 2)
        cv2.line(frame, (bx+bw, by+bh), (bx+bw, by+bh - d), (0, 255, 255), 2)
        
        if data:
            label = f"{data.get('brand', '')} {data.get('model_name', 'Product')}"
            cv2.putText(frame, label, (bx, by - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
        else:
            cv2.putText(frame, "HYBRID LOCK", (bx, by - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1, cv2.LINE_AA)

    # 🌆 2. TRANSLUCENT PREMIUM HUD COATING LAYERS
    hud_overlay = frame.copy()
    cv2.rectangle(hud_overlay, (width - sidebar_w, 0), (width, height), (15, 12, 10), -1)
    cv2.rectangle(hud_overlay, (0, height - bottom_h), (width - sidebar_w, height), (10, 10, 10), -1)
    cv2.addWeighted(hud_overlay, 0.65, frame, 0.35, 0, frame)

    cv2.line(frame, (width - sidebar_w, 0), (width - sidebar_w, height), (60, 60, 60), 1)
    cv2.line(frame, (0, height - bottom_h), (width - sidebar_w, height - bottom_h), (60, 60, 60), 1)

    # 📊 3. POPULATE HUD DATA METRICS
    cv2.putText(frame, "SYSTEM ENGINE READOUT", (width - sidebar_w + 20, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
    
    if data:
        details = [
            f"Brand: {data.get('brand', 'N/A')}",
            f"Model: {data.get('model_name', 'N/A')}",
            f"Color: {data.get('color', 'N/A')}",
        ]
        y = 80
        for detail in details:
            cv2.putText(frame, detail, (width - sidebar_w + 20, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            y += 28

        cv2.putText(frame, "SPECIFICATION MATRIX:", (width - sidebar_w + 20, y + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
        
        y += 40
        for spec in data.get("specification", [])[:3]:
            cv2.putText(frame, f"- {spec[:24]}", (width - sidebar_w + 20, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1, cv2.LINE_AA)
            y += 22
            
        desc_text = data.get("description", "Awaiting narrative payload...")
    else:
        cv2.putText(frame, "Calibrating targets...", (width - sidebar_w + 20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (140, 140, 140), 1, cv2.LINE_AA)
        desc_text = "Analyzing frame environment... calibrating automated computer vision engine tracking framework targets."

    # 📝 4. RENDER MULTI-LINE SUMMARY NARRATIVE WITH WRAPPING
    cv2.putText(frame, "AI MODEL ANALYSIS NARRATIVE:", (20, height - bottom_h + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
    
    words = desc_text.replace("Gemini", "AI Model").split(" ")
    lines = []
    current_line = ""
    max_chars = int((width - sidebar_w - 40) / 6.5)
    
    for word in words:
        if len(current_line + word) < max_chars:
            current_line += word + " "
        else:
            lines.append(current_line)
            current_line = word + " "
    lines.append(current_line)

    dy = height - bottom_h + 50
    for line in lines[:2]:
        cv2.putText(frame, line.strip(), (20, dy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (220, 220, 220), 1, cv2.LINE_AA)
        dy += 20

    # Sync pulse activity dots
    status_color = (0, 255, 255) if is_processing else (0, 255, 0)
    cv2.circle(frame, (width - sidebar_w + 25, height - 25), 5, status_color, -1)
    status_label = "AI THINKING..." if is_processing else "AI SYNCED"
    cv2.putText(frame, status_label, (width - sidebar_w + 40, height - 21),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1, cv2.LINE_AA)


if __name__ == "__main__":
    start_realtime_lens()