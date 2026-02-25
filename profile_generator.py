import sqlite3
import pandas as pd
import plotly.graph_objects as go
import pycountry # <-- Import the new library
def get_country_list(db_connection):
    """Fetches a sorted list of all country names from the database."""
    query = "SELECT name FROM countries ORDER BY name ASC;"
    df = pd.read_sql_query(query, db_connection)
    return df['name'].tolist()

def get_country_profile_data(country_name: str, db_connection):
    """
    Queries the database for all data related to a specific country.
    """
    # Query for main ADEI score and rank
    country_query = "SELECT adei_score, adei_rank FROM countries WHERE name = ?;"
    main_stats = pd.read_sql_query(country_query, db_connection, params=(country_name,))

    # Query for the 9 main pillar scores for the radar chart
    pillars_query = """
    SELECT p.pillar_name, p.total_pillar_score
    FROM pillars p
    JOIN countries c ON p.country_id = c.id
    WHERE c.name = ?;
    """
    pillars_df = pd.read_sql_query(pillars_query, db_connection, params=(country_name,))
    
    # Clean up pillar names for better display
    pillars_df['pillar_name'] = pillars_df['pillar_name'].str.replace(r'^\w+\sPillar:\s', '', regex=True)


    # Query for all sub-pillar scores
    sub_pillars_query = """
    SELECT p.pillar_name, sp.name AS indicator, sp.score
    FROM sub_pillars sp
    JOIN pillars p ON sp.pillar_id = p.id
    JOIN countries c ON p.country_id = c.id
    WHERE c.name = ?
    ORDER BY p.id, sp.id;
    """
    sub_pillars_df = pd.read_sql_query(sub_pillars_query, db_connection, params=(country_name,))
    
    # Clean up pillar names for grouping
    sub_pillars_df['pillar_name'] = sub_pillars_df['pillar_name'].str.replace(r'^\w+\sPillar:\s', '', regex=True)


    return {
        "main_stats": main_stats,
        "pillars_df": pillars_df,
        "sub_pillars_df": sub_pillars_df
    }

def create_radar_chart(df: pd.DataFrame):
    """Creates a Plotly radar chart from a dataframe of pillar scores."""
    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=df['total_pillar_score'],
        theta=df['pillar_name'],
        fill='toself',
        name='Score'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=False,
        title=dict(text="Pillar Performance Radar", x=0.5)
    )
    return fig

def get_comparison_data(country_names: list, db_connection):
    """
    Queries the database for data needed to compare multiple countries.
    
    Args:
        country_names (list): A list of country names to compare.
        db_connection: An active sqlite3 connection object.
        
    Returns:
        A tuple of two pandas DataFrames: (main_stats_df, pillars_df).
    """
    if not country_names:
        # Return empty DataFrames if no countries are selected
        return pd.DataFrame(), pd.DataFrame()

    # Create a string of placeholders for the SQL IN clause (e.g., "?, ?, ?")
    placeholders = ', '.join(['?'] * len(country_names))

    # Query for main ADEI scores and ranks for the selected countries
    main_stats_query = f"""
    SELECT name, adei_score, adei_rank
    FROM countries
    WHERE name IN ({placeholders})
    ORDER BY adei_rank ASC;
    """
    main_stats_df = pd.read_sql_query(main_stats_query, db_connection, params=country_names)

    # Query for the 9 main pillar scores for the selected countries
    pillars_query = f"""
    SELECT
        c.name,
        p.pillar_name,
        p.total_pillar_score
    FROM pillars p
    JOIN countries c ON p.country_id = c.id
    WHERE c.name IN ({placeholders});
    """
    pillars_df = pd.read_sql_query(pillars_query, db_connection, params=country_names)
    
    # Clean up pillar names for better chart labels (e.g., "First Pillar: Institutions" -> "Institutions")
    pillars_df['pillar_name'] = pillars_df['pillar_name'].str.replace(r'^\w+\sPillar:\s', '', regex=True)

    return main_stats_df, pillars_df



def get_leaderboard_data(db_connection):
    """Fetches top 10 and bottom 10 countries by ADEI rank."""
    query = "SELECT name, adei_score, adei_rank FROM countries ORDER BY adei_rank ASC;"
    df = pd.read_sql_query(query, db_connection)
    top_10 = df.head(10)
    bottom_10 = df.tail(10).sort_values(by="adei_rank", ascending=True)
    return top_10, bottom_10

