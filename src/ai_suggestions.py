# File: src/ai_suggestions.py
import os
import json
import google.generativeai as genai
from typing import List, Dict
from dotenv import load_dotenv
from .file_handler import FileHandler
import re
import streamlit as st
# Load environment variables
load_dotenv()

class AIRedactionSuggester:
    def __init__(self):
        api_key = st.secrets["GOOGLE_GEMINI_API_KEY"]
        if not api_key:
            raise ValueError("GOOGLE_GEMINI_API_KEY environment variable not found")
        
        genai.configure(api_key=api_key)
        
        # Configure safety settings
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            }
        ]
        
        # Initialize model with safety settings
        self.model = genai.GenerativeModel(
            'gemini-1.5-flash',
            safety_settings=self.safety_settings
        )
        
        self.sensitive_types = {
            'PII': ['email', 'phone', 'address', 'name', 'ssn', 'dob'],
            'FINANCIAL': ['credit_card', 'bank_account', 'financial_data'],
            'MEDICAL': ['health_info', 'medical_record', 'diagnosis'],
            'CREDENTIALS': ['password', 'api_key', 'token']
        }

    def get_redaction_suggestions(self, file_path: str, sensitivity: int = 50, language: str = 'English') -> List[Dict[str, str]]:
        try:
            file_handler = FileHandler()
            document_text = file_handler.extract_text(file_path)

            prompt = f"""
            Analyze the following text and identify sensitive information that should be redacted.
            Language: {language}
            Minimum confidence threshold: {sensitivity}%

            Consider these types of sensitive information:
            - Personal Identifiable Information (PII)
            - Financial Information
            - Medical Information
            - Security Credentials

            Text to analyze:
            {document_text}

            Provide output in the following JSON format:
            {{
                "redactions": [
                    {{
                        "type": "category_of_sensitive_info",
                        "text": "exact_text_to_redact",
                        "confidence": confidence_score_as_integer,
                        "reason": "brief_explanation"
                    }}
                ]
            }}
            """

            response = self.model.generate_content(prompt)
            suggestions = self._parse_suggestions(response.text)
            
            # When processing AI suggestions, ensure required fields
            processed_suggestions = []
            for suggestion in suggestions:
                suggestion.update({
                    'page': 0,  # Default to first page
                    'bbox': [50, 50, 550, 70]  # Default bounding box
                })
                processed_suggestions.append(suggestion)
            
            return processed_suggestions
        
        except Exception as e:
            print(f"Warning: AI suggestion generation encountered an error: {e}")
            return []

    def _parse_suggestions(self, response_text: str) -> List[Dict[str, str]]:
        try:
            # Extract JSON content from the response
            cleaned_text = response_text.strip()
            
            # Handle potential markdown code block formatting
            if '```json' in cleaned_text:
                cleaned_text = cleaned_text.split('```json')[1].split('```')[0].strip()
            elif '```JSON' in cleaned_text:
                cleaned_text = cleaned_text.split('```JSON')[1].split('```')[0].strip()
            elif '```' in cleaned_text:
                cleaned_text = cleaned_text.split('```')[1].strip()
            
            # Handle empty redactions case
            if not cleaned_text or cleaned_text.isspace():
                return []
            
            # Parse JSON
            try:
                data = json.loads(cleaned_text)
            except json.JSONDecodeError:
                # If parsing fails, return empty list
                return []
            
            # Validate and normalize suggestions
            suggestions = []
            for item in data.get('redactions', []):
                if all(key in item for key in ['type', 'text', 'confidence', 'reason']):
                    suggestions.append({
                        'type': str(item['type']),
                        'text': str(item['text']),
                        'confidence': int(item['confidence']),
                        'reason': str(item['reason'])
                    })
            
            return suggestions
            
        except Exception as e:
            # Log the error and return empty list instead of raising
            print(f"Error parsing suggestions: {e}")
            return []

    def analyze_text_for_redaction(self, document_text: str, text_to_redact: str, redaction_type: str) -> List[Dict]:
        suggestions = []
        
        # First, check for exact matches of the custom text
        if text_to_redact:
            for page_num, page_text in enumerate(document_text.split('\n\n')):
                start = 0
                while True:
                    index = page_text.find(text_to_redact, start)
                    if index == -1:
                        break
                    suggestions.append({
                        'type': redaction_type,
                        'text': text_to_redact,
                        'confidence': 100,
                        'reason': "Exact text match",
                        'page': page_num,
                        'bbox': self._calculate_bbox(index, index + len(text_to_redact), page_text)
                    })
                    start = index + 1
        
        # Then check patterns for related sensitive information
        patterns = {
            'name': r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'(?:\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            'address': r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)[.,]?\s+[A-Za-z\s]+(?:,\s*[A-Z]{2})?\b'
        }
        
        # Add pattern-based matches
        for page_num, page_text in enumerate(document_text.split('\n\n')):
            for pii_type, pattern in patterns.items():
                matches = re.finditer(pattern, page_text)
                for match in matches:
                    if text_to_redact.lower() in match.group().lower():
                        suggestions.append({
                            'type': redaction_type,
                            'text': match.group(),
                            'confidence': 100,
                            'reason': f'{pii_type.title()} detection',
                            'page': page_num,
                            'bbox': self._calculate_bbox(match.start(), match.end(), page_text)
                        })
        
        return suggestions

    def _calculate_bbox(self, start_pos: int, end_pos: int, text: str) -> List[float]:
        """Calculate bounding box coordinates based on text position"""
        # Approximate coordinates based on character position
        x1 = 50  # Left margin
        y1 = 50 + (start_pos * 0.2)  # Top position based on character position
        x2 = 550  # Right margin
        y2 = y1 + 20  # Height of text line
        
        return [x1, y1, x2, y2]

    def _check_pattern_matches(self, document_text: str, text_to_redact: str, redaction_type: str) -> List[Dict]:
        suggestions = []
        patterns = {
            'address': r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)[.,]?\s+[A-Za-z\s]+(?:,\s*[A-Z]{2})?\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'phone': r'\b(\+\d{1,2}[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'
        }
        
        for pattern_type, pattern in patterns.items():
            matches = re.finditer(pattern, document_text)
            for match in matches:
                start_pos = match.start()
                suggestions.append({
                    'type': redaction_type,
                    'text': match.group(),
                    'confidence': 100,
                    'reason': f'{pattern_type.title()} pattern match',
                    'bbox': [50, 50 + (start_pos * 0.5), 550, 70 + (start_pos * 0.5)]  # Dynamic positioning
                })
        
        return suggestions

    def _clean_and_parse_response(self, response_text: str) -> dict:
        """Clean and parse AI response text to extract JSON content"""
        try:
            # Remove any markdown formatting
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0]
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0]
            
            # Clean the text
            response_text = response_text.strip()
            
            # Try to parse JSON
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # Try to fix common JSON issues
                response_text = response_text.replace("'", '"')  # Replace single quotes
                response_text = re.sub(r'(\w+):', r'"\1":', response_text)  # Quote unquoted keys
                return json.loads(response_text)
                
        except Exception as e:
            print(f"Failed to parse AI response: {e}")
            return {"matches": []}

    def analyze_contextual_meaning(self, document_text: str, text_to_redact: str, redaction_type: str) -> List[Dict]:
        try:
            prompt = f"""
            Analyze the following text and identify all instances related to '{text_to_redact}' 
            considering the context and semantic meaning. The type of information is: {redaction_type}

            Text to analyze:
            {document_text}

            Provide output in the following JSON format:
            {{
                "matches": [
                    {{
                        "text": "exact_matched_text",
                        "type": "{redaction_type}",
                        "confidence": confidence_score_as_integer,
                        "reason": "explanation_of_match"
                    }}
                ]
            }}
            """

            response = self.model.generate_content(prompt)
            
            # Parse the response
            matches = []
            try:
                # Clean and parse the response similar to _parse_suggestions method
                cleaned_text = response.text.strip()
                
                if '```json' in cleaned_text:
                    cleaned_text = cleaned_text.split('```json')[1].split('```')[0].strip()
                elif '```' in cleaned_text:
                    cleaned_text = cleaned_text.split('```')[1].strip()
                
                data = json.loads(cleaned_text)
                
                for match in data.get('matches', []):
                    if all(key in match for key in ['text', 'type', 'confidence', 'reason']):
                        matches.append({
                            'text': str(match['text']),
                            'type': str(match['type']),
                            'confidence': int(match['confidence']),
                            'reason': str(match['reason'])
                        })
                
            except Exception as e:
                print(f"Error parsing Gemini response: {e}")
                return []

            return matches

        except Exception as e:
            print(f"Error in contextual analysis: {e}")
            return []
