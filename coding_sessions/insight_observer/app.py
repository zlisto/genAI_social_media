import streamlit as st
import cv2
import os
import glob
import time
import base64
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
MODEL = "gpt-5-nano" #https://platform.openai.com/docs/models/compare?model=gpt-5-nano
IMAGES_DIR = "images"
MAX_IMAGES = 20
CAPTURE_INTERVAL_SECONDS = 10 # Seconds
PROMPT_FILE = "prompt_reaction.txt"
YOUTUBE_DATA_FILE = "youtube_data.json"
DEFAULT_PROMPT_TEMPLATE = (
    "These are chronological snapshots of a person watching the YouTube video: "
    "'{video_title}'. Please summarize their emotional reaction and engagement "
    "level based on these images."
)

if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

def log_event(message: str) -> None:
    # Print to the Streamlit server terminal (stdout).
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {message}", flush=True)

def clear_images():
    files = glob.glob(os.path.join(IMAGES_DIR, "*.png"))
    for f in files:
        os.remove(f)

def load_prompt_template() -> str:
    try:
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            template = f.read().strip()
        return template if template else DEFAULT_PROMPT_TEMPLATE
    except FileNotFoundError:
        log_event(f"Prompt file '{PROMPT_FILE}' not found. Using default prompt.")
        return DEFAULT_PROMPT_TEMPLATE
    except Exception as e:
        log_event(f"Error reading prompt file '{PROMPT_FILE}': {e}. Using default prompt.")
        return DEFAULT_PROMPT_TEMPLATE

# --- OPENAI REACTION SUMMARY ---
def evaluate_reaction(video_title, video_duration_seconds, video_description=None, 
                      video_transcript=None, iframe_html=None):
    client = OpenAI()
    image_files = sorted(glob.glob(os.path.join(IMAGES_DIR, "*.png")))
    
    if not image_files:
        log_event(f"AI evaluation requested for '{video_title}' but no images were found.")
        return "No images found to analyze."

    prompt_template = load_prompt_template()
    try:
        prompt_text = prompt_template.format(
            video_title=video_title,
            video_duration_seconds=video_duration_seconds,
            video_description=video_description or "",
            video_transcript=video_transcript or "",
            iframe_html=iframe_html or "",
        )
        # Save the final prompt to a UTF-8 text file for inspection.
        # On Windows, the default encoding can be a legacy code page (e.g., cp1252),
        # which may not support all Unicode characters in the prompt.
        with open("prompt.txt", "w", encoding="utf-8") as f:
            f.write(prompt_text)
    except Exception as e:
        # If the template contains unmatched braces or other format issues, fall back safely.
        log_event(f"Prompt formatting error ({e}). Using unformatted prompt + video title.")
        prompt_text = f"{prompt_template}\n\nVideo title: {video_title}\n\nDescription: {video_description or ''}"

    content = [
        {"type": "text", "text": prompt_text}
    ]

    # Add up to MAX_IMAGES to the prompt
    num_images = 0
    for img_path in image_files[:MAX_IMAGES]:
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"}
        })
        num_images += 1
    try:
        log_event(f"Calling AI for '{video_title}' with {min(len(image_files), MAX_IMAGES)} image(s).")
        content.append({"type": "text", "text": f"Number of images provided: {num_images}"})
        response = client.chat.completions.create(
            model=MODEL, 
            messages=[{"role": "user", "content": content}]
        )
        output = response.choices[0].message.content
        log_event(f"AI response received for '{video_title}' ({len(output) if output else 0} chars).")
        return output
    except Exception as e:
        log_event(f"AI Error for '{video_title}': {e}")
        return f"AI Error: {e}"

# --- STREAMLIT UI ---
st.set_page_config(page_title="Reaction Analyzer", layout="wide")
st.title("YouTube Content Reaction Study")

# Load YouTube data from JSON
try:
    with open(YOUTUBE_DATA_FILE, "r", encoding="utf-8") as f:
        youtube_data = json.load(f)
    if not isinstance(youtube_data, list):
        raise ValueError("YouTube data must be a list of objects.")
