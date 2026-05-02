import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['GLOG_minloglevel'] = '2'

import cv2
import mediapipe as mp
import numpy as np
import time
import threading
import glob
import subprocess
import psutil
from flask import Flask, render_template, Response, jsonify, request
from gpiozero import OutputDevice

# --- PCA9685 SERVO CONTROLLER ---
try:
    from adafruit_servokit import ServoKit
except ImportError:
    ServoKit = None

app = Flask(__name__)
output_frame = None

# --- CRITICAL THREAD LOCKS ---
lock = threading.Lock()
i2c_lock = threading.Lock()

# --- GLOBAL VARIABLES ---
relay_on = False
ball_x, ball_y = 320.0, 240.0
eyes_closed_prev = False
blink_count = 0
current_hover_target = None
last_blink_time = 0.0
BLINK_TIMEOUT = 1.5

LIMIT_X_MIN = 0.40
LIMIT_X_MAX = 0.65
LIMIT_Y_MIN = 0.35
LIMIT_Y_MAX = 0.55

last_manual_override = 0.0 

# Left Eye:  0 (Pan/X), 1 (Tilt/Y), 2 (Lid)
# Right Eye: 4 (Pan/X), 5 (Tilt/Y), 6 (Lid)
SERVO_DEFAULTS = {0: 90, 1: 90, 2: 140, 4: 90, 5: 90, 6: 140}

# --- HARDWARE INITIALIZATION ---
try:
    hardware_relay = OutputDevice(17, active_high=True, initial_value=True)
    print("[HARDWARE] GPIO 17 Relay ready.")
except Exception as e:
    print(f"[WARNING] GPIO 17 cannot be initialized: {e}")
    hardware_relay = None

try:
    if ServoKit is not None:
        kit = ServoKit(channels=16)
        print("[HARDWARE] PCA9685 connected. Robotic eyes ready!")
        for ch, angle in SERVO_DEFAULTS.items():
            kit.servo[ch].angle = angle
    else:
        kit = None
except Exception as e:
    print(f"[WARNING] PCA9685 not found. Check I2C wiring: {e}")
    kit = None

# --- MASTER RELAY SWITCH ---
def toggle_system_relay():
    global relay_on, hardware_relay
    try:
        if hardware_relay is not None:
            hardware_relay.toggle()
            relay_on = hardware_relay.is_active
            print(f"[RELAY] Hardware relay switched: {'ON' if relay_on else 'OFF'}")
        else:
            relay_on = not relay_on
            print(f"[RELAY] Software switch: {'ON' if relay_on else 'OFF'}")
    except Exception as e:
        print(f"[RELAY ERROR] {e}")

# --- SCREEN TRACKING CONFIG ---
FRAME_W = 640
FRAME_H = 480
CALIBRATION_POINTS = [(80, 60), (320, 60), (560, 60), (80, 240), (320, 240), (560, 240), (80, 420), (320, 420), (560, 420)]
HEAD_COMP_X, HEAD_COMP_Y = 0.22, 0.28
BASE_SMOOTHING, FAST_SMOOTHING, DEAD_ZONE = 0.03, 0.08, 6.0
CALIBRATION_SETTLE_TIME, CALIBRATION_SAMPLE_TARGET = 0.7, 25
BLINK_EAR_THRESHOLD = 0.20

calibration_mode = True
calib_stage = 0
calib_collecting = False
calib_collect_start = 0.0
calib_sample_buffer = []
calib_dataset = []
model_x, model_y = None, None

BUTTONS = {
    "TOP LEFT": (10, 10, 160, 110), "TOP RIGHT": (470, 10, 630, 110),
    "BTM LEFT": (10, 370, 160, 470), "BTM RIGHT": (470, 370, 630, 470)
}

# --- SYSTEM UTILS ---
def is_monitor_connected():
    if os.name == 'nt': return False
    try:
        connectors = glob.glob('/sys/class/drm/card*-*/status')
        return any(open(c).read().strip() == 'connected' for c in connectors)
    except: return False

def get_cpu_temp():
    try:
        res = subprocess.check_output(["vcgencmd", "measure_temp"]).decode("utf-8")
        return res.replace("temp=", "").replace("'C\n", "")
    except: return "N/A"

def clamp(value, lo, hi): return max(lo, min(hi, value))

def build_feature_vector(gx, gy, yaw, pitch):
    return np.array([1.0, gx, gy, yaw, pitch, gx * gy, gx * gx, gy * gy, yaw * gx, pitch * gy], dtype=np.float32)

