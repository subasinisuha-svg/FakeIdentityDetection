# AI-Based Fake Identity & Document Screening System

## Project Overview
This project is a Python-based web application that extracts information from uploaded documents and performs basic validation checks.

## Features
- Upload PDF and image files
- Extract text from documents using OCR
- Extract name and ID number
- Validate required fields and ID number format
- Detect duplicate ID numbers
- Calculate a preliminary risk score
- Save document records in a database
- Search saved documents
- View verification summary and average risk score

## Technologies Used
- Python
- Flask
- EasyOCR
- PyMuPDF
- SQLite
- HTML
- CSS

## How to Run
1. Open the project folder in VS Code.
2. Activate your Python virtual environment.
3. Install the required packages.
4. Run the application:

```bash
python app.py
```

5. Open this URL in your browser:

http://127.0.0.1:5000/

## Disclaimer
This is an educational prototype. Basic validation and risk scores cannot confirm whether a document is genuine or fake. Official verification requires trusted sources.