except Exception as e:
    st.error(f"Could not load {YOUTUBE_DATA_FILE}: {e}")
    st.stop()

# Build list of titles for dropdown
video_titles = [item.get("title", "Untitled") for item in youtube_data]
selected_title = st.selectbox("Choose a video to watch:", video_titles)

# Find the selected video's full data
selected_video = next(
    (item for item in youtube_data if item.get("title") == selected_title),
    youtube_data[0],
)
selected_iframe = selected_video.get("iframe", "")
selected_description = selected_video.get("description", "") or ""
selected_transcript = selected_video.get("transcript", "") or ""
selected_duration_seconds = selected_video.get("duration_seconds", 0)

# Detect change to clear old data
if "last_video" not in st.session_state or st.session_state.last_video != selected_title:
    clear_images()
    st.session_state.last_video = selected_title
    st.session_state.start_time = None
    st.session_state.img_count = 0

# Ensure session defaults exist
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "img_count" not in st.session_state:
    st.session_state.img_count = 0

# 2. Display Video (iframe HTML from JSON) - centered
if selected_iframe:
    _, center_col, _ = st.columns([1, 6, 1])
    with center_col:
        st.components.v1.html(
            f"<div style='display:flex; justify-content:center;'>{selected_iframe}</div>",
            height=400,
        )
else:
    st.warning("No iframe HTML found for this video.")

col1, col2 = st.columns(2)

with col1:
    run_study = st.toggle("Start Recording Reaction", key="run_study")

    # Log toggle changes (prints to the terminal)
    if "last_run_study" not in st.session_state:
        st.session_state.last_run_study = run_study
    elif st.session_state.last_run_study != run_study:
        log_event(f"Recording toggled to {run_study} for '{selected_title}'.")
        st.session_state.last_run_study = run_study

    if st.button("Evaluate Response", type="primary"):
        log_event(f"'Evaluate Response' clicked for '{selected_title}'.")
        with st.spinner("Analyzing frames..."):
            summary = evaluate_reaction(
                video_title=selected_title,
                video_duration_seconds=selected_duration_seconds,
                video_description=selected_description,
                video_transcript=selected_transcript,
                iframe_html=selected_iframe,
            )
            st.session_state.summary = summary

with col2:
    st.write(f"Images Captured: {len(glob.glob(os.path.join(IMAGES_DIR, '*.png')))} / {MAX_IMAGES}")

# 3. Background Capture Logic (blocking loop; reliable camera capture)
if run_study:
    if st.session_state.start_time is None:
        st.session_state.start_time = time.time()
    
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    status_placeholder = st.empty()
    
    try:
        while run_study and st.session_state.img_count < MAX_IMAGES:
            ret, frame = cap.read()
            if not ret or frame is None:
                status_placeholder.error("Could not read from webcam.")
                log_event("ERROR: Could not read from webcam.")
                break

            st.session_state.img_count += 1
            img_filename = f"screen_shot_{st.session_state.img_count:02d}.png"
            img_path = os.path.join(IMAGES_DIR, img_filename)

            ok = cv2.imwrite(img_path, frame)
            if ok:
                status_placeholder.success(f"Captured {img_filename}")
                log_event(f"Saved image: {img_filename} ({img_path})")
            else:
                status_placeholder.error(f"Failed to save {img_filename}")
                log_event(f"ERROR: Failed to save image: {img_filename} ({img_path})")
                break
            
            time.sleep(CAPTURE_INTERVAL_SECONDS)
            
            if st.session_state.img_count >= MAX_IMAGES:
                status_placeholder.warning("Max images reached.")
                log_event(f"Max images reached ({MAX_IMAGES}).")
                break
    finally:
        cap.release()

# 4. Display Results
if "summary" in st.session_state:
    st.divider()
    st.subheader("AI Reaction Summary")
    st.write(st.session_state.summary)