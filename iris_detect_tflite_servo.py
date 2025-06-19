import cv2
import mediapipe as mp
import numpy as np
import math
import time
import requests  # Added for HTTP communication
from adafruit_servokit import ServoKit

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
kit = ServoKit(channels=16)
kit.servo[0].angle = 140
kit.servo[1].angle = 90
kit.servo[4].angle = 140
kit.servo[5].angle = 90
eye_move = "eye move center"  # Initialize eye_move variable
debounce_time = 1  # seconds
last_event_time = 0

# NodeMCU settings
NODEMCU_IP = "192.168.0.102	"  # Replace with your NodeMCU's IP
TOGGLE_URL = f"http://{NODEMCU_IP}/toggle"

# Blink detection variables
eyes_closed = False
blink_count = 0
last_blink_time = 0
BLINK_SEQUENCE_TIME = 1.5  # Time window for 3 blinks (seconds)

# Ball properties
width = 640
height = 480
ball_radius = 20
ball_color = (255, 255, 255)
ball_speed = 15
ball_x = width // 2
ball_y = height//4*3

def send_toggle_command():
    """Send HTTP request to NodeMCU to toggle relay"""
    try:
        response = requests.get(TOGGLE_URL, timeout=2)
        if response.status_code == 200:
            print("Light toggled successfully")
        else:
            print("Failed to toggle light")
    except Exception as e:
        print(f"Error sending command: {e}")

def move_ball(gesture):
    global ball_x, ball_y, ball_speed, ball_color
    if gesture == "eye move left":
        ball_x += ball_speed
    elif gesture == "eye move right":
        ball_x -= ball_speed
    elif gesture == "left eye close":
        ball_color = (255, 0, 0)
    elif gesture == "right eye close":
        ball_color = (0, 255, 0)
    elif gesture == "both eye close":
        ball_color = (0, 0, 255)
    else:
        ball_color = (255, 255, 255)

    # Ensure the ball stays within boundaries
    ball_x = np.clip(ball_x, ball_radius, width - ball_radius)
    ball_y = np.clip(ball_y, ball_radius, height - ball_radius)

def euclidean_distance(point1, point2):
    x1, y1 = point1
    x2, y2 = point2
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def iris_position(iris_center, point1, point2):
    center_to_point1 = euclidean_distance(iris_center, point1)
    center_to_point2 = euclidean_distance(iris_center, point2)
    point1_to_point2 = euclidean_distance(point1, point2)
    return center_to_point1 / point1_to_point2

def calculate_fps(prev_time, prev_fps):
    current_time = time.time()
    fps = 0.9*prev_fps + 0.1*(1 / (current_time - prev_time))
    return fps, current_time

cap = cv2.VideoCapture(0)
prev_time = time.time()
prev_fps = 0

with mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
) as face_mesh:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        cv2.namedWindow('output', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('output', 640, 480)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_h, img_w = frame.shape[:2]
        results = face_mesh.process(rgb_frame)
        current_time = time.time()

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            p = np.array([[lm.x * img_w, lm.y * img_h] for lm in landmarks]).astype(int)

            if len(p) > 2:
                # Eye metrics calculation
                ratioRH = iris_position(p[468], p[33], p[133])
                eye_width_R = euclidean_distance(p[33], p[133])
                eye_width_L = euclidean_distance(p[362], p[263])
                eye_height_R = euclidean_distance(p[159], p[145])
                eye_height_L = euclidean_distance(p[386], p[374])
                ratioROC = eye_height_R / eye_width_R
                ratioLOC = eye_height_L / eye_width_L

                # Three-blink detection
                current_eyes_closed = (ratioROC < 0.15) and (ratioLOC < 0.15)
                if current_eyes_closed and not eyes_closed:
                    blink_count += 1
                    last_blink_time = current_time
                    eyes_closed = True
                elif not current_eyes_closed:
                    eyes_closed = False

                # Check for three blinks in sequence
                if blink_count >= 3:
                    if current_time - last_blink_time <= BLINK_SEQUENCE_TIME:
                        send_toggle_command()
                        blink_count = 0
                    else:
                        blink_count = 0

                # Existing gesture detection (keep this for servo control)
                if ratioRH > 0.65:
                    if current_time - last_event_time > debounce_time:
                        eye_move = "eye move left"
                        # Servo control logic remains unchanged
                # ... (rest of your existing servo control logic)

        # Update display and check for exit
        fps, prev_time = calculate_fps(prev_time, prev_fps)
        cv2.putText(frame, f'FPS: {int(fps)}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        cv2.circle(frame, (ball_x, ball_y), ball_radius, ball_color, -1)
        move_ball(eye_move)
        cv2.imshow('output', frame)

        if cv2.waitKey(5) & 0xFF == 27:
            break

# Cleanup
kit.servo[0].angle = 140
kit.servo[1].angle = 90
kit.servo[4].angle = 140
kit.servo[5].angle = 90
cap.release()
cv2.destroyAllWindows()
