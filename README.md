# PROJECT3_BreathRateSensor

# BreatheWell™: Multi-Sensor Breath-Rate Monitoring System

An advanced embedded perception and data fusion pipeline developed for the **TRC3500 Sensors and Artificial Perception** project (Semester 1, Monash University Malaysia). This system overcomes the environmental and motion vulnerabilities of single-sensor biometric monitors by intelligently fusing real-time digital streams from two complementary hardware channels.

---

##  Project Overview

Single-sensor breath-rate monitors are highly susceptible to tracking failures during physical movement, environmental noise, or displacement artifacts. **BreatheWell™** solves this by combining two distinct physiological sensing modalities:
1. **CH1: TMP61 Thermistor** – Detects thermal shifts caused by inhalation and exhalation cycles near the face.
2. **CH2: Conductive Rubber Cord** – Measures physical chest/abdominal expansion and strain via an adjustable body harness.

The companion Python application establishes a high-speed serial pipeline with an STM32 microcontroller, isolates environmental noise using a low-pass moving average filter, extracts breath cycles through peak-crest velocity analysis, and applies **Adaptive Variance Decision-Level Fusion** to compute an optimized, error-resistant respiratory rate.

---

## 🛠️ System Architecture

### 1. Embedded Data Acquisition
* **Microcontroller:** STM32 handles real-time multiplexed analog-to-digital conversions (ADC).
* **Serial Telemetry:** Cleansed telemetry strings are broadcast over USB UART at `115200` baud using the structured packet format:  
  `CH1=XXXX, CH2=YYYY`

### 2. Digital Signal Processing (DSP) Pipeline
To clean the raw ADC inputs before calculation, each channel passes through a standalone DSP sequence:
* **Noise Reduction:** A sliding-window convolution filter ($w = 25$) acts as a digital low-pass filter, suppressing high-frequency hardware jitters and circuit noise.
* **Peak Detection:** Rather than relying on rigid, static voltage thresholds, the algorithm tracks the signal's **first derivative (velocity change)**. A breath cycle is registered at the exact moment the slope transitions from positive to negative (zero-crossing point), guarded by a 5-sample rising refractory lockout to prevent double-counting.

### 3. Adaptive Decision-Level Data Fusion
Instead of a simple average—which would corrupt data if one sensor encounters high noise—the system calculates the **moving variance of each signal's derivative**. 
* **Resting Phase:** Both signals remain clean and stable. The system assigns balanced weights ($w_1 \approx 1.0, w_2 \approx 1.0$), splitting the calculation evenly between both sensors.
* **Heavy Exercise Phase:** Physical body movements introduce massive motion artifacts into the Conductive Rubber channel, causing its variance to spike. The fusion algorithm automatically penalizes its reliability weight ($w_2 \to 0$), seamlessly shifting tracking reliance to the facial thermistor to preserve system accuracy.

$$BR_{fused} = \frac{w_{1} \cdot BR_{therm} + w_{2} \cdot BR_{rubber}}{w_{1} + w_{2}}$$

---

##  Getting Started

### Prerequisites
Ensure you have Python 3.8+ and the required scientific computing dependencies installed:
```bash
pip install pyserial numpy matplotlib
