import streamlit as st
import re
import pandas as pd

# -------------------------
# LOGO
# -------------------------
try:
    st.image("orica_logo.png", width=180)
except:
    st.write("ORICA")

st.title("Blaster 3000 Report Analyzer")

# -------------------------
# INPUT
# -------------------------
controller_file = st.file_uploader("Upload Blaster 3000 Report (.txt)")

run = st.button("🔍 Summarise Now")

# -------------------------
# PARSER FUNCTION
# -------------------------
def parse_blaster(text):

    # -------- SUMMARY --------
    summary = {
        "Blasters used": re.search(r"Blasters:\s*(\d+)", text),
        "Fire command received": re.search(r"Fire command received:\s*(\d+)", text),
        "Loggers": re.search(r"Loggers:\s*(.+)", text),
        "Total detonators": re.search(r"Detonators:\s*(\d+)", text),
        "Detonator Errors": re.search(r"Detonator Errors:\s*(\d+)", text)
    }

    summary = {k: (v.group(1) if v else "N/A") for k, v in summary.items()}

    # -------- STATUS --------
    fire_time = re.search(r"Fire command sent at (.+)", text)
    abort_time = re.search(r"Aborted at (.+)", text)
    abort_stage = re.search(r"in sequence:\s*(.+)", text)
    abort_reason = re.search(r"Reason:\s*(.+)", text)

    # Determine status
    if fire_time:
        status = "FIRED"
        time = fire_time.group(1)
    elif abort_time:
        status = "ABORTED"
        time = abort_time.group(1)
    else:
        status = "UNKNOWN"
        time = "N/A"

    # -------- ROLES --------
    roles = re.findall(r"(B\d+)\s+(Controller|Remote.*)", text)

    # -------- BLASTER DETAILS --------
    blaster_blocks = re.findall(
        r"Blaster ID:\s*(\d+).*?Serial No.:\s*(\d+).*?Status:\s*(.+?)\s+Loggers:.*?Battery:\s*(\d+)\s*%.*?Current:\s*(\S+)",
        text,
        re.S
    )

    blaster_table = []
    for b in blaster_blocks:
        blaster_table.append({
            "Blaster ID": b[0],
            "Serial No": b[1],
            "Status": b[2],
            "Battery (%)": b[3],
            "Current": b[4]
        })

    # -------- LOGGER DETAILS --------
    logger_blocks = re.findall(
        r"Logger ID:\s*(\d+).*?Serial No.:\s*(\d+).*?Status:\s*(\w+).*?Detonators:\s*(\d+).*?(?:Detonator Errors:\s*(\d+))?.*?Current:\s*(\S+)",
        text,
        re.S
    )

    logger_table = []
    for l in logger_blocks:
        logger_table.append({
            "Logger ID": l[0],
            "Serial No": l[1],
            "Status": l[2],
            "Detonators": l[3],
            "Errors": l[4] if l[4] else "0",
            "Current": l[5]
        })

    return summary, status, time, abort_stage, abort_reason, roles, pd.DataFrame(blaster_table), pd.DataFrame(logger_table)


# -------------------------
# MAIN EXECUTION
# -------------------------
if run and controller_file:

    text = controller_file.read().decode("utf-8")

    summary, status, time, abort_stage, abort_reason, roles, blaster_df, logger_df = parse_blaster(text)

    report_text = "BLASTER 3000 REPORT\n\n"

    # ✅ TITLE
    st.header("💥 Blaster 3000 Report")

    # ✅ SUMMARY
    st.subheader("📊 Blast Summary")
    for k, v in summary.items():
        st.write(f"**{k}:** {v}")
        report_text += f"{k}: {v}\n"

    # ✅ STATUS
    st.subheader("🚦 Blast Status")

    if status == "FIRED":
        st.success(f"✅ FIRED at {time}")
        report_text += f"\nStatus: FIRED at {time}\n"

    elif status == "ABORTED":
        st.error(f"❌ ABORTED at {time}")
        report_text += f"\nStatus: ABORTED at {time}\n"

        if abort_stage:
            st.write(f"Stage: {abort_stage.group(1)}")
            report_text += f"Stage: {abort_stage.group(1)}\n"

        if abort_reason:
            st.write(f"Reason: {abort_reason.group(1)}")
            report_text += f"Reason: {abort_reason.group(1)}\n"

    # ✅ ROLES
    st.subheader("🧭 Blaster Roles")
    for r in roles:
        st.write(f"{r[0]} → {r[1]}")
        report_text += f"{r[0]} → {r[1]}\n"

    # ✅ BLASTER DETAILS
    if not blaster_df.empty:
        st.subheader("🔧 Blaster Details")
        st.dataframe(blaster_df)
        report_text += "\nBlaster Details:\n"
        report_text += blaster_df.to_string(index=False)

    # ✅ LOGGER DETAILS
    if not logger_df.empty:
        st.subheader("📡 Logger Breakdown")
        st.dataframe(logger_df)
        report_text += "\n\nLogger Details:\n"
        report_text += logger_df.to_string(index=False)

    # ✅ ENGINEERING INSIGHT
    st.subheader("💡 Engineering Insight")

    insights = []

    if status == "ABORTED":
        insights.append("Blast aborted before firing stage")
        if abort_reason:
            insights.append(f"Cause: {abort_reason.group(1)}")

    if summary["Detonator Errors"] != "0":
        insights.append("Detonator errors detected → investigate wiring or system")

    if summary["Fire command received"] == "0":
        insights.append("No fire command received → system did not initiate blast")

    for i in insights:
        st.write(f"- {i}")
        report_text += f"\n- {i}"

    # ✅ DOWNLOAD (FIXED)
    st.download_button(
        label="⬇️ Download Blaster Report",
        data=report_text,
        file_name="blaster_report.txt",
        mime="text/plain"
    )