def get_average_pillar_scores(db_connection):
    """Calculates the average score for each of the 9 pillars across all countries."""
    query = "SELECT pillar_name, AVG(total_pillar_score) as average_score FROM pillars GROUP BY pillar_name;"
    df = pd.read_sql_query(query, db_connection)
    df['pillar_name'] = df['pillar_name'].str.replace(r'^\w+\sPillar:\s', '', regex=True)
    return df

def get_pillar_rankings(pillar_name: str, db_connection):
    """
    Returns all countries ranked by score for a specific pillar,
    plus all sub-pillar scores for that pillar across all countries.
    """
    countries_query = """
    SELECT c.name, c.adei_rank, p.total_pillar_score
    FROM pillars p
    JOIN countries c ON p.country_id = c.id
    WHERE p.pillar_name = ?
    ORDER BY p.total_pillar_score DESC;
    """
    countries_df = pd.read_sql_query(countries_query, db_connection, params=(pillar_name,))
    countries_df.insert(0, 'pillar_rank', range(1, len(countries_df) + 1))

    sub_pillars_query = """
    SELECT c.name, sp.name AS indicator, sp.score
    FROM sub_pillars sp
    JOIN pillars p ON sp.pillar_id = p.id
    JOIN countries c ON p.country_id = c.id
    WHERE p.pillar_name = ?
    ORDER BY c.adei_rank, sp.id;
    """
    sub_pillars_df = pd.read_sql_query(sub_pillars_query, db_connection, params=(pillar_name,))

    return countries_df, sub_pillars_df


def get_all_pillar_names(db_connection):
    """Returns the ordered list of distinct pillar names from the database."""
    query = "SELECT DISTINCT pillar_name FROM pillars ORDER BY pillar_name;"
    df = pd.read_sql_query(query, db_connection)
    # Sort by pillar number prefix (First, Second, …)
    order = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth"]
    def sort_key(n):
        for i, word in enumerate(order):
            if n.startswith(word):
                return i
        return 99
    names = sorted(df['pillar_name'].tolist(), key=sort_key)
    return names


def get_geo_pillar_data(pillar_name: str, db_connection):
    """
    Returns a dataframe with iso_alpha, country name, adei_score, adei_rank,
    and the score for the specified pillar (or overall ADEI if pillar_name is None).
    """
    if pillar_name is None:
        query = "SELECT name, adei_score AS score, adei_rank FROM countries;"
        df = pd.read_sql_query(query, db_connection)
    else:
        query = """
        SELECT c.name, p.total_pillar_score AS score, c.adei_score, c.adei_rank
        FROM pillars p
        JOIN countries c ON p.country_id = c.id
        WHERE p.pillar_name = ?;
        """
        df = pd.read_sql_query(query, db_connection, params=(pillar_name,))

    def get_iso_alpha(country_name):
        special = {
            "Iran, Islamic Rep.": "Iran",
            "Brunei Darussalam": "Brunei",
            "Cote d'Ivoire": "CIV",
            "Syrian Arab Republic": "SYR",
        }
        if country_name in special:
            val = special[country_name]
            if len(val) == 3:
                return val
            country_name = val
        try:
            return pycountry.countries.search_fuzzy(country_name)[0].alpha_3
        except LookupError:
            return None

    df['iso_alpha'] = df['name'].apply(get_iso_alpha)
    return df.dropna(subset=['iso_alpha'])


def get_map_data(db_connection):
    """Fetches country scores and adds ISO Alpha-3 codes for mapping."""
    query = "SELECT name, adei_score FROM countries;"
    df = pd.read_sql_query(query, db_connection)

    def get_iso_alpha(country_name):
        # Handle special cases where names might not match pycountry's database
        if country_name == "Iran, Islamic Rep.":
            country_name = "Iran"
        if country_name == "Brunei Darussalam":
            country_name = "Brunei"
        if country_name == "Cote d'Ivoire":
            return "CIV" # Direct mapping for names with apostrophes
        if country_name == "Syrian Arab Republic":
            return "SYR"
            
        try:
            return pycountry.countries.search_fuzzy(country_name)[0].alpha_3
        except LookupError:
            return None # Return None if country is not found

    df['iso_alpha'] = df['name'].apply(get_iso_alpha)
    return df.dropna(subset=['iso_alpha']) # Drop rows where no ISO code was found


