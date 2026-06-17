import streamlit as st
import re
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------
# LOGO
# -------------------------
try:
    st.image("orica_logo.png", width=180)
except:
    st.write("ORICA")

st.title("Logger Report Analyzer")

# -------------------------
# INPUT
# -------------------------
logger_file = st.file_uploader("Upload Logger Report (.txt)")

run = st.button("🔍 Summarise Now")

# -------------------------
# VOLTAGE CALCULATION
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

# -------------------------
# TYPE MAP
# -------------------------
def get_type(det_id):
    first = det_id[0]
    if first in ["2", "3"]:
        return "i-kon"
    elif first in ["6", "7"]:
        return "eDev"
    else:
        return "Unknown"

# -------------------------
# LEGWIRE FUNCTION
# -------------------------
def get_legwire(det_id):
    second = det_id[1].upper()
    return legwire_map.get(second, 0)

# -------------------------
# PARSER
# -------------------------
def parse_logger(text):

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

            # Category
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

    return pd.DataFrame(data)

# -------------------------
# MAIN
# -------------------------
if run and logger_file:

    text = logger_file.read().decode("utf-8")
    df = parse_logger(text)

    report_text = ""

    # ✅ SUMMARY
    st.header("⚡ Logger Summary")

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
        msg = "✅ All detonators >20V and ready to fire"
        st.success(msg)
    else:
        msg = f"{high} >20V, {mid} (12–20V), {low} <12V"
        st.warning(msg)

    st.write(f"**Total Legwire:** {total_legwire} m")

    report_text += f"Total Dets: {total}\n"
    report_text += f"i-kon: {ikon}, eDev: {edev}\n"
    report_text += f"{msg}\n"
    report_text += f"Total Legwire: {total_legwire} m\n"

    # ✅ TABLE
    st.subheader("📊 Detonator Details")
    st.dataframe(df)

    # ✅ HISTOGRAM (3 BARS)
    st.subheader("📉 Voltage Distribution")

    counts = [low, mid, high]
    labels = ["0–12 V", "12–20 V", "20+ V"]

    fig, ax = plt.subplots()
    ax.bar(labels, counts)
    ax.set_ylabel("Number of Detonators")
    st.pyplot(fig)

    # ✅ DOWNLOAD
    st.download_button(
        label="⬇️ Download Logger Report",
        data=report_text,
        file_name="logger_report.txt",
        mime="text/plain"
    )
