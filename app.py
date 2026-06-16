import streamlit as st
import re
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------
# HEADER (ORICA LOGO)
# -------------------------
try:
    st.image("orica_logo.png", width=180)
except:
    st.write("ORICA")

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

    summary = {
        "Blasters used": re.search(r"Blasters:\s*(\d+)", text),
        "Fire command received": re.search(r"Fire command received:\s*(\d+)", text),
        "Loggers": re.search(r"Loggers:\s*(.+)", text),
        "Total detonators": re.search(r"Detonators:\s*(\d+)", text),
        "Detonator Errors": re.search(r"Detonator Errors:\s*(\d+)", text)
    }

    summary = {k: (v.group(1) if v else "N/A") for k, v in summary.items()}

    roles = re.findall(r"(B\d+).*?(Controller|Remote.*)", text)

    blasters = re.findall(
        r"Blaster ID:\s*(\d+).*?Serial No.:\s*(\d+).*?Battery:\s*(\d+).*?Status:\s*(.+)",
        text, re.S
    )

    blaster_table = []
    for b in blasters:
        blaster_table.append({
            "Blaster ID": b[0],
            "Serial No": b[1],
            "Battery (%)": b[2],
            "Status": b[3]
        })

    logger_data = re.findall(
        r"Logger ID:\s*(\d+).*?Detonators:\s*(\d+).*?Detonator Errors:\s*(\d+).*?Current:\s*(\d+)mA",
        text, re.S
    )

    logger_table = []
    for l in logger_data:
        logger_table.append({
            "Logger ID": l[0],
            "Detonators": int(l[1]),
            "Errors": int(l[2]),
            "Current (mA)": int(l[3])
        })

    fire_time = re.search(r"Fire command sent at (.+)", text)

    return summary, roles, pd.DataFrame(blaster_table), pd.DataFrame(logger_table), (fire_time.group(1) if fire_time else "N/A")


# -------------------------
# LOGGER PARSER
# -------------------------
def parse_logger(text):

    lines = text.split("\n")
    data = []

    for i, line in enumerate(lines):
        match = re.search(
            r"(\d+)\s+([A-Z0-9]+)\s+(\d+)\s+ms\s+(\d+\.\d+)\s+mA\s+\((\w+)\)\s+Det\s+(\w+)",
            line
        )

        if match:
            try:
                voltage = float(lines[i + 1].strip())
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

    # Voltage classification
    df["Category"] = df["Voltage"].apply(
        lambda v: "✅ >20V" if v and v > 20 else ("⚠️ 14–20V" if v and v >= 14 else "❌ <14V")
    )

    return df


# -------------------------
# MAIN EXECUTION
# -------------------------
if run:

    ctrl_ids = set()
    log_ids = set()

    # ---------------- BLASTER REPORT ----------------
    if controller_file:

        st.header("💥 Blaster 3000 Report")

        text = controller_file.read().decode("utf-8")

        summary, roles, blaster_df, logger_df, fire_time = parse_controller(text)

        st.subheader("Summary")
        for k, v in summary.items():
            st.write(f"**{k}:** {v}")

        st.write(f"**Fire Timestamp:** {fire_time}")

        st.subheader("Blaster Roles")
        for r in roles:
            st.write(f"{r[0]} → {r[1]}")

        st.subheader("Blaster Details")
        st.dataframe(blaster_df)

        st.subheader("Logger Breakdown")
        st.dataframe(logger_df)

        ctrl_ids = set(re.findall(r"\b[A-Z0-9]{8}\b", text))

    # ---------------- LOGGER REPORT ----------------
    if logger_file:

        st.header("⚡ Logger Report")

        log_text = logger_file.read().decode("utf-8")
        df = parse_logger(log_text)

        st.dataframe(df)

        voltages = df["Voltage"].dropna()

        high = len(voltages[voltages > 20])
        mid = len(voltages[(voltages >= 14) & (voltages <= 20)])
        low = len(voltages[voltages < 14])

        st.subheader("Voltage Summary")

        if low == 0 and mid == 0:
            st.success("✅ All detonators have received >20V and are ready to fire")
        else:
            st.warning(f"{high} >20V, {mid} between 14–20V, {low} <14V")

        # Histogram FIXED
        fig, ax = plt.subplots()
        ax.hist(voltages, bins=20)
        ax.set_xlabel("Voltage")
        ax.set_ylabel("Count")
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

        if extra:
            st.warning("Extra Detonators:")
            st.write(list(extra))

    # ---------------- REPORT BUTTON ----------------
    if st.button("📄 Generate Report"):

        if logger_file and controller_file:
            st.success("✅ Report: Blast Report (Blaster + Logger)")
        elif logger_file:
            st.success("✅ Report: Logger Report")
        elif controller_file:
            st.success("✅ Report: Blaster 3000 Report")