def fit_models(dataset):
    if len(dataset) < 6: return None, None
    X = np.array([d['features'] for d in dataset], dtype=np.float32)
    yx = np.array([d['target'][0] for d in dataset], dtype=np.float32)
    yy = np.array([d['target'][1] for d in dataset], dtype=np.float32)
    mx, *_ = np.linalg.lstsq(X, yx, rcond=None)
    my, *_ = np.linalg.lstsq(X, yy, rcond=None)
    return mx, my

def predict_screen_xy(gx, gy, yaw, pitch):
    if model_x is None or model_y is None: return FRAME_W / 2, FRAME_H / 2
    fv = build_feature_vector(gx, gy, yaw, pitch)
    return clamp(float(fv @ model_x), 0, FRAME_W - 1), clamp(float(fv @ model_y), 0, FRAME_H - 1)

def robust_point(sample_buffer):
    if not sample_buffer: return None
    arr = np.array(sample_buffer, dtype=np.float32)
    med = np.median(arr, axis=0)
    mad = np.where((m := np.median(np.abs(arr - med), axis=0)) < 1e-6, 1e-6, m)
    keep = np.all((np.abs(arr - med) / mad) < 3.5, axis=1)
    return np.median(arr[keep] if np.any(keep) else arr, axis=0)

def adaptive_smooth(current, target):
    dx, dy = target[0] - current[0], target[1] - current[1]
    if (dist := float(np.hypot(dx, dy))) < DEAD_ZONE: return current[0], current[1]
    alpha = clamp(FAST_SMOOTHING if dist > 80 else BASE_SMOOTHING + (FAST_SMOOTHING - BASE_SMOOTHING) * (dist / 80.0), BASE_SMOOTHING, FAST_SMOOTHING)
    return current[0] + dx * alpha, current[1] + dy * alpha

def extract_gaze_features(points):
    fw, fh = np.linalg.norm(points[234] - points[454]), np.linalg.norm(points[10] - points[152])
    cx, cy = (points[234][0] + points[454][0]) / 2.0, (points[10][1] + points[152][1]) / 2.0
    yaw, pitch = (points[1][0] - cx) / fw if fw > 0 else 0.0, (points[1][1] - cy) / fh if fh > 0 else 0.0
    rw, rh = max(np.linalg.norm(points[33] - points[133]), 0.1), np.linalg.norm(points[159] - points[145])
    lw, lh = max(np.linalg.norm(points[362] - points[263]), 0.1), np.linalg.norm(points[386] - points[374])
    gx = (np.linalg.norm(points[468] - points[33])/rw + np.linalg.norm(points[473] - points[362])/lw) / 2.0 + (yaw * HEAD_COMP_X)
    gy = ((np.linalg.norm(points[468] - points[159])/rh if rh>0 else 0.5) + (np.linalg.norm(points[473] - points[386])/lh if lh>0 else 0.5)) / 2.0 + (pitch * HEAD_COMP_Y)
    closed = (((rh/rw) + (lh/lw)) / 2.0) < BLINK_EAR_THRESHOLD
    return gx, gy, yaw, pitch, ((rh/rw) + (lh/lw)) / 2.0, closed

def reset_calibration():
    global calibration_mode, calib_stage, calib_collecting, calib_collect_start, calib_sample_buffer, calib_dataset, model_x, model_y
    calibration_mode, calib_stage, calib_collecting, calib_collect_start = True, 0, False, 0.0
    calib_sample_buffer, calib_dataset, model_x, model_y = [], [], None, None

