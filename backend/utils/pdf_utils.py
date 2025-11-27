import base64

def encode_pdf_to_base64(pdf_path: str) -> str:
    """
    Reads a PDF file and returns its base64-encoded string."""

    with open(pdf_path, 'rb') as pdf_file:
        pdf_bytes = pdf_file.read()
        return base64.b64encode(pdf_bytes).decode('utf-8')