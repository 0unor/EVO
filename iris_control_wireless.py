import cv2
import numpy as np
import mediapipe as mp
import tensorflow as tf
import requests
import time
import os
import threading

# Configuration
NODEMCU_AP_SSID = "EyeControl_AP"
NODEMCU_AP_PASSWORD = "kokoilil7"
NODEMCU_IP = "192.168.4.1"
GESTURE_ENDPOINT = f"http://{NODEMCU_IP}/gesture"
RELAY_ENDPOINT = f"http://{NODEMCU_IP}/relay"

# Network Parameters
CONNECTION_CHECK_INTERVAL = 15  # Seconds
MAX_RETRIES = 5
REQUEST_TIMEOUT = 3.0  # Seconds

# Camera Configuration
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# Gesture Recognition Parameters
GESTURES = ['up', 'down', 'right', 'left', 'center', 'close', 'l_close', 'r_close']

class NetworkManager:
    def __init__(self):
        self.connected = False
        self.running = True
        self._setup_network()
        self._start_monitor()

    def _setup_network(self):
        """Configure network interface settings"""
        os.system("sudo iwconfig wlan0 power off")
        os.system(f"nmcli device wifi connect '{NODEMCU_AP_SSID}' password '{NODEMCU_AP_PASSWORD}'")

    def _check_connection(self):
        """Check if connected to NodeMCU AP"""
        response = os.system(f"ping -c 1 {NODEMCU_IP} > /dev/null 2>&1")
        self.connected = response == 0
        return self.connected

    def _connection_monitor(self):
        """Background connection maintenance"""
        while self.running:
            if not self._check_connection():
                print("Connection lost! Reconnecting...")
                self._setup_network()
            time.sleep(CONNECTION_CHECK_INTERVAL)

    def _start_monitor(self):
        """Start network monitoring thread"""
        self.monitor_thread = threading.Thread(target=self._connection_monitor)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop(self):
        """Clean shutdown"""
        self.running = False
        self.monitor_thread.join()

def send_gesture(gesture_name):
    """Send gesture command with enhanced reliability"""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                GESTURE_ENDPOINT,
                json={'gesture': gesture_name},
                timeout=REQUEST_TIMEOUT
            )
            return True
        except Exception as e:
            print(f"[{time.ctime()}] Attempt {attempt+1} failed: {str(e)}")
            time.sleep(1 + attempt)  # Backoff delay
    
    print(f"[{time.ctime()}] Critical: Failed to send gesture after {MAX_RETRIES} attempts")
    return False

def handle_blink(gesture_name):
    """Handle blink-triggered relay activation"""
    if gesture_name in ["l_close", "r_close"]:
        for attempt in range(MAX_RETRIES):
            try:
                requests.get(RELAY_ENDPOINT, timeout=REQUEST_TIMEOUT)
                return True
            except Exception as e:
                print(f"[{time.ctime()}] Relay attempt {attempt+1} failed: {str(e)}")
                time.sleep(1)
    return False

def main():
    # Initialize network connection
    network = NetworkManager()
    
    # Initialize MediaPipe Face Mesh
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    # Load TFLite model
    try:
        interpreter = tf.lite.Interpreter(model_path='iris_gesture_model.tflite')
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
    except Exception as e:
        print(f"Model loading failed: {str(e)}")
        return

    # Initialize camera
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    # Landmark indices (update if using different model)
    LEFT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
    RIGHT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
    IRIS = [474, 475, 476, 477, 473, 469, 470, 471, 472, 468]

    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                continue

            # Process frame
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_frame)
            
            if results.multi_face_landmarks:
                for face in results.multi_face_landmarks:
                    # Convert landmarks to normalized input
                    try:
                        landmarks = face.landmark
                        left_center = np.mean([[landmarks[i].x, landmarks[i].y] for i in LEFT_EYE], axis=0)
                        right_center = np.mean([[landmarks[i].x, landmarks[i].y] for i in RIGHT_EYE], axis=0)
                        mid_point = (left_center + right_center) / 2.0
                        
                        normalized = np.array([[landmarks[i].x - mid_point[0],
                                              landmarks[i].y - mid_point[1]]
                                             for i in [*LEFT_EYE, *RIGHT_EYE, *IRIS]]).flatten()
                        input_data = np.array(normalized, dtype=np.float32).reshape(input_details[0]['shape'])
                        
                        # Run inference
                        interpreter.set_tensor(input_details[0]['index'], input_data)
                        interpreter.invoke()
                        output = interpreter.get_tensor(output_details[0]['index'])
                        
                        gesture = GESTURES[np.argmax(output[0])]
                        
                        # Send command if network is connected
                        if network.connected:
                            send_gesture(gesture)
                            handle_blink(gesture)
                        else:
                            print("Skipping command - network disconnected")

                    except Exception as e:
                        print(f"Processing error: {str(e)}")

            # Display FPS and connection status
            cv2.putText(frame, f"Connected: {network.connected}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if network.connected else (0, 0, 255), 2)
            cv2.imshow('Eye Control System', frame)
            
            if cv2.waitKey(1) == 27:
                break

    finally:
        network.stop()
        cap.release()
        cv2.destroyAllWindows()
        print("System shutdown complete")

if __name__ == "__main__":
    main()
