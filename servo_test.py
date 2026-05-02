import time
import sys

try:
    from adafruit_servokit import ServoKit
except ImportError:
    print("[ERROR] adafruit-circuitpython-servokit library not found.")
    print("Please run: pip install adafruit-circuitpython-servokit")
    sys.exit(1)

# Initialize the PCA9685
try:
    kit = ServoKit(channels=16)
    print("[SUCCESS] PCA9685 Servo Driver connected via I2C.")
except Exception as e:
    print(f"[FATAL ERROR] Could not connect to PCA9685: {e}")
    print("Check your I2C wiring (SDA/SCL) and ensure Pi I2C is enabled.")
    sys.exit(1)

# Your specific servo channel mapping
PAN_CHANNELS = [0, 4]   # Left and Right Horizontal
TILT_CHANNELS = [1, 5]  # Left and Right Vertical
LID_CHANNELS = [2, 6]   # Left and Right Eyelids

# Default resting positions
DEFAULTS = {0: 90, 1: 90, 2: 140, 4: 90, 5: 90, 6: 140}

def set_angle(channels, angle):
    """Moves multiple servos to the exact same angle safely."""
    for ch in channels:
        try:
            kit.servo[ch].angle = max(0.0, min(180.0, float(angle)))
        except Exception as e:
            print(f"[WARNING] Failed to move servo on channel {ch}: {e}")

def smooth_sweep(channels, start, end, step_delay=0.01):
    """Moves servos smoothly from start to end angle."""
    step = 1 if start < end else -1
    for angle in range(start, end + step, step):
        set_angle(channels, angle)
        time.sleep(step_delay)

def reset_all():
    print("Resetting all servos to default forward position...")
    for ch, ang in DEFAULTS.items():
        try:
            kit.servo[ch].angle = ang
        except:
            pass
    time.sleep(0.5)

print("\n--- STARTING SERVO DIAGNOSTIC TEST ---")
print("Press CTRL+C at any time to stop the test and reset servos.\n")

try:
    reset_all()

    while True:
        print("1. Testing Pan (Left/Right) ...")
        smooth_sweep(PAN_CHANNELS, 90, 65)   # Look Left
        time.sleep(0.5)
        smooth_sweep(PAN_CHANNELS, 65, 115)  # Look Right
        time.sleep(0.5)
        smooth_sweep(PAN_CHANNELS, 115, 90)  # Center
        time.sleep(1)

        print("2. Testing Tilt (Up/Down) ...")
        smooth_sweep(TILT_CHANNELS, 90, 65)   # Look Up
        time.sleep(0.5)
        smooth_sweep(TILT_CHANNELS, 65, 115)  # Look Down
        time.sleep(0.5)
        smooth_sweep(TILT_CHANNELS, 115, 90)  # Center
        time.sleep(1)

        print("3. Testing Eyelids (Blink) ...")
        set_angle(LID_CHANNELS, 90)  # Close
        time.sleep(0.3)
        set_angle(LID_CHANNELS, 140) # Open
        time.sleep(0.3)
        set_angle(LID_CHANNELS, 90)  # Close
        time.sleep(0.3)
        set_angle(LID_CHANNELS, 140) # Open
        time.sleep(2)

except KeyboardInterrupt:
    print("\n[STOPPED] User interrupted the test.")
except Exception as e:
    print(f"\n[ERROR] An unexpected error occurred: {e}")
finally:
    reset_all()
    print("Test finished. Servos parked safely.")