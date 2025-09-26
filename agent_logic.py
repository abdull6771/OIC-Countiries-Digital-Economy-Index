import os
from dotenv import load_dotenv

# LangChain imports
from langchain.sql_database import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_google_genai import GoogleGenerativeAI

def get_llm():
    """
    Initializes and returns the Google Generative AI LLM.
    Loads the API key from the .env file.
    """
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        # In a real app, you might raise an exception or handle this more gracefully
        print("Error: GOOGLE_API_KEY not found in environment variables.")
        return None
    
    # Initialize and return the LLM instance
    llm = GoogleGenerativeAI(
        model="gemini-1.5-pro-latest",
        google_api_key=api_key,
        temperature=0.1,
    )
    return llm

def get_sql_agent(llm: GoogleGenerativeAI, db_engine: SQLDatabase):
    """
    Initializes and returns the LangChain SQL Agent using the provided LLM and DB engine.
    
    Args:
        llm: An initialized LangChain LLM object.
        db_engine: An initialized LangChain SQLDatabase object.
        
    Returns:
        An executable LangChain agent.
    """
    # Create the SQL agent. This agent is aware of the database schema 
    # and can write and execute SQL queries.
    agent_executor = create_sql_agent(
        llm=llm,
        db=db_engine,
        agent_type="zero-shot-react-description", # Generic agent type compatible with Gemini
        verbose=True, # Set to True to see the agent's thought process in the terminal
        handle_parsing_errors=True, # Gracefully handle cases where the LLM output is not perfect
    )
    return agent_executor
