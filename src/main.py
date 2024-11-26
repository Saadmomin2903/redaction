# File: src/main.py
import streamlit as st
import os
import tempfile
from src.file_handler import FileHandler
from src.redaction_engine import RedactionEngine
from src.ai_suggestions import AIRedactionSuggester
from src.report_generator import RedactionReportGenerator
from src.security_utils import SecurityManager

# Must be the first Streamlit command
st.set_page_config(
    page_title="MultiDoc Redaction Assistant",
    page_icon="📄",
    layout="wide"
)

class MultiDocRedactionApp:
    def __init__(self):
        # Initialize session state if it doesn't exist
        if 'custom_redactions' not in st.session_state:
            st.session_state.custom_redactions = []
        
        self.ai_suggester = AIRedactionSuggester()
        self.redaction_engine = RedactionEngine()
        self.report_generator = RedactionReportGenerator()
        self.security_manager = SecurityManager()
        self.file_handler = FileHandler()

    def run(self):
        st.title("MultiDoc Redaction Assistant")
        
        uploaded_file = st.file_uploader(
            "Upload a document",
            type=["pdf", "docx", "txt"],
            help="Supported formats: PDF, DOCX, TXT"
        )
        
        if uploaded_file:
            # Create temporary file
            temp_file_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(uploaded_file.getvalue())
            
            # Extract and display text
            try:
                document_text = self.file_handler.extract_text(temp_file_path)
                st.subheader("Document Preview")
                st.text(document_text)
                
                # Get AI suggestions first
                with st.spinner("Analyzing document for sensitive information..."):
                    ai_suggestions = self.ai_suggester.get_redaction_suggestions(
                        temp_file_path,
                        sensitivity=50  # Default sensitivity threshold
                    )
                
                # Display AI suggestions
                if ai_suggestions:
                    st.subheader("AI-Suggested Redactions")
                    for i, suggestion in enumerate(ai_suggestions):
                        with st.expander(f"Suggestion #{i+1}: {suggestion['type']}"):
                            st.markdown(f"""
                            - **Text to Redact:** `{suggestion['text']}`
                            - **Type:** {suggestion['type']}
                            - **Confidence:** {suggestion['confidence']}%
                            - **Reason:** {suggestion['reason']}
                            """)
                            if st.button("Accept Suggestion", key=f"accept_{i}"):
                                if 'custom_redactions' not in st.session_state:
                                    st.session_state.custom_redactions = []
                                st.session_state.custom_redactions.append(suggestion)
                                st.success("Suggestion added to redaction list!")
                
                # Redaction interface
                st.subheader("Custom Redaction")
                text_to_redact = st.text_input("Enter text to redact:")
                redaction_type = st.selectbox(
                    "Redaction Type:",
                    ["PII", "CREDENTIALS", "FINANCIAL", "CUSTOM"]
                )
                reason = st.text_input("Reason for redaction (optional):")
                
                submit_button = st.button("Add Redaction")
                
                # Debug print
                st.write(f"Current redactions count before processing: {len(st.session_state.custom_redactions)}")
                
                if submit_button and text_to_redact:
                    with st.spinner("Analyzing document..."):
                        # Get AI suggestions
                        ai_suggestions = self.ai_suggester.analyze_text_for_redaction(
                            document_text,
                            text_to_redact,
                            redaction_type
                        )
                        
                        if ai_suggestions:
                            # Show preview of what will be redacted
                            st.subheader("Preview of Items to be Redacted:")
                            for idx, sugg in enumerate(ai_suggestions, 1):
                                st.write(f"{idx}. {sugg['text']} ({sugg['reason']})")
                            
                            # Confirm redaction
                            if st.button("Confirm Redactions"):
                                st.session_state.custom_redactions.extend(ai_suggestions)
                                st.success(f"Added {len(ai_suggestions)} redactions!")
                        else:
                            # Handle manual redaction
                            new_redaction = {
                                "type": redaction_type,
                                "text": text_to_redact,
                                "confidence": 100,
                                "reason": reason or "User-specified redaction",
                                "page": 0,
                                "bbox": [50, 50, 550, 70]
                            }
                            st.session_state.custom_redactions.append(new_redaction)
                            st.warning("Added exact text match only.")
                
                # Display current redactions
                if st.session_state.custom_redactions:
                    st.subheader("Current Redactions")
                    for i, redaction in enumerate(st.session_state.custom_redactions):
                        with st.expander(f"Redaction #{i+1}"):
                            st.markdown(f"""
                            - **Text to Redact:** `{redaction['text']}`
                            - **Type:** {redaction['type']}
                            - **Reason:** {redaction['reason']}
                            """)
                            
                            if st.button("Remove", key=f"remove_{i}"):
                                st.session_state.custom_redactions.pop(i)
                                st.rerun()
                
                # Process redactions
                if st.button("Apply Redactions"):
                    # Debug print
                    st.write(f"Attempting to process {len(st.session_state.custom_redactions)} redactions")
                    
                    if not st.session_state.custom_redactions:
                        st.error("Please add at least one redaction before processing")
                    else:
                        try:
                            with st.spinner("Applying redactions..."):
                                output_path = os.path.join(
                                    tempfile.gettempdir(),
                                    f"redacted_{uploaded_file.name}"
                                )
                                
                                redacted_path = self.redaction_engine.redact_document(
                                    temp_file_path,
                                    st.session_state.custom_redactions,  # Use session state
                                    output_path
                                )
                                
                                report = self.report_generator.create_report(
                                    temp_file_path,
                                    redacted_path,
                                    st.session_state.custom_redactions
                                )
                                
                                st.success("Document redacted successfully!")
                                
                                # Create two columns for side-by-side preview
                                col1, col2 = st.columns(2)

                                with col1:
                                    st.subheader("Original Document")
                                    st.text(document_text)

                                with col2:
                                    st.subheader("Redacted Document")
                                    # Extract and display redacted text
                                    redacted_text = self.file_handler.extract_text(redacted_path)
                                    st.text(redacted_text)

                                # Download buttons
                                with open(redacted_path, "rb") as f:
                                    st.download_button(
                                        "Download Redacted Document",
                                        f,
                                        file_name=f"redacted_{uploaded_file.name}"
                                    )
                                
                                st.download_button(
                                    "Download Redaction Report",
                                    report,
                                    file_name="redaction_report.txt"
                                )
                                
                        except Exception as e:
                            st.error(f"Error during redaction: {str(e)}")
                            
                        finally:
                            if os.path.exists(temp_file_path):
                                self.security_manager.secure_file_deletion(temp_file_path)
                            if os.path.exists(output_path):
                                self.security_manager.secure_file_deletion(output_path)
                
            except Exception as e:
                st.error(f"Error processing document: {str(e)}")

def run_app():
    app = MultiDocRedactionApp()
    app.run()

if __name__ == "__main__":
    run_app()