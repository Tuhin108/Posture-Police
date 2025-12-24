# =========================
# FORCE MEDIAPIPE CPU (fix EGL crash on Streamlit Cloud)
# =========================
import os
os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"

import streamlit as st
import cv2
import mediapipe as mp
import numpy as np
import time
import threading
import av

from streamlit_webrtc import (
    webrtc_streamer,
    VideoProcessorBase,
    WebRtcMode
)

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Posture Police", layout="wide")

alarm_event = threading.Event()

# =========================
# SESSION STATE INIT
# =========================
def init_state():
    defaults = {
        "calibrated": False,
        "baseline_neck": 0.0,
        "baseline_eye_level": 0.0,
        "bad_posture_start": None,
        "calibrate_request": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# =========================
# MEDIAPIPE
# =========================
mp_pose = mp.solutions.pose

@st.cache_resource
def load_pose():
    return mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

pose = load_pose()

# =========================
# POSTURE LOGIC
# =========================
def calibrate(landmarks, shape):
    h, _ = shape[:2]
    le, re = landmarks[7], landmarks[8]
    ls, rs = landmarks[11], landmarks[12]
    ley, rey = landmarks[2], landmarks[5]

    ear_y = (le.y + re.y) / 2 * h
    sh_y = (ls.y + rs.y) / 2 * h
    eye_y = (ley.y + rey.y) / 2 * h

    return sh_y - ear_y, eye_y


def check_posture(landmarks, shape, sensitivity):
    h, w = shape[:2]
    le, re = landmarks[7], landmarks[8]
    ls, rs = landmarks[11], landmarks[12]
    ley, rey = landmarks[2], landmarks[5]

    ear_y = (le.y + re.y) / 2 * h
    sh_y = (ls.y + rs.y) / 2 * h
    eye_y = (ley.y + rey.y) / 2 * h

    curr_neck = sh_y - ear_y
    curr_eye = eye_y

    factor = 0.65 + sensitivity * 0.03
    neck_limit = st.session_state.baseline_neck * factor
    is_hunch = curr_neck < neck_limit

    drop = 120 - sensitivity * 10
    is_sink = curr_eye > st.session_state.baseline_eye_level + drop

    is_bad = is_hunch or is_sink

    coords = (
        int((le.x + re.x) / 2 * w), int(ear_y),
        int((ls.x + rs.x) / 2 * w), int(sh_y)
    )

    debug = {
        "curr_neck": int(curr_neck),
        "limit_neck": int(neck_limit),
        "curr_eye": int(curr_eye),
        "limit_eye": int(st.session_state.baseline_eye_level + drop),
        "hunching": is_hunch,
        "sinking": is_sink,
    }

    return is_bad, coords, debug


def draw_hud(frame, is_bad, coords, debug):
    h, w = frame.shape[:2]
    ex, ey, sx, sy = coords
    color = (0, 0, 255) if is_bad else (0, 255, 0)

    cv2.line(frame, (ex, ey), (sx, sy), color, 4)
    cv2.circle(frame, (ex, ey), 6, (255, 255, 0), -1)
    cv2.circle(frame, (sx, sy), 6, (255, 255, 0), -1)

    cv2.rectangle(frame, (10, 10), (340, 110), (0, 0, 0), -1)
    cv2.rectangle(frame, (10, 10), (340, 110), (255, 255, 255), 2)

    cv2.putText(frame, f"Neck: {debug['curr_neck']} (Min {debug['limit_neck']})",
                (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
    cv2.putText(frame, f"Eyes: {debug['curr_eye']} (Max {debug['limit_eye']})",
                (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

    status = "GOOD"
    if debug["hunching"]:
        status = "HUNCHING!"
    if debug["sinking"]:
        status = "SINKING!"

    cv2.putText(frame, status, (20, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    if is_bad:
        cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 8)
        cv2.putText(frame, "FIX POSTURE!",
                    (w//2 - 140, h//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                    (0, 0, 255), 3)

    return frame

# =========================
# VIDEO PROCESSOR
# =========================
class PostureProcessor(VideoProcessorBase):
    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        res = pose.process(rgb)

        if res.pose_landmarks and len(res.pose_landmarks.landmark) > 12:
            lm = res.pose_landmarks.landmark

            if st.session_state.calibrate_request:
                n, e = calibrate(lm, img.shape)
                st.session_state.baseline_neck = n
                st.session_state.baseline_eye_level = e
                st.session_state.calibrated = True
                st.session_state.bad_posture_start = None
                alarm_event.clear()
                st.session_state.calibrate_request = False

            if st.session_state.calibrated:
                is_bad, coords, debug = check_posture(
                    lm, img.shape, sensitivity
                )
                img = draw_hud(img, is_bad, coords, debug)
            else:
                cv2.putText(img, "Sit straight & Click Calibrate",
                            (30, 60), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, (0, 255, 0), 2)

        return av.VideoFrame.from_ndarray(img, format="bgr24")

# =========================
# UI
# =========================
with st.sidebar:
    st.title("🎚 Controls")
    alarm_delay = st.slider("Alarm Delay (sec)", 1, 60, 30)
    sensitivity = st.slider("Sensitivity", 1, 10, 8)

    if st.button("🎯 Calibrate"):
        st.session_state.calibrate_request = True

    if st.session_state.calibrated:
        st.success("Calibrated ✅")

st.title("👮 Posture Police")

ctx = webrtc_streamer(
    key="posture-police",
    mode=WebRtcMode.SENDRECV,
    video_processor_factory=PostureProcessor,
    media_stream_constraints={"video": True, "audio": False},
    rtc_configuration={
        "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
    },
    async_processing=True,
)

if ctx.state.playing:
    st.success("✅ Camera stream running")
else:
    st.info("📹 Click Start above and allow camera access")