# --- MAIN CAMERA LOOP ---
def process_camera():
    global output_frame, relay_on, ball_x, ball_y, eyes_closed_prev, blink_count, current_hover_target, last_blink_time
    global calibration_mode, calib_stage, calib_collecting, calib_collect_start, calib_sample_buffer, calib_dataset, model_x, model_y
    global hardware_relay, last_manual_override

    cap = None
    for cam_index in range(0, 6):
        if (temp_cap := cv2.VideoCapture(cam_index)).isOpened() and temp_cap.read()[0]:
            print(f"[SUCCESS] Camera connected on index {cam_index}")
            cap = temp_cap; break
        temp_cap.release()

    if cap is None:
        print("[ERROR] No working camera found!")
        return

    cap.set(3, FRAME_W); cap.set(4, FRAME_H)

    face_mesh = mp.solutions.face_mesh.FaceMesh(refine_landmarks=True, min_detection_confidence=0.5, min_tracking_confidence=0.5)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: continue
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        res = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        if res.multi_face_landmarks:
            mesh = res.multi_face_landmarks[0].landmark
            p = np.array([[lm.x * w, lm.y * h] for lm in mesh], dtype=np.float32)

            gx, gy, yaw, pitch, ear, closed = extract_gaze_features(p)
            now = time.time()

            # --- AUTOMATIC ROBOTIC EYE TRACKING ---
            if 'kit' in globals() and kit is not None and (now - last_manual_override > 3.0):

                rw = np.linalg.norm(p[33] - p[133])
                rh = np.linalg.norm(p[159] - p[145])
                pure_x = np.linalg.norm(p[468] - p[33]) / (rw if rw > 0 else 0.1)
                pure_y = np.linalg.norm(p[468] - p[159]) / (rh if rh > 0 else 0.1)

                with i2c_lock:
                    try:
                        # Eyelids (Channels 2, 6)
                        if closed:
                            kit.servo[2].angle, kit.servo[6].angle = 90, 90
                        else:
                            kit.servo[2].angle, kit.servo[6].angle = 140, 140

                        # Horizontal X (Channels 0, 4)
                        if pure_x > LIMIT_X_MAX:
                            kit.servo[0].angle, kit.servo[4].angle = 65, 65
                        elif pure_x < LIMIT_X_MIN:
                            kit.servo[0].angle, kit.servo[4].angle = 115, 115
                        else:
                            kit.servo[0].angle, kit.servo[4].angle = 90, 90

                        # Vertical Y (Channels 1, 5)
                        if pure_y > LIMIT_Y_MAX: # Looking down
                            kit.servo[1].angle, kit.servo[5].angle = 115, 115
                        elif pure_y < LIMIT_Y_MIN: # Looking up
                            kit.servo[1].angle, kit.servo[5].angle = 65, 65
                        else:
                            kit.servo[1].angle, kit.servo[5].angle = 90, 90
                    except Exception as e:
                        pass

            # --- SCREEN CURSOR & BUTTON LOGIC ---
            if calibration_mode:
                cx, cy = CALIBRATION_POINTS[calib_stage]
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.68, frame, 0.32, 0, frame)
                cv2.circle(frame, (cx, cy), 22, (0, 255, 255), 2)
                cv2.circle(frame, (cx, cy), 6, (0, 0, 255), -1)
                cv2.putText(frame, f"9-POINT CALIBRATION ({calib_stage + 1}/9)", (150, 40), 2, 0.8, (0, 255, 255), 2)

                if not calib_collecting:
                    cv2.putText(frame, "LOOK AT THE DOT AND BLINK TO START", (110, 230), 2, 0.7, (255, 255, 255), 2)
                    if not closed and eyes_closed_prev:
                        calib_collecting, calib_collect_start, calib_sample_buffer = True, now, []
                else:
                    if (remaining := max(0.0, CALIBRATION_SETTLE_TIME - (now - calib_collect_start))) > 0:
                        cv2.putText(frame, f"HOLD STILL... {remaining:.1f}s", (210, 230), 2, 0.7, (255, 255, 255), 2)
                    else:
                        if not closed: calib_sample_buffer.append([gx, gy, yaw, pitch])
                        progress = min(1.0, len(calib_sample_buffer) / CALIBRATION_SAMPLE_TARGET)
                        cv2.putText(frame, f"SAMPLING {len(calib_sample_buffer)}/{CALIBRATION_SAMPLE_TARGET}", (180, 230), 2, 0.7, (255, 255, 255), 2)
                        cv2.rectangle(frame, (170, 255), (470, 280), (70, 70, 70), 2)
                        cv2.rectangle(frame, (170, 255), (170 + int(300 * progress), 280), (0, 220, 220), -1)

                        if len(calib_sample_buffer) >= CALIBRATION_SAMPLE_TARGET:
                            if (point := robust_point(calib_sample_buffer)) is not None:
                                calib_dataset.append({'features': build_feature_vector(*point), 'target': (cx, cy)})
                            calib_stage += 1
                            calib_collecting, calib_sample_buffer = False, []

                            if calib_stage >= len(CALIBRATION_POINTS):
                                model_x, model_y = fit_models(calib_dataset)
                                calibration_mode = False
                                print(f"[CALIBRATED] {len(calib_dataset)} points captured. Screen cursor ready.")
            else:
                if not closed:
                    ball_x, ball_y = adaptive_smooth((ball_x, ball_y), predict_screen_xy(gx, gy, yaw, pitch))

                new_hover_target = next((k for k, (x1, y1, x2, y2) in BUTTONS.items() if x1 < ball_x < x2 and y1 < ball_y < y2), None)
                if new_hover_target != current_hover_target: 
                    blink_count, current_hover_target = 0, new_hover_target

                if not closed and eyes_closed_prev and current_hover_target:
                    blink_count = 1 if (now - last_blink_time > BLINK_TIMEOUT) else blink_count + 1
                    last_blink_time = now
                    if blink_count >= 3:
                        print(f"\n[EYE CONTROL] 3 blinks detected on {current_hover_target}!")
                        toggle_system_relay()
                        blink_count = 0

                cv2.rectangle(frame, (170, 0), (470, 56), (30, 30, 30), -1)
                cv2.putText(frame, f"RELAY: {'ON' if relay_on else 'OFF'}", (230, 36), 2, 0.8, (0, 200, 0) if relay_on else (0, 0, 200), 2)
                cv2.putText(frame, f"EAR:{ear:.2f}", (8, 26), 2, 0.5, (180, 180, 180), 1)

                for k, (x1, y1, x2, y2) in BUTTONS.items():
                    act = (k == current_hover_target)
                    color, th = ((0, 255, 255), 3) if act else ((100, 100, 100), 1)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, th)
                    cv2.putText(frame, f"{k} [{blink_count}/3]" if act and blink_count > 0 else k, (x1 + 10, y1 + 55), 2, 0.5, color, 1)

                cv2.circle(frame, (int(ball_x), int(ball_y)), 10, (0, 255, 255), 2)
                cv2.circle(frame, (int(ball_x), int(ball_y)), 2, (0, 255, 255), -1)

            eyes_closed_prev = closed
        else:
            cv2.putText(frame, "NO FACE DETECTED", (210, 240), 2, 0.9, (0, 0, 255), 2)

        with lock:
            if is_monitor_connected():
                try: cv2.imshow('EVO LOCAL', frame); cv2.waitKey(1)
                except: pass
                output_frame = None
            else:
                output_frame = frame.copy()

