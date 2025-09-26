from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import PydanticOutputParser # <--- IMPORT THIS
from dotenv import load_dotenv
import os

from src.core.data_models import CountryData # Import from your models file
# LLM_MODEL_NAME is not used here since the model is hardcoded, but we'll leave the import
from src.config import LLM_MODEL_NAME 

def create_rag_chain(file_path: str):
    """Creates the structured RAG chain using Google Generative AI."""
    load_dotenv() # Loads API key from .env file
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")

    loader = PyMuPDFLoader(file_path)
    documents = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=8000, chunk_overlap=400) # Increased chunk size for better context
    texts = text_splitter.split_documents(documents)
    
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
    vector_store = FAISS.from_documents(texts, embeddings)
    retriever = vector_store.as_retriever(search_kwargs={"k": 15})
    
    # --- 1. Create a Pydantic Output Parser ---
    parser = PydanticOutputParser(pydantic_object=CountryData)

    # --- 2. Define the Prompt Template with Format Instructions ---
    prompt_template = """
You are an expert data extraction system. Your task is to extract detailed information from the provided document context based on the user's question.
Ensure you extract all nine pillars detailed in the context. Do not stop until all data for the requested country is included.
You must format the output strictly as a JSON object that adheres to the schema provided below.

CONTEXT:
{context}

QUESTION:
{question}

FORMAT INSTRUCTIONS:
{format_instructions}
"""
    
    prompt = ChatPromptTemplate.from_template(
        template=prompt_template,
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    # --- 3. Initialize the Google Generative AI Model ---
    # Using a powerful model like Gemini 1.5 Pro is recommended for this complex task.
    llm = GoogleGenerativeAI(
    model="gemini-1.5-pro-latest",
    google_api_key=api_key,
    temperature=0.1,
    max_output_tokens=8192 
)


    # --- 4. Construct the RAG Chain with the Explicit Parser ---
    rag_chain = (
        {
            "context": retriever,
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | parser # Pipe the LLM's string output to the parser
    )
    
    return rag_chain

# src/core/extractor.py

# ... (keep all your existing imports)

def create_rag_chain_from_documents(documents: list):
    """Creates a structured RAG chain from a list of documents."""
    api_key = os.getenv("GOOGLE_API_KEY")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
    
    # Create a vector store and retriever just for the provided documents
    vector_store = FAISS.from_documents(documents, embeddings)
    retriever = vector_store.as_retriever(search_kwargs={"k": len(documents)}) # Use all chunks for context

    parser = PydanticOutputParser(pydantic_object=CountryData)
    
    prompt_template = """
You are an expert data extraction system. Your task is to extract detailed information from the provided document context based on the user's question.
Ensure you extract all nine pillars detailed in the context. Do not stop until all data for the requested country is included.
You must format the output strictly as a JSON object that adheres to the schema provided below.

CONTEXT:
{context}

QUESTION:
{question}

FORMAT INSTRUCTIONS:
{format_instructions}
"""
     # Your existing prompt template
    prompt = ChatPromptTemplate.from_template(
        template=prompt_template,
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    llm = GoogleGenerativeAI(
    model="gemini-1.5-pro-latest",
    google_api_key=api_key,
    temperature=0.1,
    max_output_tokens=8192 
)
    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | parser
    )
    return rag_chain
