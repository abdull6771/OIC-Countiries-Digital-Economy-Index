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
