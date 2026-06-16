import streamlit as st
import re

st.title("💥 Blast + Logger Analysis Tool")

controller_file = st.file_uploader("Upload Controller Report (.txt)")
logger_file = st.file_uploader("Upload Logger Report (.txt)")

# Controller parser
def parse_controller(text):
    matches = re.findall(r"\d+\s+([A-Z0-9]+)\s+(\d+)\s+Programmed", text)
    delays = [int(m[1]) for m in matches]

    return {
        "Total Dets": len(delays),
        "Min Delay": min(delays) if delays else None,
        "Max Delay": max(delays) if delays else None
    }

# Logger parser
def parse_logger(text):
    lines = text.split("\n")
    voltages = []
    leakages = []

    for i, line in enumerate(lines):
        if "mA" in line:
            leak = re.search(r"(\d+\.\d+)\s*mA", line)
            if leak:
                leakages.append(float(leak.group(1)))

            if i + 1 < len(lines):
                try:
                    voltages.append(float(lines[i+1].strip()))
                except:
                    pass

    return {
        "Total": len(voltages),
        "Avg Voltage": round(sum(voltages)/len(voltages), 2) if voltages else 0,
        "Min Voltage": min(voltages) if voltages else 0,
        "Max Voltage": max(voltages) if voltages else 0,
        "Below 20V": len([v for v in voltages if v < 20]),
        "Max Leakage": max(leakages) if leakages else 0
    }

# Main
if controller_file and logger_file:

    ctrl_text = controller_file.read().decode("utf-8")
    log_text = logger_file.read().decode("utf-8")

    ctrl = parse_controller(ctrl_text)
    log = parse_logger(log_text)

    st.subheader("📊 Controller Summary")
    st.write(ctrl)

    st.subheader("⚡ Logger Summary")
    st.write(log)

    st.subheader("💡 Final Assessment")

    if log["Below 20V"] > 0:
        st.error("❌ Low voltage detonators detected")
    else:
        st.success("✅ All detonators above 20V")

    if log["Max Leakage"] > 0.05:
        st.warning("⚠️ High leakage detected")
    else:
        st.info("✅ Leakage normal")
