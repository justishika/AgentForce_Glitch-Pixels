import os
import json
import argparse
import google.generativeai as genai
import time
from typing import Any


genai.configure(api_key=GEMINI_API_KEY)

# Prefer the requested model name first, but fall back to stable public models
GEMINI_MODEL_CANDIDATES = [
    "gemini-1.5-flash-8b",    # cheapest/high-quota option
    "gemini-pro-flash-2.5",   # requested by user; may not exist in SDK
    "gemini-1.5-flash",       # fast model
    "gemini-1.5-pro",         # higher-quality model
]

def gemini_chat(messages: list[str] | str, temperature: float = 0.2, max_tokens: int = 2048) -> str:
    """Call Gemini with fallbacks and return plain text.

    Tries a sequence of model names until one succeeds. Accepts a single
    string or list of strings as messages.
    """
    if isinstance(messages, str):
        messages = [messages]
    last_error: Exception | None = None
    for model_name in GEMINI_MODEL_CANDIDATES:
        try:
            model = genai.GenerativeModel(model_name)
            # brief retry loop to smooth over transient 429s
            for attempt in range(3):
                try:
                    response = model.generate_content(
                        messages,
                        generation_config={
                            "temperature": temperature,
                            "max_output_tokens": max_tokens,
                        },
                    )
                    return (response.text or "").strip()
                except Exception as inner_e:
                    message = str(inner_e).lower()
                    if "429" in message or "quota" in message or "rate" in message:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    raise
        except Exception as e:  # try next candidate
            last_error = e
            continue
    # If all candidates fail, re-raise the last error
    raise last_error or RuntimeError("Gemini generation failed with no specific error")

def gemini_chat_quick(messages: list[str] | str, temperature: float = 0.2, max_tokens: int = 400) -> str:
    """Low-latency single-attempt call using a small fast model.

    - No retries, no model fallbacks
    - Uses gemini-1.5-flash-8b for speed/cost
    - Keeps max_tokens small to reduce latency
    """
    if isinstance(messages, str):
        messages = [messages]
    model = genai.GenerativeModel("gemini-1.5-flash-8b")
    response = model.generate_content(
        messages,
        generation_config={
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        },
    )
    return (getattr(response, "text", "") or "").strip()

def gemini_chat_stream(messages: list[str] | str, temperature: float = 0.2, max_tokens: int = 2048):
    """Yield partial text chunks from Gemini with the same fallbacks as gemini_chat.

    This function returns a generator of strings so callers can stream updates to
    the UI. If all online attempts fail, it raises and the caller should use a
    local fallback.
    """
    if isinstance(messages, str):
        messages = [messages]
    last_error: Exception | None = None
    for model_name in GEMINI_MODEL_CANDIDATES:
        try:
            model = genai.GenerativeModel(model_name)
            for attempt in range(3):
                try:
                    response = model.generate_content(
                        messages,
                        generation_config={
                            "temperature": temperature,
                            "max_output_tokens": max_tokens,
                        },
                        stream=True,
                    )
                    for chunk in response:
                        yield getattr(chunk, "text", "")
                    # ensure the stream is resolved
                    try:
                        response.resolve()
                    except Exception:
                        pass
                    return
                except Exception as inner_e:
                    message = str(inner_e).lower()
                    if "429" in message or "quota" in message or "rate" in message:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    raise
        except Exception as e:
            last_error = e
            continue
    raise last_error or RuntimeError("Gemini streaming failed with no specific error")

def _fallback_summary(document_text: str) -> str:
    """Heuristic summarization used if the API call fails or document is empty.

    Produces 4–6 concise bullets, attempting light labeling based on keywords.
    """
    text = (document_text or "").strip()
    if not text:
        return (
            "• Document text could not be extracted. Please upload a text-based PDF or TXT.\n"
            "• Without text, the system cannot analyze clauses or risks.\n"
            "• Provide a plaintext contract and checklist to continue."
        )
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [" ".join(text.split())]

    labels = [
        ("Parties/Document", ["shareholder", "agreement", "between", "by and between", "parties", "msa", "master services", "contract", "nda"]) ,
        ("Scope/Services", ["scope", "services", "deliverable", "obligation", "work", "service"]) ,
        ("Payments", ["payment", "fees", "invoice", "consideration", "price"]) ,
        ("Term/Termination", ["term", "termination", "notice"]) ,
        ("Liability/Indemnity", ["liability", "indemn", "damages", "cap"]) ,
        ("Confidentiality/IP", ["confidential", "privacy", "intellectual", "ip", "proprietary"]) ,
        ("Governing law/Dispute", ["govern", "law", "jurisdiction", "arbitrat", "dispute"]) ,
    ]

    def pick_label(p: str) -> str:
        low = p.lower()
        for label, keys in labels:
            if any(k in low for k in keys):
                return label
        return "Key point"

    bullets: list[str] = []
    for p in paragraphs[:6]:
        condensed = " ".join(p.split())
        label = pick_label(condensed)
        bullets.append(f"• **{label}:** {condensed}")
        if len(bullets) >= 6:
            break
    return "\n".join(bullets)

