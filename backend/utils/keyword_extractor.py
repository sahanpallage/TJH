from typing import Any
import google.generativeai as genai  # type: ignore
from settings import MODEL_API_KEY
from utils.pdf_utils import encode_pdf_to_base64

genai.configure(api_key=MODEL_API_KEY)  # type: ignore

def extract_keywords_from_pdf(pdf_path: str, is_resume: bool) -> list[str]:
    """
    Uses Gemini to extract keywords from a PDF.
    :param pdf_path: Path to the PDF file.
    :param is_resume: True if resume (extract skills/experience), False if job search info (extract preferences).
    return: List of extracted keywords.
    """
    base64_pdf = encode_pdf_to_base64(pdf_path)

    model: Any = genai.GenerativeModel('gemini-2.5-flash')  # type: ignore

    prompt = ("""Extract key skills from "CORE COMPETENCIES", job titles from "PROFESSIONAL EXPERIENCE", "ADDITIONAL EXPERIENCE" and location on top of the resume."""
              if is_resume
              else """Extract salary expectations, locations like Remote or hybrid work in South Florida, Fort Lauderdale, Florida, 
              South Florida, Miami, Hollywood, Hialeah, Pembroke Pines, Pompano Beach, Coral Spring, Miramar, Davie, Boca Raton, Sunrise, Job Titles, 
              Industries, Companies, and other search criteria from the job search information."""
              )
    prompt += "Output as a comma-seperated list of keywords only, no other text."

    content: list[Any] = [
        prompt,
        {
            "mime_type": "application/pdf",
            "data": base64_pdf
        }
    ]

    response: Any = model.generate_content(content)  # type: ignore[attr-defined]
    keywords: list[str] = [kw.strip() for kw in response.text.split(",") if kw.strip()]  # type: ignore[union-attr]

    return keywords