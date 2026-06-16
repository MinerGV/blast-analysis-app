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

controller_file = st.file_uploader("Upload Blaster 3000 Report (.txt)")
logger_file = st.file_uploader("Upload Logger Report (.txt)")
compare = st.checkbox("Compare Controller & Logger")

run = st.button("🔍 Summarise Now")

# -------------------------
# VOLTAGE CALC
# -------------------------
def calculate_voltage(status_id):
    try:
        hex_part = status_id[4:6]
        val = int(hex_part, 16)
        return round((val / 255) * 30, 2)
    except:
        return None

# -------------------------
# LOGGER PARSER
# -------------------------
def parse_logger(text):

    lines = text.split("\n")
    data = []

    for line in lines:
        match = re.search(
            r"(\d+)\s+([A-Z0-9]+)\s+(\d+)\s+ms\s+(\d+\.\d+)\s+mA\s+\((\w+)\)\s+Det\s+(\w+)",
            line
        )

        if match:
            det_id = match.group(2)
            timing = int(match.group(3))
            leakage = float(match.group(4))
            status_id = match.group(5)
            status = match.group(6)

            voltage = calculate_voltage(status_id)

            data.append({
                "Number": int(match.group(1)),
                "Detonator ID": det_id,
                "Timing (ms)": timing,
                "Leakage (mA)": leakage,
                "Status ID": status_id,
                "Status": status,
                "Voltage (V)": voltage
            })

    df = pd.DataFrame(data)

    return df

# -------------------------
# MAIN
# -------------------------
if run:

    report_text = ""

    # ---------------- LOGGER REPORT ----------------
    if logger_file:

        st.header("⚡ Logger Report")

        text = logger_file.read().decode("utf-8")
        df = parse_logger(text)

        # ✅ LOGGER HEADER (NEW)
        st.subheader("Logger Summary")

        total_dets = len(df)
        total_current = df["Leakage (mA)"].sum()

        st.write(f"**Total Detonators:** {total_dets}")
        st.write(f"**Total Leakage Current:** {round(total_current,2)} mA")

        # Voltage categories
        high = len(df[df["Voltage (V)"] >= 20])
        mid = len(df[(df["Voltage (V)"] >= 12) & (df["Voltage (V)"] < 20)])
        low = len(df[df["Voltage (V)"] < 12])

        if low == 0 and mid == 0:
            msg = "✅ All detonators have >20V and ready to fire"
            st.success(msg)
        else:
            msg = f"{high} ≥20V, {mid} (12–20V), {low} <12V"
            st.warning(msg)

        report_text += f"\nLOGGER REPORT\n{msg}\n"

        # ✅ TABLE
        st.dataframe(df)

        # ✅ 3 BAR HISTOGRAM
        fig, ax = plt.subplots()
        counts = [low, mid, high]
        labels = ["0–12 V", "12–20 V", "20+ V"]
        ax.bar(labels, counts)
        ax.set_ylabel("Number of Detonators")
        ax.set_title("Voltage Distribution")
        st.pyplot(fig)

        log_ids = set(df["Detonator ID"])

    # ---------------- BLASTER REPORT ----------------
    if controller_file:

        st.header("💥 Blaster 3000 Report")

        text = controller_file.read().decode("utf-8")

        # ✅ SUMMARY
        st.subheader("Summary")

        blasters = re.search(r"Blasters:\s*(\d+)", text)
        dets = re.search(r"Detonators:\s*(\d+)", text)
        errors = re.search(r"Detonator Errors:\s*(\d+)", text)

        st.write(f"Blasters used: {blasters.group(1) if blasters else 'N/A'}")
        st.write(f"Total detonators: {dets.group(1) if dets else 'N/A'}")
        st.write(f"Errors: {errors.group(1) if errors else '0'}")

        # ✅ ROLES
        st.subheader("Blaster Roles")
        roles = re.findall(r"(B\d+)\s*→\s*(.+)", text)

        for r in roles:
            st.write(f"{r[0]} → {r[1]}")
            report_text += f"{r[0]} → {r[1]}\n"

        # ✅ SERIAL + BATTERY + TIME
        st.subheader("Blaster Details")

        blaster_details = re.findall(
            r"Blaster ID:\s*(\d+).*?Serial No.:\s*(\d+).*?Battery:\s*(\d+)%.*?Fire.*at (.+)",
            text,
            re.S
        )

        df_blast = []

        for b in blaster_details:
            df_blast.append({
                "Blaster ID": b[0],
                "Serial": b[1],
                "Battery (%)": b[2],
                "Fire Time": b[3]
            })

        if df_blast:
            st.dataframe(pd.DataFrame(df_blast))

        # ✅ ABORT
        if "aborted" in text.lower():
            st.error("❌ Blast Aborted")

        ctrl_ids = set(re.findall(r"\b[A-Z0-9]{8}\b", text))

    # ---------------- COMPARISON ----------------
    if compare and controller_file and logger_file:

        st.header("🔄 Comparison")

        missing = ctrl_ids - log_ids
        extra = log_ids - ctrl_ids

        if missing:
            st.error("Missing Detonators")
            st.write(list(missing))

        if extra:
            st.warning("Extra Detonators")
            st.write(list(extra))

    # ✅ ✅ FIXED DOWNLOAD (works now)
    st.download_button(
        "⬇️ Download Report",
        data=report_text if report_text else "No data generated",
        file_name="blast_report.txt",
        mime="text/plain"
    )
