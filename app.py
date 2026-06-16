import streamlit as st
import re
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------
# ORICA HEADER
# -------------------------
try:
    st.image("orica_logo.png", width=180)
except:
    st.write("ORICA")

# -------------------------
# INPUTS
# -------------------------
controller_file = st.file_uploader("Upload Blaster 3000 Report (.txt)")
logger_file = st.file_uploader("Upload Logger Report (.txt)")
compare = st.checkbox("Compare Controller & Logger")

run = st.button("🔍 Summarise Now")

# -------------------------
# VOLTAGE CALCULATION
# -------------------------
def calculate_voltage(status_id):
    try:
        hex_part = status_id[4:6]
        decimal = int(hex_part, 16)
        voltage = (decimal / 255) * 30
        return round(voltage, 2)
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
            status_id = match.group(5)
            voltage = calculate_voltage(status_id)

            data.append({
                "Number": int(match.group(1)),
                "Detonator ID": match.group(2),
                "Timing (ms)": int(match.group(3)),
                "Leakage (mA)": float(match.group(4)),
                "Status ID": status_id,
                "Det Status": match.group(6),
                "Voltage (V)": voltage
            })

    df = pd.DataFrame(data)

    df["Category"] = df["Voltage (V)"].apply(
        lambda v: "✅ >20V" if v and v >= 20 else ("⚠️ 12–20V" if v and v >= 12 else "❌ <12V")
    )

    return df

# -------------------------
# CONTROLLER PARSER
# -------------------------
def parse_controller(text):

    summary = {
        "Blasters used": re.search(r"Blasters:\s*(\d+)", text),
        "Fire command received": re.search(r"Fire command received:\s*(\d+)", text),
        "Loggers": re.search(r"Loggers:\s*(.+)", text),
        "Total detonators": re.search(r"Detonators:\s*(\d+)", text),
        "Detonator Errors": re.search(r"Detonator Errors:\s*(\d+)", text)
    }

    summary = {k: (v.group(1) if v else "N/A") for k, v in summary.items()}

    roles = re.findall(r"(B\d+).*?(Controller|Remote.*)", text)

    # Aborted
    aborted = "aborted" in text.lower()
    abort_time = re.search(r"Abort.*at (.+)", text)
    abort_reason = re.search(r"Reason:\s*(.+)", text)

    return summary, roles, aborted, abort_time, abort_reason

# -------------------------
# MAIN EXECUTION
# -------------------------
if run:

    report_text = ""
    ctrl_ids = set()
    log_ids = set()

    # ---------------- TITLE LOGIC ----------------
    if controller_file and logger_file:
        st.title("Blast Report")
    elif controller_file:
        st.title("Blaster 3000 Report")
    elif logger_file:
        st.title("Logger Report")

    # ---------------- BLASTER ----------------
    if controller_file:

        st.header("💥 Blaster 3000 Report")

        text = controller_file.read().decode("utf-8")
        summary, roles, aborted, abort_time, abort_reason = parse_controller(text)

        st.subheader("Summary")
        for k, v in summary.items():
            st.write(f"**{k}:** {v}")
            report_text += f"{k}: {v}\n"

        st.subheader("Blaster Roles")
        for r in roles:
            st.write(f"{r[0]} → {r[1]}")
            report_text += f"{r[0]} → {r[1]}\n"

        if aborted:
            st.error("❌ Blast Aborted")
            report_text += "\nBlast Aborted\n"

            if abort_time:
                st.write(f"Abort Time: {abort_time.group(1)}")
                report_text += f"Abort Time: {abort_time.group(1)}\n"

            if abort_reason:
                st.write(f"Reason: {abort_reason.group(1)}")
                report_text += f"Reason: {abort_reason.group(1)}\n"

        ctrl_ids = set(re.findall(r"\b[A-Z0-9]{8}\b", text))

    # ---------------- LOGGER ----------------
    if logger_file:

        st.header("⚡ Logger Report")

        df = parse_logger(logger_file.read().decode("utf-8"))
        st.dataframe(df)

        voltages = df["Voltage (V)"].dropna()

        high = len(voltages[voltages >= 20])
        mid = len(voltages[(voltages >= 12) & (voltages < 20)])
        low = len(voltages[voltages < 12])

        st.subheader("Logger Summary")

        if low == 0 and mid == 0:
            msg = "✅ All detonators have received >20V and are ready to fire"
            st.success(msg)
        else:
            msg = f"{high} ≥20V, {mid} (12–20V), {low} <12V"
            st.warning(msg)

        report_text += f"\nLogger Summary:\n{msg}\n"

        # 3 BAR HISTOGRAM
        counts = [low, mid, high]
        labels = ["0–12 V", "12–20 V", "20+ V"]

        fig, ax = plt.subplots()
        ax.bar(labels, counts)
        ax.set_ylabel("Number of Detonators")
        ax.set_title("Voltage Distribution")
        st.pyplot(fig)

        log_ids = set(df["Detonator ID"])

    # ---------------- COMPARISON ----------------
    if compare and controller_file and logger_file:

        st.header("🔄 Comparison")

        missing = ctrl_ids - log_ids
        extra = log_ids - ctrl_ids

        if missing:
            st.error("Missing Detonators:")
            st.write(list(missing))
            report_text += f"\nMissing: {list(missing)}\n"

        if extra:
            st.warning("Extra Detonators:")
            st.write(list(extra))
            report_text += f"\nExtra: {list(extra)}\n"

    # ---------------- DOWNLOAD ----------------
    if st.button("📄 Generate Report"):

        if not report_text:
            report_text = "No data processed."

        st.download_button(
            label="⬇️ Download Report",
            data=report_text,
            file_name="blast_report.txt",
            mime="text/plain"
        )