# --- Tools ---
class FileReaderTool:
    name: str = "file_reader"
    description: str = "Reads a legal document from a file path."
    def _run(self, file_path):
        if file_path.lower().endswith('.pdf'):
            try:
                from PyPDF2 import PdfReader
            except ImportError:
                raise ImportError("PyPDF2 is required for PDF support. Please install it with 'pip install PyPDF2'.")
            reader = PdfReader(file_path)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="ISO-8859-1") as f:
                return f.read()

class SummarizeTool:
    name: str = "summarize"
    description: str = "Summarizes a section of legal text."
    def _run(self, text):
        prompt = f"You are a legal AI assistant. Summarize the following legal section in 2-3 bullet points:\n{text}"
        return gemini_chat([prompt])

class ClauseMatchTool:
    name: str = "clause_match"
    description: str = "Checks if a clause from the checklist is present in the document section."
    def _run(self, section, clause):
        prompt = (
            "You are a legal AI assistant. Does the following section address this checklist item?\n"
            f"Section: {section}\n"
            f"Checklist: {clause}\n"
            "Answer yes/no first, then briefly explain in one sentence."
        )
        try:
            return gemini_chat([prompt])
        except Exception:
            # Simple heuristic fallback based on keyword overlap
            section_lower = (section or "").lower()
            keywords = [w for w in (clause or "").lower().replace(",", " ").split() if len(w) > 3]
            overlap = sum(1 for w in keywords if w in section_lower)
            threshold = max(3, len(keywords) // 5)
            if overlap >= threshold:
                return "Yes. Heuristic match based on keyword overlap in the section."
            return "No. Clause not detected by heuristic keyword overlap."

class JSONReportTool:
    name: str = "json_report"
    description: str = "Writes a structured JSON report to a file."
    def _run(self, report, out_path):
        if out_path:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            return f"Report saved to {out_path}"
        return report

# --- Agent Reasoning Steps ---
def agent_reasoning(file_path, checklist_path, out_path):
    # Read files
    doc_text = FileReaderTool()._run(file_path)
    checklist = json.loads(FileReaderTool()._run(checklist_path))

    # Split document into sections (simple split by paragraphs)
    sections = [s.strip() for s in doc_text.split('\n\n') if s.strip()]
    if not sections:
        sections = [doc_text]

    # Summarize: ultra-fast path -> robust multi-model -> offline fallback
    summary_prompt = (
        "You are a legal AI assistant. Create a concise but detailed executive summary in 4–6 bullets. "
        "Focus on the main business terms and clearly label each bullet in bold. Include where present: "
        "parties/document type, scope/services, payment/consideration, term/termination, liability/indemnity, "
        "confidentiality/IP, and governing law/dispute resolution. If any item is missing, state 'Not specified'.\n\n"
        f"Document:\n{doc_text}"
    )
    summary_warning: str | None = None
    try:
        summary = gemini_chat_quick([summary_prompt], max_tokens=320)
    except Exception:
        try:
            summary = gemini_chat([summary_prompt], max_tokens=600)
        except Exception:
            summary_warning = (
                "Online AI limit reached. Generated a concise offline summary instead. "
                "You can retry later to use the full AI model."
            )
            summary = _fallback_summary(doc_text)

    # Checklist validation
    validation = {}
    for clause_name, clause_text in checklist.items():
        found = False
        for sec in sections:
            try:
                match_result = ClauseMatchTool()._run(sec, clause_text)
            except Exception as e:
                match_result = f"No. Heuristic fallback due to error: {e}"
            if "yes" in match_result.lower():
                validation[clause_name] = {
                    "status": "COMPLIANT",
                    "reason": match_result,
                    "suggested_fix": "",
                    "severity": "low"
                }
                found = True
                break
        if not found:
            validation[clause_name] = {
                "status": "MISSING",
                "reason": "Clause not found in document.",
                "suggested_fix": f"Add clause: {clause_text}",
                "severity": "high"
            }

    # Red flags and follow-up questions
    prompt_redflags = (
        "You are a legal AI assistant. Read the following legal document and checklist validation. "
        "List any risky terms, missing clauses, or red flags. "
        "Suggest 3 follow-up questions for a lawyer."
        f"\nDocument Summary:\n{summary}\nValidation:\n{json.dumps(validation, indent=2)}"
    )
    try:
        redflag_response = gemini_chat([prompt_redflags])
        red_flags = []
        questions = []
        for line in redflag_response.split('\n'):
            if "red flag" in line.lower() or "risk" in line.lower():
                red_flags.append(line)
            if "?" in line:
                questions.append(line)
    except Exception:
        # Fallback red flags and questions derived from validation
        red_flags = [
            f"Risk: Missing clause '{name}'." for name, v in validation.items() if v.get("status") == "MISSING"
        ]
        questions = [
            "What payment terms (amounts, due dates, late fees) are specified?",
            "Is there an explicit limitation of liability and exclusions (e.g., consequential damages)?",
            "Under what conditions can either party terminate, and what notice is required?",
        ]

    # Build report
    report = {
        "summary": summary,
        "validation": validation,
        "red_flags": red_flags,
        "questions": questions,
    }
    if summary_warning:
        report["warning"] = summary_warning
    JSONReportTool()._run(report, out_path)
    return report
    # ...existing code...
