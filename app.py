import streamlit as st
import cv2
import mediapipe as mp
import time
import threading
import platform

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Posture Police", layout="wide")

try:
    import winsound  # Windows only
except Exception:
    winsound = None

alarm_event = threading.Event()
alarm_lock = threading.Lock()

# =========================
# SESSION STATE INIT
# =========================
def init_state():
    defaults = {
        "initialized": True,
        "calibrated": False,
        "baseline_neck": 0.0,
        "baseline_eye_level": 0.0,
        "bad_posture_start": None,
        "camera_on": False,
        "calibrate_request": False,
        "cap": None,
        "stop_requested": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# =========================
# CAMERA CONTROL
# =========================
def get_camera():
    if st.session_state.cap is None:
        try:
            if platform.system() == "Windows":
                st.session_state.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            else:
                st.session_state.cap = cv2.VideoCapture(0)
        except Exception:
            st.session_state.cap = cv2.VideoCapture(0)
    return st.session_state.cap


def release_camera():
    cap = st.session_state.get("cap")
    if cap is not None:
        try:
            cap.release()
        except Exception:
            pass
    st.session_state.cap = None


# Always release on reload if camera flag is off
if st.session_state.cap is not None and not st.session_state.camera_on:
    release_camera()

# =========================
# CALLBACKS
# =========================
def stop_camera():
    release_camera()
    alarm_event.clear()

if st.session_state.stop_requested:
    st.session_state.camera_on = False
    st.session_state.stop_requested = False
    stop_camera()



# =========================
# MEDIAPIPE
# =========================
mp_pose = mp.solutions.pose  # type: ignore

@st.cache_resource
def load_pose():
    return mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

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
    if debug["hunching"]: status = "HUNCHING!"
    if debug["sinking"]: status = "SINKING!"

    cv2.putText(frame, status, (20, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    if is_bad:
        cv2.rectangle(frame, (0,0), (w,h), (0,0,255), 10)
        cv2.putText(frame, "FIX POSTURE!", (w//2-120, h//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,0,255), 3)

    return frame

# =========================
# ALARM THREAD
# =========================
def alarm_loop():
    while alarm_event.is_set():
        try:
            if platform.system() == "Windows" and winsound:
                winsound.Beep(1000, 150)
            else:
                print("\a", end="", flush=True)
        except Exception:
            pass
        time.sleep(0.3)

# =========================
# UI
# =========================
with st.sidebar:
    st.title("🎚 Controls")
    alarm_delay = st.slider("Alarm Delay (sec)", 1, 60, 30)
    sensitivity = st.slider("Sensitivity", 1, 10, 8)

    st.checkbox("Start Camera", key="camera_on")

    if st.button("⏹ Stop Camera"):
        st.session_state.stop_requested = True
        st.rerun()

    if st.button("🎯 Calibrate", disabled=not st.session_state.camera_on):
        st.session_state.calibrate_request = True

    if st.session_state.calibrated:
        st.success("Calibrated ✅")

st.title("👮 Posture Police")
video_placeholder = st.empty()

# =========================
# MAIN LOOP
# =========================
if st.session_state.camera_on:
    cap = get_camera()
    pose = load_pose()

    if not cap.isOpened():
        st.error("❌ Camera not accessible.")
    else:
        try:
            while st.session_state.camera_on:
                ret, frame = cap.read()
                if not ret:
                    break

                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res = pose.process(rgb)

                if res.pose_landmarks and len(res.pose_landmarks.landmark) > 12:
                    lm = res.pose_landmarks.landmark

                    if st.session_state.calibrate_request:
                        n, e = calibrate(lm, frame.shape)
                        st.session_state.baseline_neck = n
                        st.session_state.baseline_eye_level = e
                        st.session_state.calibrated = True
                        st.session_state.bad_posture_start = None
                        alarm_event.clear()
                        st.session_state.calibrate_request = False
                        st.rerun()

                    if st.session_state.calibrated:
                        is_bad, coords, debug = check_posture(lm, frame.shape, sensitivity)
                        frame = draw_hud(frame, is_bad, coords, debug)

                        if is_bad:
                            if st.session_state.bad_posture_start is None:
                                st.session_state.bad_posture_start = time.time()
                            elif time.time() - st.session_state.bad_posture_start > alarm_delay:
                                if not alarm_event.is_set():
                                    alarm_event.set()
                                    threading.Thread(target=alarm_loop, daemon=True).start()
                        else:
                            st.session_state.bad_posture_start = None
                            alarm_event.clear()
                    else:
                        cv2.putText(frame, "Sit straight & Calibrate",
                                    (30, 60), cv2.FONT_HERSHEY_SIMPLEX,
                                    0.8, (0,255,0), 2)

                video_placeholder.image(frame, channels="BGR")
                time.sleep(0.02)
        finally:
            release_camera()
            alarm_event.clear()
else:
    release_camera()
    alarm_event.clear()
    video_placeholder.info("📹 Click 'Start Camera' to begin")
