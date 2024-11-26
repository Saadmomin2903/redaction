import streamlit as st
from src.main import MultiDocRedactionApp

def main():
    st.set_page_config(
        page_title="MultiDoc Redaction Assistant",
        page_icon="🔒",
        layout="wide"
    )
    
    app = MultiDocRedactionApp()
    app.run()

if __name__ == "__main__":
    main() 