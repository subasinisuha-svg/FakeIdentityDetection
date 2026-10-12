import os
import re

import easyocr
import fitz  # PyMuPDF

from flask import Flask, request, render_template_string
from werkzeug.utils import secure_filename

from database import (
    create_database,
    save_document,
    get_all_documents,
    search_documents,
    check_duplicate_id,
)

app = Flask(__name__)

# Initialize database
create_database()

# Project folders
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

# Initialize OCR
reader = easyocr.Reader(["en"], gpu=False)


# Main website HTML
PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">

    <title>Fake Identity Screening System</title>

    <style>
    * {
        box-sizing: border-box;
    }

    body {
        font-family: Arial, sans-serif;
        max-width: 1000px;
        margin: 0 auto;
        padding: 30px 20px;
        background: #f4f7fc;
        color: #263449;
        line-height: 1.6;
    }

    .card {
        background: #ffffff;
        padding: 26px;
        margin-bottom: 22px;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        box-shadow: 0 5px 18px #1e3a5f0d;
    }

    h1 {
        color: #123d70;
        font-size: 28px;
        line-height: 1.3;
    }

    h2 {
        color: #174b85;
        font-size: 21px;
        margin-top: 0;
    }

    h3 {
        color: #174b85;
    }

    p {
        overflow-wrap: anywhere;
    }

    button {
        background: #1765c0;
        color: white;
        border: none;
        padding: 12px 22px;
        border-radius: 8px;
        font-size: 15px;
        font-weight: bold;
        cursor: pointer;
        transition: background 0.2s;
    }

    button:hover {
        background: #104b91;
    }

    input[type="file"] {
        display: block;
        width: 100%;
        max-width: 100%;
        margin: 16px 0;
        padding: 12px;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        background: #f8fafc;
    }

    pre {
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        background: #f1f5f9;
        padding: 16px;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        font-size: 14px;
    }

    .success {
        color: #187443;
    }

    .error {
        color: #b42332;
    }

    .note {
        color: #64748b;
        font-size: 13px;
    }

    a {
        display: inline-block;
        margin: 8px 12px 4px 0;
        color: #1765c0;
        font-weight: 600;
        text-decoration: none;
    }

    a:hover {
        text-decoration: underline;
    }

    hr {
        border: none;
        border-top: 1px solid #e2e8f0;
        margin: 24px 0;
    }

    @media (max-width: 600px) {
        body {
            padding: 14px;
        }

        .card {
            padding: 18px;
        }

        h1 {
            font-size: 23px;
        }

        h2 {
            font-size: 19px;
        }
    }
</style>
</head>

<body>
    <div class="card">
        <h1>Fake Identity & Document Screening System</h1>

        <p>
            Upload an image or PDF to extract text
            and check required fields.
        </p>

        <form action="/check"
              method="POST"
              enctype="multipart/form-data">

            <input type="file"
                   name="document"
                   accept=".pdf,.png,.jpg,.jpeg"
                   required>

            <br>

            <button type="submit">Check Document</button>
        </form>

        <p class="note">Maximum file size: 5 MB.</p>

        <hr>

        <a href="/documents">Saved Documents</a>
        <a href="/search">Search Documents</a>
        <a href="/summary">Verification Summary</a>
    </div>

    {% if error %}
    <div class="card error">
        <strong>{{ error }}</strong>
    </div>
    {% endif %}

    {% if extracted_text is not none %}
    <div class="card">
        <h2>Extracted Text</h2>
        <pre>{{ extracted_text }}</pre>
    </div>

    <div class="card">
        <h2>Extracted Details</h2>
        <p><strong>Name:</strong> {{ details["Name"] }}</p>
        <p><strong>ID Number:</strong> {{ details["ID Number"] }}</p>
    </div>
    <div class="card">
        <h2>Document Risk Score</h2>

        <p>
            <strong>Risk Score:</strong>
            {{ risk_score }} / 100
        </p>

        {% if risk_score >= 50 %}
        <p class="error">
            Higher screening risk — please review this document.
        </p>
        {% elif risk_score >= 20 %}
        <p>
            Moderate screening risk — additional review recommended.
        </p>
        {% else %}
        <p class="success">
            Lower screening risk based on basic checks.
        </p>
        {% endif %}

        <p class="note">
            This score is a preliminary screening estimate.
            It does not confirm whether a document is genuine or fake.
        </p>
    </div>
    <div class="card">
        <h2>Basic Validation Results</h2>

        <ul>
        {% for label, found in checks.items() %}
            <li class="{{ 'success' if found else 'error' }}">
                {{ label }}:
                {{ "Passed" if found else "Failed" }}
            </li>
        {% endfor %}
        </ul>

        {% if warnings %}
        <h3>Warnings</h3>
        <ul>
            {% for warning in warnings %}
            <li>{{ warning }}</li>
            {% endfor %}
        </ul>
        {% else %}
        <p class="success">
            All basic validation checks passed.
        </p>
        {% endif %}

        <p class="note">
            These checks validate extracted fields and formats.
            They do not prove whether a document is genuine or fake.
            Scanned PDFs are not OCR-processed in this version.
        </p>

        <a href="/">Check another document</a>
        <a href="/summary">View Summary</a>
    </div>
    {% endif %}
