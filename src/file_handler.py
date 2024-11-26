# File: src/file_handler.py
import os
import magic
import pikepdf
import docx
from typing import List, Union
import tempfile
import pdfplumber

class FileHandler:
    SUPPORTED_FORMATS = {
        'pdf': ['.pdf'],
        'docx': ['.docx', '.doc'],
        'txt': ['.txt', '.text'],
        'rtf': ['.rtf']
    }

    def validate_file(self, file_path: str) -> bool:
        """
        Validate file type and size
        
        Args:
            file_path (str): Path to the file to validate
        
        Returns:
            bool: Whether file is valid
        """
        # Check file existence
        if not os.path.exists(file_path):
            raise FileNotFoundError("File does not exist")

        # File size check (100MB limit)
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        if file_size > 100:
            raise ValueError("File exceeds 100MB limit")

        # MIME type detection
        file_mime = magic.from_file(file_path, mime=True)
        supported_mimes = {
            'application/pdf': 'pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'text/plain': 'txt',
            'application/rtf': 'rtf'
        }

        if file_mime not in supported_mimes:
            raise ValueError(f"Unsupported file type: {file_mime}")

        return True

    def extract_text(self, file_path: str) -> str:
        """
        Extract text from different file types
        
        Args:
            file_path (str): Path to the file
        
        Returns:
            str: Extracted text content
        """
        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension in self.SUPPORTED_FORMATS['pdf']:
            return self._extract_pdf_text(file_path)
        elif file_extension in self.SUPPORTED_FORMATS['docx']:
            return self._extract_docx_text(file_path)
        elif file_extension in self.SUPPORTED_FORMATS['txt'] + self.SUPPORTED_FORMATS['rtf']:
            return self._extract_plain_text(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF"""
        try:
            text = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text.append(page.extract_text() or '')
            return "\n".join(text)
        except Exception as e:
            raise RuntimeError(f"PDF text extraction failed: {e}")

    def _extract_docx_text(self, file_path: str) -> str:
        """Extract text from DOCX"""
        try:
            doc = docx.Document(file_path)
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            raise RuntimeError(f"DOCX text extraction failed: {e}")

    def _extract_plain_text(self, file_path: str) -> str:
        """Extract text from plain text files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Text file extraction failed: {e}")

    def save_temp_file(self, uploaded_file) -> str:
        """
        Save an uploaded file to a temporary location
        
        Args:
            uploaded_file: StreamlitUploadedFile object
        
        Returns:
            str: Path to the saved temporary file
        """
        try:
            # Create temp file with same extension as uploaded file
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=file_extension
            )
            
            # Write uploaded file content to temp file
            temp_file.write(uploaded_file.getvalue())
            temp_file.close()
            
            # Validate the saved file
            self.validate_file(temp_file.name)
            
            return temp_file.name
            
        except Exception as e:
            raise RuntimeError(f"Failed to save temporary file: {e}")