@app.route("/")
def index(): return render_template("index.html")

@app.route("/szemvezerles")
def szemvezerles(): return render_template("szemvezerles.html")

@app.route("/admin")
def admin(): return render_template("admin.html")

@app.route("/api/start_calibration", methods=["POST"])
def start_calib():
    reset_calibration()
    return jsonify({"status": "calibrating", "points": len(CALIBRATION_POINTS)})

@app.route("/api/telemetry")
def telemetry():
    return jsonify({
        "cpu": psutil.cpu_percent(), "ram": psutil.virtual_memory().percent, "temp": get_cpu_temp(), "relay": relay_on,
        "calibration_mode": calibration_mode, "calibration_stage": calib_stage + 1 if calibration_mode else len(CALIBRATION_POINTS),
        "calibration_points": len(CALIBRATION_POINTS)
    })

@app.route("/video_feed")
def video_feed():
    def gen():
        while True:
            with lock:
                f = None if output_frame is None else output_frame.copy()
            if f is None:
                time.sleep(0.5)
                continue

            ok, buf = cv2.imencode(".jpg", f, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            if ok:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + bytearray(buf) + b'\r\n')
            time.sleep(0.03)
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/toggle_relay", methods=["POST"])
def toggle_relay_api():
    toggle_system_relay()
    return jsonify({"status": "success", "relay_state": relay_on})

@app.route("/api/servo", methods=["POST"])
def set_servo():
    global last_manual_override
    data = request.json

    last_manual_override = time.time()

    if 'kit' in globals() and kit is not None and data and 'servos' in data:
        with i2c_lock:
            for s in data['servos']:
                try:
                    kit.servo[int(s['channel'])].angle = max(0.0, min(180.0, float(s['angle'])))
                except Exception as e:
                    print(f"[I2C ERROR] {e}")
    return jsonify({"status": "success"})

@app.route("/api/reset", methods=["POST"])
def reset_servos():
    global last_manual_override
    last_manual_override = time.time()

    if 'kit' in globals() and kit is not None:
        with i2c_lock:
            for ch, ang in SERVO_DEFAULTS.items():
                try: kit.servo[ch].angle = ang
                except: pass
    return jsonify({"status": "reset_complete", "defaults": SERVO_DEFAULTS})

@app.route("/api/settings", methods=["GET", "POST"])
def settings_api():
    global LIMIT_X_MIN, LIMIT_X_MAX, LIMIT_Y_MIN, LIMIT_Y_MAX

    if request.method == "POST":
        data = request.json
        if data:
            if 'x_min' in data: LIMIT_X_MIN = float(data['x_min'])
            if 'x_max' in data: LIMIT_X_MAX = float(data['x_max'])
            if 'y_min' in data: LIMIT_Y_MIN = float(data['y_min'])
            if 'y_max' in data: LIMIT_Y_MAX = float(data['y_max'])
        return jsonify({"status": "success"})

    return jsonify({
        "x_min": LIMIT_X_MIN, "x_max": LIMIT_X_MAX,
        "y_min": LIMIT_Y_MIN, "y_max": LIMIT_Y_MAX
    })

if __name__ == '__main__':
    threading.Thread(target=process_camera, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, threaded=True)