"""
Converts '27 Jan_data ADEI.xlsx' into the oic_digital_economy_index.json format
and rebuilds the SQLite database.
"""

import pandas as pd
import json
import sqlite3
import math
from pathlib import Path

# ─────────────────────────────────────────────
# 1.  Column-code → sub-pillar name mapping
# ─────────────────────────────────────────────
# Order matches the Excel column order exactly.
# Pillar totals (keys '1','2',…,'9') are used for dimension_summary values.

PILLAR_STRUCTURE = {
    "First Pillar: Institutions": {
        "dimension": "Digital Foundation",
        "pillar_short": "Institutions",
        "total_col": "1",
        "sub_cols": [
            ("1.1.1", "Political Environment"),
            ("1.1.2", "Political Stability and Security"),
            ("1.1.3", "Government Effectiveness"),
            ("1.1",   "Voice and Accountability"),
            ("1.2.1", "Regulatory Environment"),
            ("1.2.2", "Regulatory Quality"),
            ("1.2.3", "Rule of Law"),
            ("1.2",   "Control of Corruption"),
            ("1.3.1", "Technology Governance"),
            ("1.3.2", "Secure Internet Servers"),
            ("1.3.3", "E-Security"),
            ("1.3.4", "Online Shopping"),
            ("1.3.5", "ICT Regulatory Environment"),
            ("1.3.6", "Regulation of Emerging Technologies"),
            ("1.3.7", "E-commerce Legislation"),
            ("1.3",   "Protection of content privacy under the law"),
        ],
    },
    "Second Pillar: Infrastructure": {
        "dimension": "Digital Foundation",
        "pillar_short": "Infrastructure",
        "total_col": "2",
        "sub_cols": [
            ("2.1",   "Access to ICT"),
            ("2.2",   "Use of ICT"),
            ("2.3.1", "Technological Inclusion"),
            ("2.3.2", "E-Participation"),
            ("2.3.3", "Socioeconomic gap in the use of digital payments"),
            ("2.3.4", "Availability of local content online"),
            ("2.3.5", "Gender gap in internet use"),
            ("2.3",   "Rural gap in the use of digital payments"),
            ("2.4",   "Logistical Performance"),
        ],
    },
    "Third Pillar: Workforce": {
        "dimension": "Digital Works",
        "pillar_short": "Workforce",
        "total_col": "3",
        "sub_cols": [
            ("3.1", "Expenditure on education as a % of GDP"),
            ("3.2", "Knowledge-intensive employment %"),
            ("3.3", "ICT skills in the education system"),
        ],
    },
    "Fourth Pillar: E-Government": {
        "dimension": "E-Government",
        "pillar_short": "E-Government",
        "total_col": "4",
        "sub_cols": [
            ("4.1", "Government services online"),
            ("4.2", "Telecommunication Infrastructure"),
            ("4.3", "Human Capital Component"),
        ],
    },
    "Fifth Pillar: Innovation": {
        "dimension": "Innovation",
        "pillar_short": "Innovation",
        "total_col": "5",
        "sub_cols": [
            ("5.1", "Percentage of total R&D expenditure financed by the business sector"),
            ("5.2", "University-industry collaboration in R&D"),
            ("5.3", "Knowledge impact"),
            ("5.4", "Knowledge absorption"),
        ],
    },
    "Sixth Pillar: Future Technologies": {
        "dimension": "Readiness in digital\nfor the citizen",
        "pillar_short": "Future Technologies",
        "total_col": "6",
        "sub_cols": [
            ("6.1", "Adoption of emerging technologies"),
            ("6.2", "Investment in emerging technologies"),
            ("6.3", "Artificial Intelligence (AI) strategy"),
        ],
    },
    "Seventh Pillar: Market Development and Sophistication": {
        "dimension": "Market Development and Sophistication",
        "pillar_short": "Market Development\nand Sophistication",
        "total_col": "7",
        "sub_cols": [
            ("7.1", "Financing of startups and ease of access"),
            ("7.2", "Domestic credit to private sector, % of GDP"),
            ("7.3", "Diversification of local industry"),
        ],
    },
    "Eighth Pillar: Financial Market Development": {
        "dimension": "Financial Market Development",
        "pillar_short": "Financial Market\nDevelopment",
        "total_col": "8",
        "sub_cols": [
            ("8.1.1", "FinTech and Financial Inclusion"),
            ("8.1.2", "Percentage of population (age 15+) who own bank accounts"),
            ("8.1.3", "Percentage (age 15+) who own a debit or credit card"),
            ("8.1",   "Percentage (age 15+) who have made or received a digital payment"),
            ("8.2",   "Market capitalization as a % of GDP"),
        ],
    },
    "Ninth Pillar: Sustainable Development Goals": {
        "dimension": "Sustainable Development",
        "pillar_short": "Sustainable\nDevelopment",
        "total_col": "9",
        "sub_cols": [
            ("9.1", "Goal 1: No Poverty"),
            ("9.2", "Goal 2: Zero Hunger"),
            ("9.3", "Goal 3: Good Health and Well-being"),
            ("9.4", "Goal 4: Quality Education"),
            ("9.5", "Goal 8: Decent Work and Economic Growth"),
            ("9.6", "Goal 9: Industry, Innovation and Infrastructure"),
            ("9.7", "Goal 17: Partnerships for the Goals"),
        ],
    },
}


