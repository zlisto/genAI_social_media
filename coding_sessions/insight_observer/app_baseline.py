import streamlit as st
import cv2
import os
import glob
import time
import sys
from datetime import datetime

# --- CONFIG ---
IMAGES_DIR = "images"
MAX_IMAGES = 20
CAPTURE_INTERVAL_SECONDS = 5  # Seconds between captures

# Create images directory if it doesn't exist
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

def clear_images():
    files = glob.glob(os.path.join(IMAGES_DIR, "*.png"))
    for f in files:
        os.remove(f)
        

def log_event(message: str) -> None:
    # Print to the Streamlit server terminal (stdout).
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {message}", flush=True)

# --- STREAMLIT UI ---
st.set_page_config(page_title="Camera Test", layout="wide")
st.title("Camera Test")

# Initialize session state (reset count to 0 when app loads)
if "img_count" not in st.session_state:
    st.session_state.img_count = 0
if "camera_active" not in st.session_state:
    st.session_state.camera_active = False

col1, col2 = st.columns(2)

with col1:
    run_camera = st.toggle("Turn on Camera", key="run_camera")

    # Log toggle changes (prints to the terminal)
    if "last_run_camera" not in st.session_state:
        st.session_state.last_run_camera = run_camera
    elif st.session_state.last_run_camera != run_camera:
        log_event(f"Camera toggled to {run_camera}")
        st.session_state.last_run_camera = run_camera
        st.session_state.camera_active = run_camera

# Update camera active state
st.session_state.camera_active = run_camera

with col2:
    st.write(f"Images Captured: {st.session_state.img_count} / {MAX_IMAGES}")

# Camera capture logic
status_placeholder = st.empty()
image_placeholder = st.empty()

if st.session_state.camera_active:
    # Cross-platform camera selection
    if sys.platform == "win32":
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        status_placeholder.error("Could not access the webcam.")
        log_event("ERROR: Could not access the webcam.")
        st.session_state.camera_active = False
    else:
        ret, frame = cap.read()
        if not ret or frame is None:
            status_placeholder.error("Could not read from webcam.")
            log_event("ERROR: Could not read from webcam.")
            st.session_state.camera_active = False
        else:
            # Increment counter and save image
            st.session_state.img_count += 1
            img_filename = f"screen_shot_{st.session_state.img_count:02d}.png"
            img_path = os.path.join(IMAGES_DIR, img_filename)

            ok = cv2.imwrite(img_path, frame)
            if ok:
                status_placeholder.success(f"Captured {img_filename}")
                log_event(f"Saved image: {img_filename} ({img_path})")
                
                # Display the saved image (convert BGR to RGB for display)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image_placeholder.image(frame_rgb, caption=f"Latest: {img_filename}", width=400)
            else:
                status_placeholder.error(f"Failed to save {img_filename}")
                log_event(f"ERROR: Failed to save image: {img_filename} ({img_path})")
                st.session_state.camera_active = False
            
            # Check if max images reached
            if st.session_state.img_count >= MAX_IMAGES:
                status_placeholder.warning("Max images reached.")
                log_event(f"Max images reached ({MAX_IMAGES}).")
                st.session_state.camera_active = False
            else:
                # Continue capturing if camera is still active
                if st.session_state.camera_active:
                    time.sleep(CAPTURE_INTERVAL_SECONDS)
                    st.rerun()
        
        cap.release()
else:
    status_placeholder.info("Camera is OFF. Toggle to start capturing images.")
    
    # Show the latest saved image if available
    image_files = glob.glob(os.path.join(IMAGES_DIR, "*.png"))
    if image_files:
        # Get the most recently modified image
        latest_image = max(image_files, key=os.path.getmtime)
        image_placeholder.image(latest_image, caption=f"Latest: {os.path.basename(latest_image)}", width=400)
    else:
        image_placeholder.info("No images captured yet.")

