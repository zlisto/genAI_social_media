import streamlit as st
from streamlit_webrtc import webrtc_streamer

st.set_page_config(page_title="Pro Webcam Stream", layout="centered")

# --- Title and device name box ---
title_placeholder = st.empty()
title_placeholder.title("Smooth WebRTC Stream")
device_name_box = st.empty()

# 1. Initialize WebRTC
ctx = webrtc_streamer(
    key="snapshot",
    media_stream_constraints={
        "video": {
            "width": {"ideal": 640},
            "height": {"ideal": 480},
            "frameRate": {"ideal": 30}
        },
        "audio": False,
    },
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
)

# 2. Capture Logic and Device Name Retrieval
# Track stream state so we only print to terminal when it changes
if "_stream_connected" not in st.session_state:
    st.session_state._stream_connected = False

if ctx.video_receiver:
    # Show the selected device name in a box (from the track label after Start)
    device_label = None
    try:
        track = ctx.video_receiver.get_track()
        if track and getattr(track, "label", None):
            device_label = track.label
    except Exception:
        pass

    if not st.session_state._stream_connected:
        st.session_state._stream_connected = True
        name = device_label or "(device name pending)"
        print(f"[Webcam] Stream connected — using device: {name}")

    if device_label:
        device_name_box.info(f"**Using device:** {device_label}")
    else:
        device_name_box.info("**Using device:** (starting stream…)")

    if st.button("📸 Take Snapshot for AI"):
        try:
            # Pull the most recent frame
            frame = ctx.video_receiver.get_frame()
            img = frame.to_ndarray(format="bgr24")
            # BGR → RGB for Streamlit (no cv2 — works on Windows & Mac)
            img_rgb = img[:, :, ::-1]
            
            st.subheader("Captured Image")
            st.image(img_rgb, caption="Snapshot from Live Feed", use_container_width=True)
            st.success("Image successfully captured!")
            
        except Exception as e:
            st.error(f"Waiting for video to start... ({e})")
else:
    if st.session_state._stream_connected:
        st.session_state._stream_connected = False
        print("[Webcam] Stream stopped.")
    device_name_box.empty()
    st.info("Click 'Start' above to begin the high-speed stream.")