from pdfai.pdf_ops import extract_fields_from_form
import os


# TODO: Make paths relative
pdf_path = "pdfs/ek_anlage_v2.pdf"

extract_fields_from_form(pdf_path)
