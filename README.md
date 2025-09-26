# Digital Economy Index — Q&A & Extraction Toolkit

A lightweight extraction, processing, and Q&A workspace for the OIC Digital Economy Index (ADEI). This project extracts structured ADEI data from a raw PDF, stores it as JSON and SQLite, and provides a Streamlit chat interface that answers natural-language questions by issuing SQL against the processed dataset via a LangChain SQL agent.

## Project overview

- Purpose: Extract the ADEI dataset (57 countries) from a source PDF, convert it to a structured JSON dataset, load that data into a SQLite database, and allow natural-language Q&A over the dataset using a LangChain SQL agent and a modern LLM (OpenAI or Google Gemini).
- Key features:
  - Document extraction pipeline using PyMuPDF + LangChain RAG pattern.
  - Pydantic models for strict, validated structured outputs.
  - JSON and SQLite output for easy downstream use.
  - Streamlit chat UI that converts user prompts to SQL and returns answers (text + optional simple charts).

## Quick start — prerequisites

- Python 3.10+ (project developed on macOS with Python 3.10)
- git (optional)
- An LLM API key (Google Generative AI or OpenAI depending on which agent you configure)

Create a virtual environment and install dependencies (example):

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# Install commonly used libraries; adjust versions as needed
pip install streamlit python-dotenv pandas pydantic langchain langchain-community PyMuPDF faiss-cpu
```

Note: The project imports a small set of language/LLM-specific packages such as `langchain_google_genai` and `langchain_openai` in different files. If you plan to use Google Gemini follow the Google Generative AI client library and LangChain integration instructions for your environment; for OpenAI use `openai` and LangChain's OpenAI LLM wrapper.

## Environment configuration

The project reads API keys from a `.env` file at the repository root. Create a `.env` file with the appropriate key(s):

```bash
# Example .env
GOOGLE_API_KEY=your_google_generative_api_key_here
# or
OPENAI_API_KEY=your_openai_api_key_here
```

The main file `src/config.py` also contains a small set of file-path constants and model names. You can edit these values to point to local paths if your filesystem layout differs:

- `RAW_DATA_PATH` — path to the input PDF (default: `data/raw/index.pdf`)
- `PROCESSED_DATA_PATH` — path to the extracted JSON (default: `data/processed/oic_digital_economy_index.json`)
- `DB_FILE_PATH` — path to the generated SQLite DB (default: `data/processed/digital_economy.db`)

## Usage

1. Extract structured JSON from the source PDF

   This runs the RAG extraction flow and saves structured country objects to `data/processed/oic_digital_economy_index.json`.

   ```bash
   # From repository root
   python main.py
   ```

   Notes:

   - `main.py` uses the `PyMuPDFLoader` via LangChain. Ensure `data/raw/index.pdf` exists or update `RAW_DATA_PATH` in `src/config.py`.
   - The extraction uses a Pydantic model to validate outputs; extraction may require tuning of LLM prompts or API configuration.

2. Load the JSON into SQLite

   The loader script reads the processed JSON and writes three normalized tables into a SQLite DB: `countries`, `dimension_summaries`, `pillars`, `sub_pillars`.

   ```bash
   # From repository root
   python src/load_to_db.py
   ```

   Output: `data/processed/digital_economy.db` (by default). If you see path-related errors, check `src/config.py` for the `DB_FILE_PATH` value.

3. Run the Streamlit Q&A app

   The project includes two Streamlit app variants: `myapp.py` (simpler) and `myapp2.py` (chart-aware). Run either from the repository root:

   ```bash
   streamlit run myapp.py
   # or
   streamlit run app.py
   ```

   - The app expects the SQLite DB to exist at the configured path (`data/processed/digital_economy.db` by default).
   - Provide the appropriate API key(s) in `.env` so the agent can call your chosen LLM.

Example interaction: ask questions in natural language such as "Which country has the highest score in the Innovation pillar?" or "Top 5 countries by ADEI rank." The app will convert queries into SQL, execute them, and return natural-language answers. `myapp2.py` additionally attempts to parse chartable responses and will show simple bar charts for ranked results.

## Project structure

Top-level files and directories (key items):

- `main.py` — Extraction driver that processes the PDF, runs the RAG chain, and writes structured JSON.
- `myapp.py` — Streamlit Q&A app (LLM-driven SQL agent).
- `myapp2.py` — Enhanced Streamlit Q&A with chart parsing and visualizations.
- `chart_models.py` — Pydantic models used to represent chartable data.
- `data/` — Data folder
  - `raw/` — Raw source PDF(s)
  - `processed/` — Processed JSON and generated SQLite DB
- `src/` — Helper modules and core logic
  - `core/` — `extractor.py` (RAG chain builders), `data_models.py` (Pydantic data schemas)
  - `config.py` — Basic configuration constants (file paths, model names, countries list)
  - `load_to_db.py` — Loads the processed JSON into an SQLite DB

## Configuration details

- File paths: Change the constants in `src/config.py` if you want to use different locations for raw/processed data or the DB.
- API keys: Add `GOOGLE_API_KEY` or `OPENAI_API_KEY` to the `.env` file. The Streamlit apps call `load_dotenv()` to pick these up.
- LLM selection: Files reference both Google and OpenAI LLM wrappers; open and edit `myapp.py` / `myapp2.py` to select which provider and model you want to use. The LLM-specific client libraries must be installed separately.

## Troubleshooting & common gotchas

- AttributeError: 'str' object has no attribute 'exists'

  - Cause: A path constant was used directly with `.exists()` instead of converting to a `Path` object. Fix: wrap the string path with `Path(...)` or update the code to use `Path` consistently. Example:

    ```python
    from pathlib import Path
    if not Path(DB_PATH).exists():
        # handle missing db
    ```

- Missing API key errors in the Streamlit app: ensure `.env` contains the required key and the app was restarted after editing `.env`.
- Extraction returns invalid JSON or fails validation: extraction prompts and parser config may need adjustment, or the LLM output may need post-processing. Check console logs printed by `main.py`.

## Contributing

Contributions are welcome. A suggested lightweight workflow:

1. Fork the repository.
2. Create a feature branch: `git checkout -b feat/your-feature`.
3. Run tests / smoke-check locally (if you add tests).
4. Open a pull request with a clear description and a small, focused change.

Please open issues for bugs, feature requests, or to propose enhancements.
