"""generates a personalised discharge document."""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_anthropic import ChatAnthropic # pip install -U langchain-anthropic
from langchain.messages import HumanMessage, AIMessage, SystemMessage
from .models import PatientDischargeContext

load_dotenv()


llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
)

_SYSTEM_PROMPT = """
You are a clinical documentation assistant for Lakeland Regional Health.
Your task is to generate a clear, compassionate, and easy-to-understand
patient discharge summary for a nurse to review and hand to the patient.

Guidelines:
- Use plain, patient-friendly language (avoid heavy medical jargon).
- Organise the document with clearly labelled sections.
- Highlight any diagnoses and procedures from the most recent hospitalisation.
- Reference prior hospitalisations only where they provide relevant context.
- Include a short "What to watch for" section with warning signs related to
  the patient's conditions.
- End with a brief "Follow-up" reminder.
- Keep the tone warm and reassuring.
""".strip()


def generate_discharge_document(context: PatientDischargeContext) -> str:
    """
    Accept a fully-populated PatientDischargeContext and return the LLM's
    discharge document as a plain string.
    """
    patient_json = context.model_dump_json(indent=2)

    human_msg = HumanMessage(
        content=(
            "Below is the structured medical history for this patient.\n"
            "Please generate a personalised discharge document following the "
            "guidelines in your system prompt.\n\n"
            f"```json\n{patient_json}\n```"
        )
    )

    response = llm.invoke([SystemMessage(content=_SYSTEM_PROMPT), human_msg])
    return response.content