# ─────────────────────────────────────────────
# Regional groupings for peer comparison and geo aggregation
# ─────────────────────────────────────────────
COUNTRY_REGIONS = {
    "GCC": ["United Arab Emirates", "Saudi Arabia", "Kuwait", "Qatar", "Bahrain", "Oman"],
    "North Africa": ["Morocco", "Algeria", "Tunisia", "Libya", "Egypt"],
    "East Africa": ["Somalia", "Djibouti", "Comoros", "Mozambique"],
    "West Africa": ["Nigeria", "Senegal", "Gambia", "Guinea", "Guinea-Bissau",
                    "Sierra Leone", "Burkina Faso", "Mali", "Niger", "Chad",
                    "Togo", "Benin", "Cote d'Ivoire"],
    "Central Africa": ["Cameroon", "Gabon", "Equatorial Guinea"],
    "Middle East & Levant": ["Jordan", "Iraq", "Syrian Arab Republic", "Yemen",
                              "Palestine", "Lebanon", "Iran, Islamic Rep."],
    "South Asia": ["Pakistan", "Bangladesh", "Afghanistan", "Maldives"],
    "Southeast Asia": ["Malaysia", "Indonesia", "Brunei Darussalam"],
    "Central & West Asia": ["Kazakhstan", "Kyrgyzstan", "Tajikistan",
                             "Turkmenistan", "Uzbekistan", "Azerbaijan", "Turkey"],
    "Europe & Americas": ["Albania", "Suriname", "Guyana"],
}

def get_country_region(country_name: str) -> str:
    for region, countries in COUNTRY_REGIONS.items():
        if country_name in countries:
            return region
    return "Other"


def get_pillar_correlation_matrix(db_connection):
    """Returns a correlation matrix DataFrame of pillar scores across all countries."""
    query = """
    SELECT c.name, p.pillar_name, p.total_pillar_score
    FROM pillars p
    JOIN countries c ON p.country_id = c.id;
    """
    df = pd.read_sql_query(query, db_connection)
    df['pillar_name'] = df['pillar_name'].str.replace(r'^\w+\sPillar:\s', '', regex=True)
    pivot = df.pivot_table(index='name', columns='pillar_name', values='total_pillar_score')
    return pivot.corr().round(2)


def get_oic_aggregate_stats(db_connection):
    """Returns per-pillar OIC aggregate statistics (mean, median, Q1, Q3)."""
    query = """
    SELECT p.pillar_name, p.total_pillar_score
    FROM pillars p;
    """
    df = pd.read_sql_query(query, db_connection)
    df['pillar_name'] = df['pillar_name'].str.replace(r'^\w+\sPillar:\s', '', regex=True)
    stats = df.groupby('pillar_name')['total_pillar_score'].agg(
        Mean='mean', Median='median',
        Q1=lambda x: x.quantile(0.25),
        Q3=lambda x: x.quantile(0.75),
    ).round(1).reset_index()
    order = ["Institutions", "Infrastructure", "Workforce", "E-Government",
             "Innovation", "Future Technologies",
             "Market Development and Sophistication",
             "Financial Market Development", "Sustainable Development Goals"]
    stats['_ord'] = stats['pillar_name'].apply(
        lambda n: order.index(n) if n in order else 99)
    return stats.sort_values('_ord').drop(columns='_ord').reset_index(drop=True)


def get_country_strengths_weaknesses(country_name: str, db_connection, top_n: int = 5):
    """Returns top N (strengths) and bottom N (weaknesses) sub-pillar indicators."""
    query = """
    SELECT sp.name AS indicator, sp.score, p.pillar_name
    FROM sub_pillars sp
    JOIN pillars p ON sp.pillar_id = p.id
    JOIN countries c ON p.country_id = c.id
    WHERE c.name = ?
    ORDER BY sp.score DESC;
    """
    df = pd.read_sql_query(query, db_connection, params=(country_name,))
    df['pillar_name'] = df['pillar_name'].str.replace(r'^\w+\sPillar:\s', '', regex=True)
    strengths = df.head(top_n).reset_index(drop=True)
    weaknesses = df.tail(top_n).sort_values('score').reset_index(drop=True)
    return strengths, weaknesses


