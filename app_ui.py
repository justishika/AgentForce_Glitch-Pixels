import streamlit as st
import json
from app import agent_reasoning  # Import the main agent function
from fpdf import FPDF

st.set_page_config(page_title="Legal Document Summarizer & Validator", layout="wide")

st.title("📜 Legal Document Summarizer & Validator")
st.write("Upload a legal document, and the AI agent will summarize it, validate clauses, and flag risks.")

uploaded_file = st.file_uploader("Upload Contract (required)", type=["txt", "pdf"], accept_multiple_files=False)
checklist_file = st.file_uploader("Upload Compliance Checklist (JSON, required)", type=["json"], accept_multiple_files=False)

if uploaded_file and checklist_file:
    with st.spinner("Processing... ⏳"):
        # Save uploaded files temporarily
        contract_path = "temp_contract.pdf" if uploaded_file.name.lower().endswith('.pdf') else "temp_contract.txt"
        with open(contract_path, "wb") as f:
            f.write(uploaded_file.read())
        with open("temp_checklist.json", "wb") as f:
            f.write(checklist_file.read())
    # Use agent_reasoning, but don't write to disk
    result = agent_reasoning(contract_path, "temp_checklist.json", out_path=None)

    st.success("✅ Processing complete!")
    st.sidebar.header("Instructions")
    st.sidebar.markdown("""
    1. Upload a legal document (PDF or TXT).
    2. Upload a compliance checklist (JSON).
    3. View summary and download the legal report as PDF.
    """)


    # Display summary in a structured format
    st.subheader("📄 Structured Summary")
    summary = result.get("summary", "No summary generated.")
    if isinstance(summary, str) and "•" in summary:
        bullets = [line.strip() for line in summary.split("•") if line.strip()]
        for i, bullet in enumerate(bullets, 1):
            st.markdown(f"**{i}.** {bullet}")
    else:
        st.markdown(summary)

    # Display validation results
    st.subheader("✅ Validation Results")
    validation = result.get("validation", {})
    if validation:
        for key, val in validation.items():
            display_key = key if not str(key).isdigit() else f"Clause {key}"
            if isinstance(val, dict):
                status = val.get("status", "")
                reason = val.get("reason", "")
                suggested_fix = val.get("suggested_fix", "")
                severity = val.get("severity", "")
                sev_color = {'high': '#ff4c4c', 'medium': '#ffa500', 'low': '#4caf50'}.get(severity, '#888')
                st.markdown(f"<div style='background-color:#181818;padding:12px;border-radius:8px;margin-bottom:10px'>"
                            f"<span style='font-weight:bold;font-size:1.05em'>{display_key}</span>: "
                            f"<span style='color:{sev_color};font-weight:bold'>{status}</span><br>"
                            f"<span style='font-size:0.98em'><i>Reason:</i> {reason}</span><br>"
                            f"<span style='font-size:0.98em'><i>Suggested fix:</i> {suggested_fix}</span><br>"
                            f"<span style='font-size:0.98em'><i>Severity:</i> <span style='color:{sev_color}'>{severity}</span></span>"
                            f"</div>", unsafe_allow_html=True)
            elif isinstance(val, list):
                for item in val:
                    st.markdown(f"<div style='background-color:#181818;padding:12px;border-radius:8px;margin-bottom:10px'>"
                                f"<span style='font-weight:bold;font-size:1.05em'>{display_key}</span>: "
                                f"{item}"
                                f"</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background-color:#181818;padding:12px;border-radius:8px;margin-bottom:10px'>"
                            f"<span style='font-weight:bold;font-size:1.05em'>{display_key}</span>: "
                            f"{val}"
                            f"</div>", unsafe_allow_html=True)
    else:
        st.info("No validation results found.")

    # PDF download button with summary and validation
    def create_pdf(summary_text, validation_dict):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Legal Document Summary", ln=True, align="C")
        pdf.ln(10)
        if isinstance(summary_text, list):
            summary_text = "\n".join(str(item) for item in summary_text)
        # If summary_text is a list, join it into a string
        if isinstance(summary_text, list):
            summary_text = "\n".join(str(item) for item in summary_text)
        if isinstance(summary_text, str):
            summary_text = summary_text.replace("•", "-")
        if isinstance(summary_text, str) and "-" in summary_text:
            bullets = [line.strip() for line in summary_text.split("-") if line.strip()]
            for i, bullet in enumerate(bullets, 1):
                pdf.multi_cell(0, 10, txt=f"{i}. {bullet}")
        else:
            pdf.multi_cell(0, 10, txt=summary_text)
        pdf.ln(8)
        pdf.set_font("Arial", size=12, style='B')
        pdf.cell(0, 10, txt="Validation Results", ln=True)
        pdf.set_font("Arial", size=12)
        if validation_dict:
            for key, val in validation_dict.items():
                display_key = key if not str(key).isdigit() else f"Clause {key}"
                if isinstance(val, dict):
                    status = val.get("status", "")
                    reason = val.get("reason", "")
                    suggested_fix = val.get("suggested_fix", "")
                    severity = val.get("severity", "")
                    pdf.multi_cell(0, 10, txt=f"{display_key}: {status}\nReason: {reason}\nSuggested fix: {suggested_fix}\nSeverity: {severity}\n")
                elif isinstance(val, list):
                    for item in val:
                        pdf.multi_cell(0, 10, txt=f"{display_key}: {item}\n")
                else:
                    pdf.multi_cell(0, 10, txt=f"{display_key}: {val}\n")
        else:
            pdf.multi_cell(0, 10, txt="No validation results found.")
        return pdf.output(dest="S").encode("utf-8")

    pdf_bytes = create_pdf(summary, validation)
    st.download_button("⬇ Download Legal Report as PDF", data=pdf_bytes, file_name="legal_report.pdf", mime="application/pdf")

else:
    st.info("Please upload both the contract and checklist to begin.")
