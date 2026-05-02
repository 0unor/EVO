![image](https://github.com/user-attachments/assets/76ff31b1-9cc6-44d0-becf-12b7d4777c97)

## EVO Project – README

EVO (Enhanced Vision Operative) is an open-source, modular animatronic eye prototype that combines eye-tracking, voice control, and artificial intelligence to elevate user interactions to a new level. The project's goal is to create a cost-effective, customizable platform that can be utilized in medical, industrial, or educational applications.

---

## Key Features

- **Real-time eye tracking**: Camera-based tracking using MediaPipe and TensorFlow Lite, with local processing (on a Raspberry Pi 4).
- **Hybrid control**: A combination of eye and voice control (e.g., the eyes turn upon the command "Look left!").
- **Modular hardware**: Easily expandable with new sensors (e.g., LIDAR, temperature sensor) or actuators (e.g., robotic arm).
- **Cost-effectiveness**: Significantly cheaper than market alternatives, low maintenance costs, and repairable with DIY components.
- **Open source**: Full access to Python and TensorFlow code, allowing for free customization.

---

## Hardware Requirements

- **Microcontroller**: Raspberry Pi 5
- **Servo motors**: 6× MG996R (for eye movement simulation)
- **Controller**: PCA9685 servo driver
- **Camera**: USB or Raspberry Pi compatible camera
- **Motion sensor**: Ultrasonic sensor (not implemented yet)
- **Microphone module**: For voice control (not implemented yet)

---

## Software Requirements

- **Python 3.x**
- **MediaPipe**
- **OpenCV**
- **GPIO libraries (for Raspberry Pi)**

---

## Installation

1. Clone the repository:
   ```bash
   git clone [https://github.com//EVO.git](https://github.com//EVO.git)
   ```
2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Connect the hardware components according to the documentation.
4. Start the control script:
   ```bash
   python main.py
   ```

---

## Development Roadmap (Excerpt)

- **Month 1**: Basic research, system design, hardware selection, and software design development
- **Month 2**: Hardware and software prototype development, and AI module integration
- **Month 3**: Development of interactive features, machine learning, and adaptive responses
- **Month 4**: User testing, documentation, and determining further development directions

---

## Use Cases

- Medical assistive devices (e.g., interaction for physically disabled individuals, potentially for ALS in the future)
- Industrial automation (attention tracking, error reduction)
- Education (interactive learning platforms)
- Human-computer interaction (HCI) research

---

## Contributing

We welcome community contributions! Bugs, ideas, or new modules can be submitted in the form of pull requests.

---

## License

This project is open-source; the license details can be found in the LICENSE file.

---

## Contact

Creator: Deák Hunor
Questions or comments: [deakhunor14@gmail.com]

---

> "People don't believe what they see; they see what they believe."
