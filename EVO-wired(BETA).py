import cv2
import mediapipe as mp
from mediapipe.solutions import drawing_utils as mp_drawing, drawing_styles as mp_drawing_styles
import numpy as np
import math
import time
import RPi.GPIO as GPIO
from adafruit_servokit import ServoKit

# GPIO Setup for Relay
RELAY_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)  # Explicit initialization

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
kit = ServoKit(channels=16)

# Initialize Servo Positions
kit.servo[0].angle = 140  # Left lid
kit.servo[1].angle = 90   # Left pan
kit.servo[4].angle = 140  # Right lid
kit.servo[5].angle = 90   # Right pan

# Blink / Relay Control Variables
blink_counter = 0                # counts individual blinks (0..2) until toggle
relay_on = False                 # current relay state
eyes_closed_prev = False         # previous frame closed state
last_closure_time = 0            # when eyes were detected closed
last_blink_time = 0              # debounce for counting blinks

# Eye Tracking Variables
eye_move = "neutral"
debounce_time = 1  # seconds
last_event_time = 0

# Display Variables
width, height = 640, 480
ball_radius = 20
ball_color = (255, 255, 255)
ball_speed = 15
ball_x = width // 2
ball_y = height//4*3

def move_ball(gesture):
    global ball_x, ball_y, ball_color
    if gesture == "eye move left":
        ball_x += ball_speed
    elif gesture == "eye move right":
        ball_x -= ball_speed
    elif "close" in gesture:
        ball_color = (0, 0, 255) if "both" in gesture else \
                    (255, 0, 0) if "left" in gesture else \
                    (0, 255, 0)
    else:
        ball_color = (255, 255, 255)

    ball_x = np.clip(ball_x, ball_radius, width - ball_radius)
    ball_y = np.clip(ball_y, ball_radius, height - ball_radius)

def euclidean_distance(point1, point2):
    return math.sqrt((point2[0]-point1[0])**2 + (point2[1]-point1[1])**2)

def iris_position(iris_center, point1, point2):
    center_to_point1 = euclidean_distance(iris_center, point1)
    center_to_point2 = euclidean_distance(iris_center, point2)
    point1_to_point2 = euclidean_distance(point1, point2)
    return center_to_point1 / point1_to_point2

def calculate_fps(prev_time, prev_fps):
    current_time = time.time()
    fps = 0.9*prev_fps + 0.1*(1/(current_time - prev_time))
    return fps, current_time

def relay_control(state):
    GPIO.output(RELAY_PIN, state)
    print(f"Relay {'ON' if state else 'OFF'}")  # Debug output

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

        eye_move = "neutral"
        current_time = time.time()
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_h, img_w = frame.shape[:2]
        results = face_mesh.process(rgb_frame)

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            points = [(landmark.x, landmark.y) for landmark in landmarks]
            p = np.array([[p.x*img_w, p.y*img_h] for p in landmarks]).astype(int)

            if len(points) > 2:
                ratioRH = iris_position(p[468], p[33], p[133])
                eye_width_R = euclidean_distance(p[33], p[133])
                eye_width_L = euclidean_distance(p[362], p[263])
                eye_height_R = euclidean_distance(p[159], p[145])
                eye_height_L = euclidean_distance(p[386], p[374])
                ratioROC = eye_height_R / eye_width_R
                ratioLOC = eye_height_L / eye_width_L

                # Eye movement detection
                if ratioRH > 0.65:
                    eye_move = "eye move left"
                    kit.servo[1].angle = 65
                    kit.servo[5].angle = 65
                elif ratioRH < 0.4:
                    eye_move = "eye move right"
                    kit.servo[1].angle = 115
                    kit.servo[5].angle = 115
                else:
                    kit.servo[1].angle = 90
                    kit.servo[5].angle = 90

                # Eye closure detection with adjusted thresholds
                eyes_closed = (ratioROC < 0.2 and ratioLOC < 0.2)

                # transitions for blink counting (closed -> open counts as a blink)
                if eyes_closed and not eyes_closed_prev:
                    last_closure_time = current_time
                    kit.servo[0].angle = 90
                    kit.servo[4].angle = 90

                if (not eyes_closed) and eyes_closed_prev:
                    closure_duration = current_time - last_closure_time
                    if 0.03 < closure_duration < 1.0 and (current_time - last_blink_time) > 0.2:
                        blink_counter += 1
                        last_blink_time = current_time
                        print(f"Blink detected (count={blink_counter})")
                        if blink_counter >= 3:
                            relay_on = not relay_on
                            relay_control(GPIO.HIGH if relay_on else GPIO.LOW)
                            print(f"Relay toggled -> {'ON' if relay_on else 'OFF'}")
                            blink_counter = 0

                # single-eye close handling when not both closed
                if not eyes_closed:
                    if ratioROC < 0.2:
                        eye_move = "right eye close"
                        kit.servo[4].angle = 90
                    elif ratioLOC < 0.2:
                        eye_move = "left eye close"
                        kit.servo[0].angle = 90

                eyes_closed_prev = eyes_closed

        # Ensure relay output matches relay_on state
        relay_control(GPIO.HIGH if relay_on else GPIO.LOW)

        # Display updates
        fps, prev_time = calculate_fps(prev_time, prev_fps)
        cv2.putText(frame, f'FPS: {int(fps)}', (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)
        cv2.putText(frame, f'State: {eye_move}', (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)
        cv2.putText(frame, f'Blinks: {blink_counter}/3', (10, 110), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
        cv2.putText(frame, f'Relay: {"ON" if relay_on else "OFF"}', (10, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
        cv2.circle(frame, (ball_x, ball_y), ball_radius, ball_color, -1)
        move_ball(eye_move)

        # Draw MediaPipe face mesh overlays for visualization
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                mp_drawing.draw_landmarks(
                    image=frame,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style())
                mp_drawing.draw_landmarks(
                    image=frame,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_contours_style())
                # Draw iris connections (may not exist in older mediapipe)
                try:
                    mp_drawing.draw_landmarks(
                        image=frame,
                        landmark_list=face_landmarks,
                        connections=mp_face_mesh.FACEMESH_IRISES,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_contours_style())
                except Exception:
                    pass

        cv2.imshow('Eye Control', frame)

        if cv2.waitKey(5) & 0xFF == 27:
            break

# Cleanup
kit.servo[0].angle = 140
kit.servo[1].angle = 90
kit.servo[4].angle = 140
kit.servo[5].angle = 90
GPIO.cleanup()
cap.release()
cv2.destroyAllWindows()