</body>
</html>
"""


# Check allowed file types
def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# Extract text from an image
def extract_text_from_image(filepath):
    results = reader.readtext(filepath, detail=0)
    return "\n".join(results)


# Extract selectable text from a PDF
def extract_text_from_pdf(filepath):
    text_parts = []

    with fitz.open(filepath) as pdf:
        for page in pdf:
            # First try extracting selectable text
            page_text = page.get_text().strip()

            if page_text:
                text_parts.append(page_text)
            else:
                # If no selectable text, render the page as an image
                pix = page.get_pixmap(
                    matrix=fitz.Matrix(2, 2),
                    alpha=False
                )

                image_bytes = pix.tobytes("png")

                # EasyOCR can read image bytes directly
                results = reader.readtext(
                    image_bytes,
                    detail=0
                )

                text_parts.append("\n".join(results))

    return "\n".join(text_parts).strip()

# Validate document fields
def validate_document(text):
    checks = {
        "Name field present": False,
        "ID number field present": False,
        "ID number has valid format": False,
    }

    details = {
        "Name": "Not found",
        "ID Number": "Not found",
    }

    warnings = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        # Support both colon and common OCR label variations
        if ":" in line:
            label, value = line.split(":", 1)
        else:
            continue

        label = " ".join(label.upper().split())
        value = value.strip()

        # Normalize common OCR mistakes in labels
        

        if label in {"NAME", "STUDENT NAME","STUDENT NAM"}:
            if value:
                details["Name"] = value
                checks["Name field present"] = True

        elif label in {
            "ID NUMBER",
            "ID NO",
            "ID",
            "STUDENT ID",
        }:
            if value:
                details["ID Number"] = value
                checks["ID number field present"] = True

    if not checks["Name field present"]:
        warnings.append("Name is missing or empty.")

    if not checks["ID number field present"]:
        warnings.append("ID Number is missing or empty.")

    id_number = details["ID Number"]

    if id_number != "Not found":
        checks["ID number has valid format"] = (
            id_number.isdigit() and len(id_number) == 8
        )

    if not checks["ID number has valid format"]:
        warnings.append(
            "ID Number must contain exactly 8 digits."
        )

    if id_number == "00000000":
        warnings.append(
            "Suspicious ID number: all digits are zero."
        )

    return checks, details, warnings


# Home page
@app.route("/", methods=["GET"])
def home():
    return render_template_string(
        PAGE,
        extracted_text=None,
        checks=None,
        details=None,
        warnings=None,
        error=None,
    )


# Saved documents page
@app.route("/documents", methods=["GET"])
def view_saved_documents():
    records = get_all_documents()

    return render_template_string("""
    <html>
    <head><title>Saved Documents</title></head>
    <body>
        <h1>Saved Documents</h1>

        <table border="1" cellpadding="10">
    <tr>
        <th>ID</th>
        <th>Name</th>
        <th>ID Number</th>
        <th>Status</th>
        <th>Risk Score</th>
    </tr>

    {% for record in records %}
    <tr>
        <td>{{ record[0] }}</td>
        <td>{{ record[1] }}</td>
        <td>{{ record[2] }}</td>
        <td>{{ record[3] }}</td>
        <td>{{ record[4] }}</td>
    </tr>
    {% else %}
    <tr>
        <td colspan="5">No documents saved yet.</td>
    </tr>
    {% endfor %}
