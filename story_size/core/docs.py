from pathlib import Path
import pypdf
import docx
import openpyxl

def read_pdf(file_path: Path) -> str:
    """Reads text from a PDF file."""
    reader = pypdf.PdfReader(file_path)
    text = []
    for page in reader.pages:
        text.append(page.extract_text())
    return "\n".join(text)

def read_docx(file_path: Path) -> str:
    """Reads text from a DOCX file."""
    doc = docx.Document(file_path)
    text = []
    for para in doc.paragraphs:
        text.append(para.text)
    return "\n".join(text)

def read_xlsx(file_path: Path) -> str:
    """Reads text from an XLSX file."""
    workbook = openpyxl.load_workbook(file_path)
    text = []
    for sheetname in workbook.sheetnames:
        sheet = workbook[sheetname]
        for row in sheet.iter_rows():
            row_text = []
            for cell in row:
                if cell.value:
                    row_text.append(str(cell.value))
            text.append(" ".join(row_text))
    return "\n".join(text)

def read_documents(docs_dir: Path) -> str:
    """
    Reads all .md, .txt, .pdf, .docx, and .xlsx files from the given directory,
    concatenates their content, and returns it as a single string.
    """
    content = []
    for file_path in docs_dir.rglob("*.md"):
        try:
            content.append(file_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    for file_path in docs_dir.rglob("*.txt"):
        try:
            content.append(file_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    for file_path in docs_dir.rglob("*.pdf"):
        try:
            content.append(read_pdf(file_path))
        except Exception:
            pass
    for file_path in docs_dir.rglob("*.docx"):
        try:
            content.append(read_docx(file_path))
        except Exception:
            pass
    for file_path in docs_dir.rglob("*.xlsx"):
        try:
            content.append(read_xlsx(file_path))
        except Exception:
            pass
    return "\n\n".join(content)