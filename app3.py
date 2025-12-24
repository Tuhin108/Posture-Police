import streamlit as st
import cv2
import mediapipe as mp
import numpy as np
import time
import threading
import winsound

# Fix for Pylance/VS Code errors
mp_pose = mp.solutions.pose  # type: ignore

# Global event for alarm control
alarm_event = threading.Event()

def initialize_session_state():
    if 'calibrated' not in st.session_state:
        st.session_state.calibrated = False
    if 'baseline_neck' not in st.session_state:
        st.session_state.baseline_neck = 0
    if 'baseline_eye_level' not in st.session_state:
        st.session_state.baseline_eye_level = 0
    if 'bad_posture_start' not in st.session_state:
        st.session_state.bad_posture_start = None
    if 'camera_on' not in st.session_state:
        st.session_state.camera_on = False

def calibrate(landmarks, frame_shape):
    h, w = frame_shape[:2]
    
    # Get Coordinates
    left_ear = landmarks[7]
    right_ear = landmarks[8]
    left_shoulder = landmarks[11]
    right_shoulder = landmarks[12]
    left_eye = landmarks[2]
    right_eye = landmarks[5]
    
    # Averages
    avg_ear_y = (left_ear.y + right_ear.y) / 2 * h
    avg_shoulder_y = (left_shoulder.y + right_shoulder.y) / 2 * h
    avg_eye_y = (left_eye.y + right_eye.y) / 2 * h
    
    # Metric 1: Neck Length (Vertical distance Ear to Shoulder)
    baseline_neck = avg_shoulder_y - avg_ear_y
    
    # Metric 2: Eye Level (Absolute Y position on screen)
    baseline_eye_level = avg_eye_y
    
    return baseline_neck, baseline_eye_level

def check_posture(landmarks, frame_shape, sensitivity):
    h, w = frame_shape[:2]
    
    left_ear = landmarks[7]
    right_ear = landmarks[8]
    left_shoulder = landmarks[11]
    right_shoulder = landmarks[12]
    left_eye = landmarks[2]
    right_eye = landmarks[5]
    
    # Current Metrics
    avg_ear_y = (left_ear.y + right_ear.y) / 2 * h
    avg_shoulder_y = (left_shoulder.y + right_shoulder.y) / 2 * h
    avg_eye_y = (left_eye.y + right_eye.y) / 2 * h
    
    curr_neck = avg_shoulder_y - avg_ear_y
    curr_eye_level = avg_eye_y
    
    # --- LOGIC WITH SENSITIVITY ---
    # Sensitivity 1 (Loose) -> Requires 30% drop to trigger
    # Sensitivity 5 (Medium) -> Requires 15% drop to trigger
    # Sensitivity 10 (Strict) -> Requires 5% drop to trigger
    
    # Map slider (1-10) to a Percentage Threshold (0.70 to 0.95)
    threshold_factor = 0.65 + (sensitivity * 0.03) 
    
    # 1. The Hunch Check (Neck gets shorter)
    # If neck length shrinks below threshold% of baseline
    neck_limit = st.session_state.baseline_neck * threshold_factor
    is_hunching = curr_neck < neck_limit
    
    # 2. The Sink Check (Eyes drop down screen)
    # If eyes drop more than X pixels (mapped to sensitivity)
    # High sensitivity = Tolerates less drop (e.g. 20 pixels)
    # Low sensitivity = Tolerates huge drop (e.g. 100 pixels)
    drop_tolerance = 120 - (sensitivity * 10) 
    is_sinking = curr_eye_level > (st.session_state.baseline_eye_level + drop_tolerance)
    
    is_bad = is_hunching or is_sinking
    
    # Pack debug info
    debug = {
        'curr_neck': int(curr_neck),
        'limit_neck': int(neck_limit),
        'curr_eye': int(curr_eye_level),
        'limit_eye': int(st.session_state.baseline_eye_level + drop_tolerance),
        'hunching': is_hunching,
        'sinking': is_sinking
    }
    
    draw_coords = (
        int((left_ear.x+right_ear.x)/2 * w), int(avg_ear_y),
        int((left_shoulder.x+right_shoulder.x)/2 * w), int(avg_shoulder_y)
    )
    
    return is_bad, draw_coords, debug

