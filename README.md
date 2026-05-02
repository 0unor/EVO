# EVO Project: Usage & Configuration Guide

This guide explains how to start, calibrate, and control your Enhanced Vision Operative (EVO) system. 

## 1. Starting the System

Before starting, ensure all hardware (Raspberry Pi, PCA9685 Servo Driver, Camera, and Relay) is properly connected and powered. 

To start the EVO software, open your terminal, activate your Python virtual environment, and run the main script:
```bash
python EVO_App.py
```

The terminal will confirm that the camera, I2C servos, and GPIO relay have successfully initialized. 

## 2. Accessing the Web Interface

EVO features a built-in web server for telemetry and control. To access it:
1. Find your Raspberry Pi's local IP address (e.g., `192.168.0.x`).
2. Open a web browser on any device connected to the same Wi-Fi network.
3. Navigate to the Admin Panel: `http://<YOUR_PI_IP>:5000/admin`

*Note: You can also access the user-facing screen tracking panel at `http://<YOUR_PI_IP>:5000/` or `http://<YOUR_PI_IP>:5000/szemvezerles`.*

---

## 3. Core Features & Controls

### A. Automatic Robotic Eye Tracking
By default, the robotic eyes will instantly start following your face using the camera. 
* The system calculates the "pure" iris-to-eye ratio to snap the servos to your gaze direction (Left, Right, Up, Down).
* **Blinking:** The robotic eyelids will automatically close when you blink.

### B. The Admin Web Panel (HUD)
The `/admin` webpage provides real-time control over the physical robot:
* **Manual Joysticks:** Drag the on-screen joysticks to move the servos manually. 
  * *Override Feature:* Using the joysticks automatically pauses the camera's face-tracking for 3 seconds so the motors don't fight your manual inputs.
  * *Link Eyes:* Toggle the "🔗 LINK EYES" button to control both eyes simultaneously with one joystick.
* **Sensitivity Sliders:** Adjust how easily the robotic eyes look around:
  * Decrease the threshold numbers to make the eyes highly sensitive to small eye movements.
  * Increase the threshold numbers if the eyes are twitching or triggering too easily.
* **Manual Relay Button:** Click the "⚡ MANUAL RELAY" button to toggle the GPIO 17 device (e.g., turning on a lamp or motor). 

### C. Screen Cursor & 9-Point Calibration
If you want to use your eyes to control the yellow cursor on the screen (to click digital buttons):
1. Upon startup (or by clicking "Start Calibration" in the Admin panel), look at the yellow dot on the screen.
2. Blink once to begin.
3. Keep your head still and follow the dot with your eyes through all 9 points. 
4. Once calibrated, hover the yellow cursor over the on-screen UI buttons.
5. **Triggering:** Blink exactly **3 times** within 1.5 seconds while hovering over a button to activate it (this is hardcoded to toggle the physical Relay).

---

## 4. Developer Tips & Troubleshooting

* **Disabling Start-up Calibration:** If you only want to test the physical servos and don't care about the on-screen cursor, you can disable the mandatory start-up calibration. Open `EVO_App.py`, find `calibration_mode = True`, and change it to `False`.
* **Lighting:** MediaPipe requires decent lighting to track the pupils accurately. If the servos are acting erratically, ensure your face is well-lit and there is no heavy backlight blinding the camera.
* **Servo Diagnostics:** If a motor stops working, run the standalone `servo_test.py` script to sweep all motors through their safe ranges and verify power delivery.
* **I2C Errors:** If the terminal spams I2C or PCA9685 errors, check your SDA/SCL wire connections between the Raspberry Pi and the servo driver board.
