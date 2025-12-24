# Posture Police 📸🕵️‍♂️

**Posture Police** is a real-time, AI-powered application designed to help you maintain healthy sitting habits while working at your computer. Built with **Streamlit**, **MediaPipe**, and **OpenCV**, it uses your webcam to monitor your body landmarks and alerts you when you slouch, hunch, or "sink" in your chair.

---

## 🚀 Features

* **Real-Time Monitoring:** Uses MediaPipe Pose estimation to track key body landmarks (ears, shoulders, eyes) at 30+ FPS.
* **One-Click Calibration:** Sets a personalized baseline for *your* ideal posture, accounting for different camera angles and seating positions.
* **Smart "Hunch" & "Sink" Detection:**
    * *Hunching:* Detects when your neck compresses (distance between ear and shoulder decreases).
    * *Sinking:* Detects when your overall eye level drops significantly on the screen.
* **Customizable Sensitivity:** Adjust how strict the detection is via a sidebar slider (1-10).
* **Intelligent Alarm System:**
    * Includes a configurable **Time Delay** (e.g., 30 seconds). The alarm only triggers if you maintain bad posture continuously for that duration, preventing false alarms during brief movements.
    * Audio feedback using system beeps.
* **Visual HUD:** On-screen skeleton overlay and status indicators (Green = Good, Red = Bad).

## 🛠️ Tech Stack

* **Python 3.8+**
* **Streamlit:** Web interface and state management.
* **MediaPipe:** ML solutions for high-fidelity body pose tracking.
* **OpenCV:** Image processing and frame manipulation.
* **NumPy:** Mathematical calculations for coordinate mapping.

---

## 📦 Installation

1.  **Clone the repository** (or download the files):
    ```bash
    git clone [https://github.com/yourusername/posture-police.git](https://github.com/yourusername/posture-police.git)
    cd posture-police
    ```

2.  **Create a Virtual Environment** (Recommended):
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## 🎮 How to Use

1.  **Run the Application**:
    ```bash
    streamlit run app.py
    ```

2.  **Configure Settings (Sidebar)**:
    * **Alarm Delay:** Set how many seconds of *continuous* bad posture are allowed before the alarm beeps (Default: 30s).
    * **Sensitivity:** Set how strict the monitoring is (1 = Loose, 10 = Strict).
    * **Start Camera:** Check the box to initialize the webcam.

3.  **Calibrate**:
    * Sit up straight in your ideal ergonomic position.
    * Look at the camera.
    * Click the **"Calibrate Now"** button in the sidebar.
    * *Note: If you move your camera or chair significantly, please recalibrate.*

4.  **Monitor**:
    * Work as usual. If the skeleton turns **RED** and the status says **"HUNCHING!"** or **"SINKING!"**, correct your posture.
    * If you remain in a bad position for longer than the "Alarm Delay" time, the system will beep until you sit up straight.

---

## 🧠 How the Algorithm Works

The application tracks normalized coordinates $(x, y)$ of the user's Pose Landmarks.

1.  **Calibration Phase:**
    * Calculates the vertical distance between the ear and the shoulder (Neck Length).
    * Records the absolute Y-position of the eyes (Eye Level).

2.  **Monitoring Phase:**
    * **The Hunch Check:** If the current Neck Length drops below a percentage of the baseline (determined by the sensitivity slider), it flags a hunch.
    * **The Sink Check:** If the Eye Level drops lower (Y-value increases) beyond a specific pixel threshold compared to the baseline, it flags sinking.

---

## ⚠️ Limitations & Compatibility

* **Windows Only (Audio):** The current version uses `winsound` for audio alerts, which is a standard Python library specific to **Windows**.
    * *Mac/Linux Users:* The visual detection will work, but the app may crash or fail to produce sound when the alarm triggers. To fix this, replace `winsound` with a cross-platform library like `playsound`.
* **Lighting:** MediaPipe works best in well-lit environments. Poor lighting may result in jittery landmark detection.

## 🤝 Contributing

Contributions are welcome! If you'd like to add cross-platform audio support or improve the detection logic:

1.  Fork the Project.
2.  Create your Feature Branch (`git checkout -b feature/NewFeature`).
3.  Commit your Changes (`git commit -m 'Add some NewFeature'`).
4.  Push to the Branch (`git push origin feature/NewFeature`).
5.  Open a Pull Request.

`Made with ❤️ by Tuhin Kumar Singha Roy`
