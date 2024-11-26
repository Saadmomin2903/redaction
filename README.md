# MultiDoc Redaction Assistant

## Overview
MultiDoc Redaction Assistant is an advanced document redaction tool leveraging AI-powered intelligent redaction suggestions.

## Features
- Multi-format document support (PDF, DOCX, TXT)
- AI-powered sensitive information detection
- Customizable redaction modes
- Secure file handling
- Comprehensive redaction reporting

## Installation
1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Google Gemini API key:
- Create a `.env` file
- Add `GOOGLE_GEMINI_API_KEY=your_api_key_here`

## Usage
```bash
streamlit run src/main.py
```

## Requirements
- Python 3.8+
- Google Gemini API Key

## Security Considerations
- Temporary files are securely deleted
- Sensitive data is encrypted during processing
- Multi-layered error handling

## Contributing
Contributions welcome! Please read the contribution guidelines.

## License
MIT License
```