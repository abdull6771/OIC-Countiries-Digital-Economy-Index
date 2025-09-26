import streamlit as st
from pathlib import Path
import os
from dotenv import load_dotenv

# LangChain imports for SQL agent
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_openai import ChatOpenAI # Or use GoogleGenerativeAI
# from src.core.config import COUNTRIES, RAW_DATA_PATH, PROCESSED_DATA_PATH, DB_FILE_PATH
DB_FILE_PATH = "/Users/mac/Documents/My_ML_Project/Customer_Review/data/processed/digital_economy.db"

# --- Page Configuration ---
st.set_page_config(
    page_title="Digital Economy Index Q&A",
    page_icon="💡",
    layout="centered",
)

st.title("💡 Digital Economy Index Q&A")
st.write("Ask questions in natural language about the digital economy data of 57 Islamic countries.")

# --- Database Connection ---
# Define the path to the database
DB_PATH = DB_FILE_PATH

def get_db_engine():
    """Initializes and returns the SQLDatabase engine."""
    from pathlib import Path
    if not Path(DB_PATH).exists():
        st.error(f"Database not found at {DB_PATH}. Please run the data loading script first.")
        st.stop()
    
    # Use f-string for cross-platform compatibility
    return SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")

# --- LLM and Agent Initialization ---
def get_sql_agent(db_engine):
    """Initializes and returns the LangChain SQL Agent."""
    load_dotenv()
    
    # For Google Gemini:
    from langchain_google_genai import GoogleGenerativeAI
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("GOOGLE_API_KEY not found. Please add it to your .env file.")
        st.stop()
        
    llm = GoogleGenerativeAI(
        model="gemini-1.5-pro-latest",
        google_api_key=api_key,
        temperature=0.1,
        # max_output_tokens=8192 # This is often not needed unless you see truncated responses
    )

    # Create the SQL agent. This agent is aware of the database schema and can write SQL queries.
    agent_executor = create_sql_agent(
        llm=llm,
        db=db_engine,
        # --- THIS IS THE FIX ---
        # Use a generic agent type compatible with Google's models.
        agent_type="zero-shot-react-description", 
        verbose=True, 
        handle_parsing_errors=True,
    )
    return agent_executor

# --- Main Application Logic ---
db = get_db_engine()
agent = get_sql_agent(db)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Example questions to guide the user
st.sidebar.title("Example Questions")
st.sidebar.info(
    """
    - Which country has the highest score in the Innovation pillar?
    - What are the top 5 countries by ADEI rank?
    - Compare the Workforce and Infrastructure scores for Turkey and Malaysia.
    - What is the 'Rule of Law' score for Saudi Arabia?
    """
)

# React to user input
if prompt := st.chat_input("Ask a question about the digital economy index..."):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Thinking..."):
        try:
            # The agent will convert the prompt to SQL, execute it, and return the answer
            response = agent.invoke({"input": prompt})
            response_content = response["output"]
        except Exception as e:
            response_content = f"Sorry, I encountered an error: {e}"

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(response_content)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response_content})