# ─────────────────────────────────────────────
# 2.  Helpers
# ─────────────────────────────────────────────

def safe_float(v):
    """Return float or 0.0 for None/NaN."""
    if v is None:
        return 0.0
    try:
        f = float(v)
        return 0.0 if math.isnan(f) else f
    except (TypeError, ValueError):
        return 0.0


def normalise_col_header(h):
    """Convert float headers like 1.1 → '1.1', keep strings as-is."""
    if isinstance(h, float):
        # e.g. 1.1 → '1.1', 2.0 → '2'
        if h == int(h):
            return str(int(h))
        return str(h)
    return str(h)


# ─────────────────────────────────────────────
# 3.  Read Excel
# ─────────────────────────────────────────────

EXCEL_PATH = Path("27 Jan_data ADEI.xlsx")
df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1", header=0)

# Normalise column names
df.columns = [normalise_col_header(c) for c in df.columns]

# Keep only the most-recent year per country (in case there are multi-year rows)
if "Year" in df.columns:
    df = df.sort_values("Year", ascending=False).drop_duplicates(subset="Country", keep="first")

print(f"Loaded {len(df)} countries from Excel.")

# ─────────────────────────────────────────────
# 4.  Compute pillar ranks for dimension_summary
# ─────────────────────────────────────────────

pillar_total_cols = [info["total_col"] for info in PILLAR_STRUCTURE.values()]
for col in pillar_total_cols:
    rank_col = f"_rank_{col}"
    df[rank_col] = df[col].rank(ascending=False, method="min").astype(int)

# ─────────────────────────────────────────────
# 5.  Build JSON list
# ─────────────────────────────────────────────

all_countries = []

