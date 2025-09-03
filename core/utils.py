import os
from PyPDF2 import PdfReader
from docx import Document

def read_file_content(local_path):
    ext = os.path.splitext(local_path)[1].lower()
    if ext == ".pdf":
        reader = PdfReader(local_path)
        return "\n".join([page.extract_text() for page in reader.pages])
    elif ext in [".docx", ".doc"]:
        doc = Document(local_path)
        return "\n".join([p.text for p in doc.paragraphs])
    else:
        with open(local_path, "r", encoding="utf-8") as f:
            return f.read()