def get_peer_region_data(country_name: str, db_connection):
    """Returns a comparison of the country against its regional peers (pillar scores)."""
    region = get_country_region(country_name)
    peers = COUNTRY_REGIONS.get(region, [country_name])

    placeholders = ', '.join(['?'] * len(peers))
    query = f"""
    SELECT c.name, p.pillar_name, p.total_pillar_score
    FROM pillars p
    JOIN countries c ON p.country_id = c.id
    WHERE c.name IN ({placeholders});
    """
    df = pd.read_sql_query(query, db_connection, params=peers)
    df['pillar_name'] = df['pillar_name'].str.replace(r'^\w+\sPillar:\s', '', regex=True)
    df['group'] = df['name'].apply(lambda n: country_name if n == country_name else f"{region} Avg")

    # Build regional average rows
    avg_df = df[df['name'] != country_name].groupby('pillar_name')['total_pillar_score'].mean().reset_index()
    avg_df['name'] = f"{region} Average"
    avg_df['group'] = f"{region} Avg"
    avg_df.rename(columns={'total_pillar_score': 'total_pillar_score'}, inplace=True)

    country_df = df[df['name'] == country_name][['name', 'pillar_name', 'total_pillar_score', 'group']]
    combined = pd.concat([country_df, avg_df[['name', 'pillar_name', 'total_pillar_score', 'group']]], ignore_index=True)
    return combined, region


def create_multi_radar_chart(pillars_df: pd.DataFrame):
    """Creates a multi-country radar chart from a pillars comparison dataframe."""
    fig = go.Figure()
    colors = [
        "#636EFA", "#EF553B", "#00CC96", "#AB63FA",
        "#FFA15A", "#19D3F3", "#FF6692", "#B6E880",
    ]
    country_names = pillars_df['name'].unique()
    for i, country in enumerate(country_names):
        subset = pillars_df[pillars_df['name'] == country]
        fig.add_trace(go.Scatterpolar(
            r=subset['total_pillar_score'].tolist() + [subset['total_pillar_score'].iloc[0]],
            theta=subset['pillar_name'].tolist() + [subset['pillar_name'].iloc[0]],
            fill='toself',
            name=country,
            line_color=colors[i % len(colors)],
            opacity=0.7,
        ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        title=dict(text="Pillar Performance Radar — All Selected Countries", x=0.5),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3),
    )
    return fig


def get_regional_aggregation(db_connection):
    """Returns average ADEI score and per-pillar averages grouped by sub-region."""
    query = """
    SELECT c.name, c.adei_score, p.pillar_name, p.total_pillar_score
    FROM pillars p
    JOIN countries c ON p.country_id = c.id;
    """
    df = pd.read_sql_query(query, db_connection)
    df['region'] = df['name'].apply(get_country_region)
    df['pillar_name'] = df['pillar_name'].str.replace(r'^\w+\sPillar:\s', '', regex=True)

    # ADEI averages per region
    adei_df = df.drop_duplicates(subset=['name'])[['name', 'adei_score', 'region']]
    adei_avg = adei_df.groupby('region')['adei_score'].agg(
        avg_adei='mean', country_count='count').round(1).reset_index()

    # Pillar averages per region
    pillar_avg = df.groupby(['region', 'pillar_name'])['total_pillar_score'].mean().round(1).reset_index()

    return adei_avg, pillar_avg


def get_rankings_explorer_data(db_connection):
    """Returns a wide-format table: rows=countries, columns=ADEI + 9 pillar scores."""
    query = """
    SELECT c.name, c.adei_score, c.adei_rank, p.pillar_name, p.total_pillar_score
    FROM pillars p
    JOIN countries c ON p.country_id = c.id
    ORDER BY c.adei_rank;
    """
    df = pd.read_sql_query(query, db_connection)
    df['pillar_name'] = df['pillar_name'].str.replace(r'^\w+\sPillar:\s', '', regex=True)
    pivot = df.pivot_table(
        index=['name', 'adei_rank', 'adei_score'],
        columns='pillar_name',
        values='total_pillar_score',
    ).reset_index().sort_values('adei_rank')
    pivot.columns.name = None
    pivot = pivot.rename(columns={'name': 'Country', 'adei_rank': 'Rank', 'adei_score': 'ADEI Score'})
    # Reorder pillar columns
    pillar_order = ["Institutions", "Infrastructure", "Workforce", "E-Government",
                    "Innovation", "Future Technologies",
                    "Market Development and Sophistication",
                    "Financial Market Development", "Sustainable Development Goals"]
    base_cols = ['Country', 'Rank', 'ADEI Score']
    ordered_cols = base_cols + [c for c in pillar_order if c in pivot.columns]
    return pivot[ordered_cols]
