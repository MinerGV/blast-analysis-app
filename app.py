import streamlit as st
import re
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------
# 🔐 LOGIN SYSTEM
# -------------------------
def check_password():

    def password_entered():
        if st.session_state["password"] == "LOGGER":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔐 Enter Passcode", type="password", on_change=password_entered, key="password")
        return False

    if not st.session_state["password_correct"]:
        st.text_input("🔐 Enter Passcode", type="password", on_change=password_entered, key="password")
        st.error("❌ Incorrect Passcode")
        return False

    return True

# Stop if not logged in
if not check_password():
    st.stop()

# -------------------------
# HEADER
# -------------------------
try:
    st.image("orica_logo.png", width=180)
except:
    st.write("ORICA")

st.title("⚡ Logger Report Analyzer")

# -------------------------
# INPUT
# -------------------------
logger_file = st.file_uploader("Upload Logger Report (.txt)")
run = st.button("🔍 Summarise Now")

# -------------------------
# VOLTAGE CALC
# -------------------------
def calculate_voltage(status_id):
    try:
        hex_part = status_id[4:6]
        decimal = int(hex_part, 16)
        return round((decimal / 255) * 30, 2)
    except:
        return None

# -------------------------
# LEGWIRE MAP
# -------------------------
legwire_map = {
    "1": 3, "2": 4, "3": 6, "4": 10, "5": 15,
    "6": 20, "7": 30, "8": 40, "9": 60,
    "A": 80, "B": 100
}

def get_legwire(det_id):
    return legwire_map.get(det_id[1].upper(), 0)

# -------------------------
# TYPE MAP
# -------------------------
def get_type(det_id):
    if det_id[0] in ["2", "3"]:
        return "i-kon"
    elif det_id[0] in ["6", "7"]:
        return "eDev"
    return "Unknown"

# -------------------------
# PARSER
# -------------------------
def parse_logger(text):

    # -------- HEADER --------
    timestamp = re.search(r"Date:\s*(.+)", text)
    logger_id = re.search(r"Logger ID:\s*(\d+)", text)
    serial = re.search(r"Serial No.:\s*(\d+)", text)
    mode = re.search(r"Mode:\s*(\w+)", text)
    battery = re.search(r"Battery:\s*(\d+%)", text)
    fw_gui = re.search(r"FW Version - GUI:\s*([\d\.]+)", text)
    det_logged = re.search(r"Detonators logged:\s*(\d+)", text)

    fire_flags = re.search(r"\*\* fire command sent \*\*.*", text)
    current = re.search(r"Current:\s*([\d\.]+ mA)", text)

    # -------- DET TABLE --------
    data = []

    for line in text.split("\n"):
        match = re.search(
            r"(\d+)\s+([A-Z0-9]+)\s+(\d+)\s+ms\s+(\d+\.\d+)\s+mA\s+\((\w+)\)\s+Det\s+(\w+)",
            line
        )

        if match:
            det_id = match.group(2)
            status_id = match.group(5)

            voltage = calculate_voltage(status_id)
            det_type = get_type(det_id)
            legwire = get_legwire(det_id)

            # CATEGORY
            if voltage is None:
                category = "Unknown"
            elif voltage >= 20:
                category = "✅ >20V"
            elif voltage >= 12:
                category = "⚠️ 12–20V"
            else:
                category = "❌ <12V"

            data.append({
                "Number": int(match.group(1)),
                "Detonator ID": det_id,
                "Timing (ms)": int(match.group(3)),
                "Leakage (mA)": float(match.group(4)),
                "Status ID": status_id,
                "Status": match.group(6),
                "Voltage (V)": voltage,
                "Category": category,
                "Type": det_type,
                "Legwire (m)": legwire
            })

    df = pd.DataFrame(data)

    return {
        "timestamp": timestamp.group(1) if timestamp else "N/A",
        "logger_id": logger_id.group(1) if logger_id else "N/A",
        "serial": serial.group(1) if serial else "N/A",
        "mode": mode.group(1) if mode else "N/A",
        "battery": battery.group(1) if battery else "N/A",
        "fw_gui": fw_gui.group(1) if fw_gui else "N/A",
        "det_logged": det_logged.group(1) if det_logged else "N/A",
        "fire_flags": fire_flags.group(0) if fire_flags else "N/A",
        "current": current.group(1) if current else "N/A",
        "table": df
    }

# -------------------------
# MAIN
# -------------------------
if run and logger_file:

    parsed = parse_logger(logger_file.read().decode("utf-8"))
    df = parsed["table"]

    # ✅ LOGGER SUMMARY
    st.header("⚡ Logger Summary")

    st.write(f"**Timestamp:** {parsed['timestamp']}")
    st.write(f"**Serial No.:** {parsed['serial']}")
    st.write(f"**Logger ID:** {parsed['logger_id']}")
    st.write(f"**Mode:** {parsed['mode']}")
    st.write(f"**Battery:** {parsed['battery']}")
    st.write(f"**Firmware (GUI):** {parsed['fw_gui']}")
    st.write(f"**Detonators Logged:** {parsed['det_logged']}")
    st.write(f"**Fire Command:** {parsed['fire_flags']}")
    st.write(f"**Total Current:** {parsed['current']}")

    # -------- ENGINEERING SUMMARY --------
    total = len(df)
    ikon = len(df[df["Type"] == "i-kon"])
    edev = len(df[df["Type"] == "eDev"])

    high = len(df[df["Voltage (V)"] >= 20])
    mid = len(df[(df["Voltage (V)"] >= 12) & (df["Voltage (V)"] < 20)])
    low = len(df[df["Voltage (V)"] < 12])

    total_legwire = df["Legwire (m)"].sum()

    st.write(f"**Total Detonators:** {total}")
    st.write(f"**i-kon:** {ikon} | **eDev:** {edev}")

    if low == 0 and mid == 0:
        st.success("✅ All detonators >20V and ready to fire")
    else:
        st.warning(f"{high} >20V, {mid} (12–20V), {low} <12V")

    st.write(f"**Total Legwire:** {total_legwire} m")

    # ✅ TABLE
    st.subheader("📊 Detonator Details")
    st.dataframe(df)

    # ✅ HISTOGRAM
    st.subheader("📉 Voltage Distribution")

    counts = [low, mid, high]
    labels = ["0–12 V", "12–20 V", "20+ V"]

    fig, ax = plt.subplots()
    ax.bar(labels, counts)
    ax.set_ylabel("Number of Detonators")
    st.pyplot(fig)

    # ✅ DOWNLOAD
    report_text = f"""
LOGGER REPORT
Timestamp: {parsed['timestamp']}
Serial: {parsed['serial']}
Logger ID: {parsed['logger_id']}
Mode: {parsed['mode']}
Battery: {parsed['battery']}
Firmware: {parsed['fw_gui']}

Total Detonators: {total}
i-kon: {ikon}, eDev: {edev}
Voltage: {high} >20V, {mid} mid, {low} low
Total Legwire: {total_legwire} m
"""

    st.download_button(
        "⬇️ Download Logger Report",
        data=report_text,
        file_name="logger_summary.txt",
        mime="text/plain"
    )
