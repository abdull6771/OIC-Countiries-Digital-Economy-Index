import sqlite3
import json
from pathlib import Path
from config import COUNTRIES, RAW_DATA_PATH, PROCESSED_DATA_PATH, DB_FILE_PATH


# --- Configuration ---
# Assumes the script is run from the project root directory
# Adjust paths if you run it from within src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
JSON_FILE_PATH = PROCESSED_DATA_PATH
DB_FILE_PATH = DB_FILE_PATH

# --- SQL Statements to Create Tables ---
CREATE_COUNTRIES_TABLE = """
CREATE TABLE IF NOT EXISTS countries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    adei_score INTEGER,
    adei_rank INTEGER
);
"""

CREATE_DIMENSION_SUMMARIES_TABLE = """
CREATE TABLE IF NOT EXISTS dimension_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id INTEGER,
    dimension TEXT,
    pillar TEXT,
    value INTEGER,
    rank INTEGER,
    FOREIGN KEY (country_id) REFERENCES countries (id)
);
"""

CREATE_PILLARS_TABLE = """
CREATE TABLE IF NOT EXISTS pillars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id INTEGER,
    pillar_name TEXT,
    total_pillar_score REAL,
    FOREIGN KEY (country_id) REFERENCES countries (id)
);
"""

CREATE_SUB_PILLARS_TABLE = """
CREATE TABLE IF NOT EXISTS sub_pillars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pillar_id INTEGER,
    name TEXT,
    score REAL,
    FOREIGN KEY (pillar_id) REFERENCES pillars (id)
);
"""

def create_database_schema(cursor):
    """Creates the database tables."""
    print("Creating database tables...")
    cursor.execute(CREATE_COUNTRIES_TABLE)
    cursor.execute(CREATE_DIMENSION_SUMMARIES_TABLE)
    cursor.execute(CREATE_PILLARS_TABLE)
    cursor.execute(CREATE_SUB_PILLARS_TABLE)
    print("Tables created successfully.")

def load_data_into_db():
    """Parses the JSON file and loads the data into the SQLite database."""
    # Check if the JSON file exists
    from pathlib import Path
    if not Path(JSON_FILE_PATH).exists():
        print(f"Error: JSON file not found at {JSON_FILE_PATH}")
        return

    # Load the JSON data
    with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
        all_countries_data = json.load(f)

    # Connect to the SQLite database (it will be created if it doesn't exist)
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()

    # Create the tables
    create_database_schema(cursor)

    print("\nStarting data insertion...")
    # Loop through each country in the JSON file
    for country_data in all_countries_data:
        if not country_data: continue # Skip empty entries

        country_name = country_data.get('country_name')
        print(f"Processing {country_name}...")

        # --- 1. Insert into 'countries' table ---
        cursor.execute(
            "INSERT OR IGNORE INTO countries (name, adei_score, adei_rank) VALUES (?, ?, ?)",
            (
                country_name,
                country_data.get('overall_adei_score'),
                country_data.get('overall_adei_rank')
            )
        )
        # Get the ID of the country we just inserted
        country_id = cursor.execute("SELECT id FROM countries WHERE name = ?", (country_name,)).fetchone()[0]

        # --- 2. Insert into 'dimension_summaries' table ---
        for summary in country_data.get('dimension_summary', []):
            cursor.execute(
                """
                INSERT INTO dimension_summaries (country_id, dimension, pillar, value, rank)
                VALUES (?, ?, ?, ?, ?)
                """,
                (country_id, summary['dimension'], summary['pillar'], summary['value'], summary['rank'])
            )

        # --- 3. Insert into 'pillars' and 'sub_pillars' tables ---
        for pillar in country_data.get('detailed_pillars', []):
            cursor.execute(
                "INSERT INTO pillars (country_id, pillar_name, total_pillar_score) VALUES (?, ?, ?)",
                (country_id, pillar['pillar_name'], pillar['total_pillar_score'])
            )
            # Get the ID of the pillar we just inserted
            pillar_id = cursor.lastrowid

            for sub_pillar in pillar.get('sub_pillars', []):
                cursor.execute(
                    "INSERT INTO sub_pillars (pillar_id, name, score) VALUES (?, ?, ?)",
                    (pillar_id, sub_pillar['name'], sub_pillar['score'])
                )

    # Commit the changes and close the connection
    conn.commit()
    conn.close()
    print(f"\nData loading complete. Database saved to '{DB_FILE_PATH}'.")

if __name__ == "__main__":
    load_data_into_db()
