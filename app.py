import streamlit as st
import re
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------
# ORICA HEADER
# -------------------------
st.image("https://upload.wikimedia.org/wikipedia/commons/6/6e/ORICA_logo.png", width=180)
st.title("Blaster 3000 Analysis Tool")

# -------------------------
# INPUTS
# -------------------------
controller_file = st.file_uploader("Upload Blaster 3000 Report (.txt)")
logger_file = st.file_uploader("Upload Logger Report (.txt)")
compare = st.checkbox("Compare Controller & Logger")

run = st.button("🔍 Summarise Now")

# -------------------------
# CONTROLLER PARSER
# -------------------------
def parse_controller(text):
    blaster_ids = re.findall(r"Blaster ID:\s*(\d+)", text)
    logger_ids = re.findall(r"Logger ID:\s*(\d+)", text)

    fire_time = re.search(r"Fire command sent at (.+)", text)
    errors = re.search(r"Detonator Errors:\s*(\d+)", text)

    logger_data = []

    loggers = re.findall(r"Logger ID:\s*(\d+).*?Detonators:\s*(\d+).*?Detonator Errors:\s*(\d+).*?Current:\s*(\d+)mA", text, re.S)

    for l in loggers:
        logger_data.append({
            "Logger ID": l[0],
            "Detonators": int(l[1]),
            "Errors": int(l[2]),
            "Current (mA)": int(l[3])
        })

    return {
        "Blasters": blaster_ids,
        "Fire Time": fire_time.group(1) if fire_time else "N/A",
        "Errors": errors.group(1) if errors else "0",
        "Logger Table": pd.DataFrame(logger_data)
    }


# -------------------------
# LOGGER PARSER
# -------------------------
def parse_logger(text):
    lines = text.split("\n")

    data = []

    for i, line in enumerate(lines):
        match = re.search(r"(\d+)\s+([A-Z0-9]+)\s+(\d+)\s+ms\s+(\d+\.\d+)\s+mA\s+\((\w+)\)\s+Det\s+(\w+)", line)
        if match:
            try:
                voltage = float(lines[i+1].strip())
            except:
                voltage = None

            data.append({
                "Number": int(match.group(1)),
                "Detonator ID": match.group(2),
                "Timing (ms)": int(match.group(3)),
                "Leakage (mA)": float(match.group(4)),
                "Status ID": match.group(5),
                "Det Status": match.group(6),
                "Voltage": voltage
            })

    df = pd.DataFrame(data)

    return df


# -------------------------
# MAIN EXECUTION
# -------------------------
if run:

    ctrl_ids = set()
    log_ids = set()

    # -------- CONTROLLER --------
    if controller_file:
        st.subheader("💥 Blaster 3000 Report")

        ctrl_text = controller_file.read().decode("utf-8")
        ctrl = parse_controller(ctrl_text)

        st.write(f"**Blaster IDs:** {ctrl['Blasters']}")
        st.write(f"**Fire Time:** {ctrl['Fire Time']}")
        st.write(f"**Total Errors:** {ctrl['Errors']}")

        st.write("### Logger Breakdown")
        st.dataframe(ctrl["Logger Table"])

        # collect IDs if comparison needed
        ctrl_ids = set(re.findall(r"\b[A-Z0-9]{8}\b", ctrl_text))

    # -------- LOGGER --------
    if logger_file:
        st.subheader("⚡ Logger Report")

        log_text = logger_file.read().decode("utf-8")
        df = parse_logger(log_text)

        st.dataframe(df)

        voltages = df["Voltage"].dropna()

        high = len(voltages[voltages > 20])
        mid = len(voltages[(voltages >= 14) & (voltages <= 20)])
        low = len(voltages[voltages < 14])

        st.write("### Voltage Summary")

        if low == 0 and mid == 0:
            st.success("✅ All detonators have received >20V and are ready to fire")
        else:
            st.warning(f"{high} >20V, {mid} between 14–20V, {low} <14V")

