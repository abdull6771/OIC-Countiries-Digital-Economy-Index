# src/main.py

import os
import json
from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Import your core functions and models
from src.core.extractor import create_rag_chain_from_documents
from src.config import COUNTRIES, RAW_DATA_PATH, PROCESSED_DATA_PATH

def run_extraction():
    """Main function to run the data extraction process."""
    load_dotenv()
    os.makedirs(os.path.dirname(PROCESSED_DATA_PATH), exist_ok=True)

    # Load the entire document once
    print("Loading the full document...")
    loader = PyMuPDFLoader(RAW_DATA_PATH)
    all_docs = loader.load()
    
    # Split the document into pages (or smaller chunks if needed)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    all_chunks = text_splitter.split_documents(all_docs)

    all_countries_data = []

    for i, country in enumerate(COUNTRIES):
        print(f"Processing {country}...")

        # --- Isolate Chunks for the Current Country ---
        next_country = COUNTRIES[i + 1] if i + 1 < len(COUNTRIES) else "End of Document"
        
        country_chunks = []
        in_country_section = False
        for chunk in all_chunks:
            if country.lower() in chunk.page_content.lower():
                in_country_section = True
            if next_country.lower() in chunk.page_content.lower() and in_country_section:
                # We've reached the start of the next country's section
                if country.lower() not in next_country.lower(): # Handles cases like "Guinea" vs "Guinea-Bissau"
                    break
            if in_country_section:
                country_chunks.append(chunk)

        if not country_chunks:
            print(f"Warning: No content found for {country}. Skipping.")
            continue

        print(f"Found {len(country_chunks)} chunks for {country}.")

        # --- Create a RAG chain specifically for these chunks ---
        rag_chain = create_rag_chain_from_documents(country_chunks)
        
        try:
            question = f"Extract the complete digital economy index data for {country} from the provided context."
            structured_output = rag_chain.invoke(question)
            all_countries_data.append(structured_output.dict())
            print(f"Successfully extracted data for {country}.")
        except Exception as e:
            print(f"Could not extract data for {country}. Error: {e}")

    # Save the final data
    with open(PROCESSED_DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_countries_data, f, ensure_ascii=False, indent=4)

    print(f"\nExtraction complete. Data saved to '{PROCESSED_DATA_PATH}'.")

if __name__ == "__main__":
    run_extraction()