for _, row in df.iterrows():
    country_name = str(row["Country"]).strip()
    adei_score = int(round(safe_float(row.get("ADEI", 0))))
    adei_rank  = int(row.get("Rank", 0)) if pd.notna(row.get("Rank", None)) else 0

    # --- dimension_summary ---
    dimension_summary = []
    for pillar_name, info in PILLAR_STRUCTURE.items():
        tcol = info["total_col"]
        val  = int(round(safe_float(row.get(tcol, 0))))
        rank = int(df.loc[df["Country"] == row["Country"], f"_rank_{tcol}"].iloc[0])
        dimension_summary.append({
            "dimension": info["dimension"],
            "pillar":    info["pillar_short"],
            "value":     val,
            "rank":      rank,
        })

    # --- detailed_pillars ---
    detailed_pillars = []
    for pillar_name, info in PILLAR_STRUCTURE.items():
        tcol  = info["total_col"]
        total = round(safe_float(row.get(tcol, 0)), 2)
        sub_pillars = []
        for code, name in info["sub_cols"]:
            score = round(safe_float(row.get(code, 0)), 2)
            sub_pillars.append({"name": name, "score": score})
        detailed_pillars.append({
            "pillar_name":        pillar_name,
            "total_pillar_score": total,
            "sub_pillars":        sub_pillars,
        })

    all_countries.append({
        "country_name":      country_name,
        "overall_adei_score": adei_score,
        "overall_adei_rank":  adei_rank,
        "dimension_summary":  dimension_summary,
        "detailed_pillars":   detailed_pillars,
    })

# Sort by rank
all_countries.sort(key=lambda x: x["overall_adei_rank"])

# ─────────────────────────────────────────────
# 6.  Write JSON (both locations)
# ─────────────────────────────────────────────

JSON_PATHS = [
    Path("data/oic_digital_economy_index.json"),
    Path("data/processed/oic_digital_economy_index.json"),
]

for p in JSON_PATHS:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(all_countries, f, ensure_ascii=False, indent=4)
    print(f"JSON written → {p}")

# ─────────────────────────────────────────────
# 7.  Rebuild SQLite database
# ─────────────────────────────────────────────

DB_PATH = Path("data/processed/digital_economy.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Remove old DB so we start clean
if DB_PATH.exists():
    DB_PATH.unlink()
    print("Old database removed.")

conn = sqlite3.connect(str(DB_PATH))
cur  = conn.cursor()

# Create tables
cur.executescript("""
CREATE TABLE IF NOT EXISTS countries (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    adei_score INTEGER,
    adei_rank  INTEGER
);

CREATE TABLE IF NOT EXISTS dimension_summaries (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id INTEGER,
    dimension  TEXT,
    pillar     TEXT,
    value      INTEGER,
    rank       INTEGER,
    FOREIGN KEY (country_id) REFERENCES countries (id)
);

CREATE TABLE IF NOT EXISTS pillars (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id        INTEGER,
    pillar_name       TEXT,
    total_pillar_score REAL,
    FOREIGN KEY (country_id) REFERENCES countries (id)
);

CREATE TABLE IF NOT EXISTS sub_pillars (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    pillar_id INTEGER,
    name     TEXT,
    score    REAL,
    FOREIGN KEY (pillar_id) REFERENCES pillars (id)
);
""")

for country in all_countries:
    cur.execute(
        "INSERT OR IGNORE INTO countries (name, adei_score, adei_rank) VALUES (?,?,?)",
        (country["country_name"], country["overall_adei_score"], country["overall_adei_rank"]),
    )
    country_id = cur.lastrowid

    for ds in country["dimension_summary"]:
        cur.execute(
            "INSERT INTO dimension_summaries (country_id, dimension, pillar, value, rank) VALUES (?,?,?,?,?)",
            (country_id, ds["dimension"], ds["pillar"], ds["value"], ds["rank"]),
        )

    for pillar in country["detailed_pillars"]:
        cur.execute(
            "INSERT INTO pillars (country_id, pillar_name, total_pillar_score) VALUES (?,?,?)",
            (country_id, pillar["pillar_name"], pillar["total_pillar_score"]),
        )
        pillar_id = cur.lastrowid
        for sp in pillar["sub_pillars"]:
            cur.execute(
                "INSERT INTO sub_pillars (pillar_id, name, score) VALUES (?,?,?)",
                (pillar_id, sp["name"], sp["score"]),
            )

conn.commit()
conn.close()
print(f"Database rebuilt → {DB_PATH}")
print(f"Total countries inserted: {len(all_countries)}")
