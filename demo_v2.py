import time
import sys
import re  
import numpy as np
import matplotlib.pyplot as plt

# Try to import serial, provide a helpful error if missing
try:
    import serial
except ImportError:
    print("Error: 'pyserial' library not found. Please install it using: pip install pyserial")
    sys.exit(1)

# --- Configuration Constants ---
SERIAL_PORT = 'COM4'  # Change to your actual STM32 port
BAUD_RATE = 115200
SAMPLE_DURATION_SEC = 30

def count_cycles_dsp(data_list, sensor_name):
    """
    DSP Noise Reduction via Moving Average and First-Derivative Peak Detection[cite: 31, 32, 73].
    Returns the cycle count and the raw/processed signal arrays for fusion analysis.
    """
    if len(data_list) < 26:
        return 0, np.array([]), np.array([])

    cycles = 0
    detect_indices = []
    
    # 1. Low-Pass Moving Average Filter (Noise Reduction) [cite: 32, 73]
    w = 25
    processed_data = np.convolve(data_list, np.ones(w), "valid") / w
    
    # 2. First Derivative / Zero-Crossing Peak Detection
    prev_diff = 0
    posCount = 0

    for i in range(len(processed_data) - 1):
        diff = processed_data[i+1] - processed_data[i]
        
        # Identify crest peak transition (slope swaps from positive to negative)
        if ((prev_diff >= 0 and diff < 0) or (prev_diff > 0 and diff <= 0)) and posCount > 5:
            cycles += 1
            detect_indices.append(i)
        
        prev_diff = diff

        if diff > 0:
            posCount += 1
        elif diff < 0:
            posCount = 0

    # 3. Dynamic Visual Plotting (Isolated Subplots to prevent code freezing)
    plt.figure(sensor_name)
    x = np.arange(0, len(processed_data), 1)
    plt.plot(x, processed_data, label=f'Filtered {sensor_name}')
    
    if detect_indices:
        plt.scatter(x[detect_indices], processed_data[detect_indices], color='red', marker='x', label='Peaks')
    
    plt.title(f"{sensor_name} DSP Analysis")
    plt.xlabel("Samples")
    plt.ylabel("ADC Amplitude")
    plt.legend()
    plt.draw() # Renders without freezing the script pipeline

    return cycles, np.array(data_list), processed_data


def run_data_fusion(ch1_cycles, raw_ch1, ch2_cycles, raw_ch2):
    """
    Decision-Level Data Fusion using Adaptive Variance Weighting[cite: 33, 88].
    Penalizes a sensor channel if body-movement artifacts introduce heavy noise[cite: 21, 88].
    """
    # Calculate variance of the first derivative to capture erratic movement spikes
    noise_ch1 = np.var(np.diff(raw_ch1)) if len(raw_ch1) > 1 else 1.0
    noise_ch2 = np.var(np.diff(raw_ch2)) if len(raw_ch2) > 1 else 1.0
    
    # Invert noise to get a quality metric weight (Lower noise = Higher weight)
    w1 = 1.0 / (1.0 + 0.01 * noise_ch1)
    w2 = 1.0 / (1.0 + 0.01 * noise_ch2)
    
    # Handle absolute dead/corrupted signal configurations safely
    if (w1 + w2) == 0:
        return int(round((ch1_cycles + ch2_cycles) / 2))
        
    # Apply Mathematical Weighted Average Fusion 
    fused_cycles = (w1 * ch1_cycles + w2 * ch2_cycles) / (w1 + w2)
    
    print(f"\n--- Data Fusion Metrics ---")
    print(f" > CH1 (Thermistor) Reliability Weight: {w1:.2f}")
    print(f" > CH2 (Conductive Rubber) Reliability Weight: {w2:.2f}")
    
    return int(round(fused_cycles))


def main():
    ch1_buffer = []
    ch2_buffer = []
    
    # Regex pattern to clean digits from CH1 and CH2 streams robustly
    data_pattern = re.compile(r"CH1\s*=\s*(\d+)\s*,\s*CH2\s*=\s*(\d+)", re.IGNORECASE)
    
    print(f"Connecting to STM32 on {SERIAL_PORT}...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        ser.reset_input_buffer() 
    except Exception as e:
        print(f"Failed to open serial port {SERIAL_PORT}. Error: {e}")
        return

    print(f"\n--- Starting {SAMPLE_DURATION_SEC}-Second Breath Data Collection ---")
    
    start_time = time.time()
    end_time = start_time + SAMPLE_DURATION_SEC
    
    while time.time() < end_time:
        if ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                match = data_pattern.search(line)
                
                if match:
                    print(f"{line} | Time Remaining: {int(end_time - time.time())}s")
                    
                    ch1_val = int(match.group(1))
                    ch2_val = int(match.group(2))
                    
                    ch1_buffer.append(ch1_val)
                    ch2_buffer.append(ch2_val)
            except Exception:
                continue

    ser.close()
    print("\n--- Time Limit Reached. Running Multi-Channel DSP Data Analysis... ---")
    
    if not ch1_buffer or not ch2_buffer:
        print("Error: No valid data points were captured.")
        return

    # --- Turn on Interactive Plotting Mode ---
    plt.ion()

    # --- Step 1: Run Separate DSP Pipelines ---
    ch1_cycles, raw_ch1, proc_ch1 = count_cycles_dsp(ch1_buffer, "CH1 Thermistor")
    ch2_cycles, raw_ch2, proc_ch2 = count_cycles_dsp(ch2_buffer, "CH2 Conductive Rubber")
    
    # --- Step 2: Run Intelligent Data Fusion ---
    fused_total_cycles = run_data_fusion(ch1_cycles, raw_ch1, ch2_cycles, raw_ch2)

    # --- Step 3: Performance Assessment Summary ---
    print("\n" + "="*50)
    print("         TRC3500 BREATHWELL™ LAB REPORT SUMMARY")
    print("="*50)
    print(f"Total Raw Data Stream Samples Logged: {len(ch1_buffer)}")
    print(f"CH1 (TMP61 Thermistor) Peak Cycles   : {ch1_cycles}")
    print(f"CH2 (Conductive Rubber) Peak Cycles  : {ch2_cycles}")
    print("-"*50)
    print(f"INTELLIGENT FUSED TOTAL BREATH CYCLES: {fused_total_cycles}")
    print(f"Estimated Respiratory Rate           : {fused_total_cycles * 2} Breaths/Min")
    print("="*50)

    # Keep visualization windows active at the end of execution
    print("\n[Notice] Close graph windows manually to exit script.")
    plt.show(block=True)

if __name__ == "__main__":
    main()