def draw_hud(frame, is_bad, coords, debug):
    h, w = frame.shape[:2]
    ear_x, ear_y, shldr_x, shldr_y = coords
    
    color = (0, 0, 255) if is_bad else (0, 255, 0)
    
    # Draw Skeleton Line
    cv2.line(frame, (ear_x, ear_y), (shldr_x, shldr_y), color, 4)
    cv2.circle(frame, (ear_x, ear_y), 6, (255, 255, 0), -1)
    cv2.circle(frame, (shldr_x, shldr_y), 6, (255, 255, 0), -1)
    
    # Draw Status Box
    cv2.rectangle(frame, (0, 0), (w, h), color, 10)
    
    # Draw Data Box (Top Left)
    cv2.rectangle(frame, (0, 0), (300, 110), (0, 0, 0), -1)
    cv2.putText(frame, f"Neck: {debug['curr_neck']} (Min: {debug['limit_neck']})", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.putText(frame, f"Eyes: {debug['curr_eye']} (Max: {debug['limit_eye']})", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    status = "GOOD"
    if debug['hunching']: status = "HUNCHING!"
    if debug['sinking']: status = "SINKING!"
    
    cv2.putText(frame, f"Status: {status}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    if is_bad:
        cv2.putText(frame, "FIX POSTURE!", (w//2 - 150, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        
    return frame

def alarm_loop():
    while alarm_event.is_set():
        try: winsound.Beep(1000, 200)
        except: pass
        time.sleep(0.5)

def main():
    st.set_page_config(page_title="Posture Police", layout="wide")
    initialize_session_state()
    
    with st.sidebar:
        st.title("🎚️ Controls")
        
        # --- UPDATED: Slider now goes up to 60 seconds, Default is 30 ---
        alarm_delay = st.slider("Alarm Delay (Seconds)", 1, 60, 30, help="Beeps only after this many seconds of continuous slouching")
        
        sensitivity = st.slider("Sensitivity", 1, 10, 8, help="Higher = Stricter")
        
        st.divider()
        
        camera_on = st.checkbox("Start Camera", value=st.session_state.camera_on)
        st.session_state.camera_on = camera_on
        
        calibrate_btn = st.button("Calibrate Now", type="primary", disabled=not camera_on)
        if st.session_state.calibrated: st.success("Calibrated!")
        
    st.title("Posture Police 📸🕵️‍♂️")
    video_placeholder = st.empty()
    
    if camera_on:
        cap = cv2.VideoCapture(0)
        with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
            while camera_on:
                ret, frame = cap.read()
                if not ret: break
                
                frame = cv2.flip(frame, 1)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(rgb_frame)
                
                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark
                    
                    if calibrate_btn:
                        n, e = calibrate(landmarks, frame.shape)
                        st.session_state.baseline_neck = n
                        st.session_state.baseline_eye_level = e
                        st.session_state.calibrated = True
                        st.rerun()
                        
                    if st.session_state.calibrated:
                        is_bad, coords, debug = check_posture(landmarks, frame.shape, sensitivity)
                        frame = draw_hud(frame, is_bad, coords, debug)
                        
                        if is_bad:
                            if not st.session_state.bad_posture_start:
                                st.session_state.bad_posture_start = time.time()
                            # --- LOGIC: Checks if current time > start time + 30 seconds ---
                            elif time.time() - st.session_state.bad_posture_start > alarm_delay and not alarm_event.is_set():
                                alarm_event.set()
                                threading.Thread(target=alarm_loop, daemon=True).start()
                        else:
                            # If you sit straight for even 1 frame, the timer resets!
                            st.session_state.bad_posture_start = None
                            alarm_event.clear()
                    else:
                        cv2.putText(frame, "Sit Straight & Calibrate", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        
                video_placeholder.image(frame, channels="BGR")
                if not st.session_state.camera_on: break
        cap.release()
        alarm_event.clear()

if __name__ == "__main__":
    main()