</table>

        <p><a href="/">Home</a></p>
        <p><a href="/search">Search Documents</a></p>
        <p><a href="/summary">Verification Summary</a></p>
    </body>
    </html>
    """, records=records)


# Search documents by name or ID number
@app.route("/search", methods=["GET"])
def search_saved_documents():
    search_term = request.args.get("q", "").strip()

    if search_term:
        records = search_documents(search_term)
    else:
        records = []

    return render_template_string("""
    <html>
    <head><title>Search Saved Documents</title></head>
    <body>
        <h1>Search Saved Documents</h1>

        <form action="/search" method="GET">
            <input type="text"
                   name="q"
                   placeholder="Enter name or ID number"
                   value="{{ search_term }}">
            <button type="submit">Search</button>
        </form>

        {% if search_term %}
            <h3>Results for: {{ search_term }}</h3>

            {% if records %}
            <table border="1" cellpadding="10">
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>ID Number</th>
                    <th>Status</th>
                </tr>

                {% for record in records %}
                <tr>
                    {% for value in record %}
                    <td>{{ value }}</td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p>No matching documents found.</p>
            {% endif %}
        {% endif %}

        <p><a href="/documents">Saved Documents</a></p>
        <p><a href="/summary">Verification Summary</a></p>
        <p><a href="/">Home</a></p>
    </body>
    </html>
    """, records=records, search_term=search_term)


# Verification summary
@app.route("/summary", methods=["GET"])
def document_summary():
    records = get_all_documents()

    total = len(records)
    passed = sum(
        1 for record in records if record[3] == "Passed"
    )
    warnings = sum(
        1 for record in records if record[3] == "Warning"
    )
    average_risk = (
        sum(record[4] or 0 for record in records) / total
        if total > 0 else 0
    )
    average_risk = round(average_risk, 2)

    return render_template_string("""
    <html>
    <head>
        <title>Verification Summary</title>
        <meta name="viewport"
              content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 750px;
                margin: 30px auto;
                padding: 20px;
                background: #f2f5fa;
            }
            .card {
                background: white;
                padding: 20px;
                margin: 15px 0;
                border-radius: 8px;
            }
            h1 {
                color: #174b85;
            }
        </style>
    </head>
    <body>
        <h1>Document Verification Summary</h1>

        <div class="card">
            <h2>Total Documents: {{ total }}</h2>
        </div>

        <div class="card">
            <h2>Passed Basic Validation: {{ passed }}</h2>
        </div>

        <div class="card">
            <h2>Documents with Warnings: {{ warnings }}</h2>
        </div>
        <div class="card">
            <h2>Average Risk Score: {{ average_risk }} / 100</h2>
        </div>
        <p>
            These results reflect basic field and format checks.
            They do not prove whether a document is genuine or fake.
        </p>

        <p><a href="/documents">View All Documents</a></p>
        <p><a href="/search">Search Documents</a></p>
        <p><a href="/">Home</a></p>
    </body>
    </html>
    """, total=total, passed=passed, warnings=warnings,average_risk=average_risk)


# Upload and check a document
@app.route("/check", methods=["POST"])
def check_document():
    if "document" not in request.files:
        return render_template_string(
            PAGE,
            extracted_text=None,
            checks=None,
            details=None,
            warnings=None,
            error="Please choose a document.",
        )

    file = request.files["document"]

    if file.filename == "":
        return render_template_string(
            PAGE,
            extracted_text=None,
            checks=None,
            details=None,
            warnings=None,
            error="No file selected.",
        )

    if not allowed_file(file.filename):
        return render_template_string(
            PAGE,
            extracted_text=None,
            checks=None,
            details=None,
            warnings=None,
            error="Upload a PDF, PNG, JPG, or JPEG file.",
        )

    filename = secure_filename(file.filename)

    if not filename:
        return render_template_string(
            PAGE,
            extracted_text=None,
            checks=None,
            details=None,
            warnings=None,
            error="Invalid filename.",
        )

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename,
    )

    file.save(filepath)

    try:
        extension = filename.rsplit(".", 1)[1].lower()

        if extension == "pdf":
            extracted_text = extract_text_from_pdf(filepath)

            if not extracted_text:
                extracted_text = (
                    "No selectable text found. This may be a scanned PDF. "
                    "OCR for scanned PDFs is not included in this version."
                )
        else:
            extracted_text = extract_text_from_image(filepath)

        checks, details, warnings = validate_document(
            extracted_text
        )
        id_number = details["ID Number"]

        if (
            id_number != "Not found"
            and check_duplicate_id(id_number)
        ):
            warnings.append(
                "Duplicate ID number: this ID already exists in the database."
            )

        failed_checks = sum(
            1 for passed in checks.values()
            if not passed
        )

        duplicate_found = any(
            "Duplicate ID number" in warning
            for warning in warnings
        )

        risk_score = min(
            100,
            failed_checks * 25 + (20 if duplicate_found else 0)
        )

        duplicate_found = any(
            "Duplicate ID number" in warning
            for warning in warnings
        )

        risk_score = min(
            100,
            failed_checks * 25 + (20 if duplicate_found else 0)
        )   
        status = (
            "Warning"
            if warnings or not all(checks.values())
            else "Passed"
        )

        save_document(
            details["Name"],
            details["ID Number"],
            status,
            risk_score,
        )

        return render_template_string(
            PAGE,
            extracted_text=extracted_text,
            checks=checks,
            details=details,
            warnings=warnings,
            risk_score=risk_score,
            error=None,
        )

    except Exception:
        app.logger.exception(
            "Document processing or saving failed"
        )

        return render_template_string(
            PAGE,
            extracted_text=None,
            checks=None,
            details=None,
            warnings=None,
            error=(
                "Could not process or save this file. "
                "Check the terminal for details."
            ),
        )


# File size error handler
@app.errorhandler(413)
def file_too_large(error):
    return render_template_string(
        PAGE,
        extracted_text=None,
        checks=None,
        details=None,
        warnings=None,
        error=(
            "File is too large. "
            "Please upload a file smaller than 5 MB."
        ),
    ), 413


if __name__ == "__main__":
    app.run(debug=True)