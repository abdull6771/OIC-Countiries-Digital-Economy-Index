import streamlit as st
from pathlib import Path
import sqlite3
import pandas as pd
import plotly.express as px

# LangChain imports for the chatbot
from langchain.sql_database import SQLDatabase

# --- Import your modularized functions ---
from agent_logic import get_llm, get_sql_agent
from profile_generator import (
    get_country_list, 
    get_country_profile_data, 
    create_radar_chart,
    get_comparison_data,
    get_leaderboard_data,
    get_average_pillar_scores,
    get_map_data
)
st.set_page_config(
    page_title="OIC Digital Economy Dashboard",
    page_icon="📈",
    layout="wide",
 )

st.title("📈 Organization of Islamic Cooperation (OIC) Digital Economy Index")

st.markdown("""
Welcome to the interactive dashboard for the **Digital Economy Index of 57 OIC Countries**. This tool is designed to provide deep insights into the digital transformation landscape across the Islamic world.

Use the tabs below to explore the data:
- **🌍 Global Overview:** Get a high-level view of the entire dataset with leaderboards, a world map, and aggregate statistics.
- **💬 Chatbot Q&A:** Ask complex questions in plain English. An AI agent will query the database to find your answer.
- **📄 Country Profiles:** Select a country to view a detailed performance report, complete with scores, ranks, and visualizations.
- **🆚 Compare Countries:** Select two or more countries to see a side-by-side comparison of their scores.
""")
st.divider()

# --- Database Connection & Initialization ---
DB_PATH = Path(__file__).resolve().parent / "data" / "processed" / "digital_economy.db"

@st.cache_resource
def get_db_engine():
    """Initializes and caches a LangChain SQLDatabase engine for the agent."""
    if not DB_PATH.exists():
        st.error(f"Database not found at {DB_PATH}. Please run the data loading script first.")
        st.stop()
    return SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")

@st.cache_resource
def get_raw_db_connection():
    """Creates and caches a raw sqlite3 connection for pandas queries."""
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)

# Initialize all necessary components (cached for performance)
db_engine = get_db_engine()
raw_conn = get_raw_db_connection()
llm = get_llm()
agent = get_sql_agent(llm, db_engine)

# --- Create Tabs for Different App Sections ---
tab1, tab2, tab3, tab4 = st.tabs(["🌍 Global Overview", "📄 Country Profiles", "🆚 Compare Countries", "💬 Chatbot Q&A"])

# --- Tab 1: Global Overview ---
with tab1:
    st.header("Global Overview of the OIC Digital Economy Landscape")

    # Aggregate Pillar Statistics
    st.subheader("Average Performance Across All Pillars")
    avg_pillar_scores = get_average_pillar_scores(raw_conn)
    
    cols = st.columns(len(avg_pillar_scores))
    for i, row in avg_pillar_scores.iterrows():
        with cols[i]:
            st.metric(label=row['pillar_name'], value=f"{row['average_score']:.1f}")
    
    st.divider()

    # Choropleth Map
    st.subheader("Geographic Distribution of ADEI Scores")
    map_data = get_map_data(raw_conn)
    fig = px.choropleth(
        map_data,
        locations="iso_alpha",
        color="adei_score",
        hover_name="name",
        color_continuous_scale=px.colors.sequential.Plasma,
        title="ADEI Scores Across OIC Countries"
    )
    fig.update_layout(margin={"r":0,"t":30,"l":0,"b":0})
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Leaderboards
    st.subheader("Country Rankings")
    top_10, bottom_10 = get_leaderboard_data(raw_conn)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Top 10 Countries by ADEI Rank")
        st.dataframe(top_10.set_index("adei_rank"), use_container_width=True)
    with col2:
        st.markdown("##### Bottom 10 Countries by ADEI Rank")
        st.dataframe(bottom_10.set_index("adei_rank"), use_container_width=True)

# --- Tab 2: Country Profiles ---
with tab2:
    st.header("Generate a Profile for a Specific Country")
    
    country_list = get_country_list(raw_conn)
    
    selected_country = st.selectbox(
        "Select a country to view its profile:",
        options=country_list,
        index=country_list.index("United Arab Emirates") if "United Arab Emirates" in country_list else 0
    )

    if selected_country:
        profile_data = get_country_profile_data(selected_country, raw_conn)
        main_stats, pillars_df, sub_pillars_df = profile_data["main_stats"], profile_data["pillars_df"], profile_data["sub_pillars_df"]

        st.markdown(f"## Profile for: **{selected_country}**")
        
        col1, col2 = st.columns(2)
        col1.metric("Overall ADEI Score", int(main_stats['adei_score'].iloc[0]))
        col2.metric("Overall ADEI Rank", f"#{int(main_stats['adei_rank'].iloc[0])}")
        
        st.divider()
        
        st.subheader("Pillar Performance Analysis")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Performance Radar")
            radar_chart = create_radar_chart(pillars_df)
            st.plotly_chart(radar_chart, use_container_width=True)
        with col2:
            st.markdown("##### Pillar Scores (Bar Chart)")
            pillars_df_sorted = pillars_df.sort_values(by="total_pillar_score", ascending=False)
            st.bar_chart(pillars_df_sorted, x="pillar_name", y="total_pillar_score", color="#ffaa00")

        st.divider()
        
        st.subheader("Detailed Scores")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Pillar Scores (Table)")
            st.dataframe(pillars_df.style.format({'total_pillar_score': '{:.2f}'}), use_container_width=True, hide_index=True)
        with col2:
            st.markdown("##### Detailed Indicator Scores")
            st.dataframe(sub_pillars_df.style.format({'score': '{:.2f}'}), use_container_width=True, hide_index=True, height=400)

# --- Tab 3: Compare Countries ---
with tab3:
    st.header("Compare Countries Side-by-Side")
    
    country_list_for_compare = get_country_list(raw_conn)
    
    selected_countries = st.multiselect(
        "Select two or more countries to compare:",
        options=country_list_for_compare,
        default=["United Arab Emirates", "Saudi Arabia", "Malaysia", "Turkey"]
    )

    if len(selected_countries) >= 2:
        main_stats_df, pillars_df = get_comparison_data(selected_countries, raw_conn)

        st.subheader("Overall Score & Rank Comparison")
        st.dataframe(main_stats_df.set_index("name"), use_container_width=True)

        st.divider()

        st.subheader("Pillar Score Comparison (Grouped Bar Chart)")
        pivot_df = pillars_df.pivot_table(index='pillar_name', columns='name', values='total_pillar_score')
        st.bar_chart(pivot_df, height=500)

        st.markdown("##### Raw Pillar Data Table")
        st.dataframe(pivot_df.style.format("{:.2f}"), use_container_width=True)

    else:
        st.warning("Please select at least two countries to start the comparison.")

# --- Tab 4: Chatbot Q&A ---
with tab4:
    st.header("Ask Questions to the Digital Economy Database")

    if "qa_messages" not in st.session_state:
        st.session_state.qa_messages = []

    for message in st.session_state.qa_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("e.g., What is the 'Rule of Law' score for Saudi Arabia?"):
        st.chat_message("user").markdown(prompt)
        st.session_state.qa_messages.append({"role": "user", "content": prompt})

        with st.spinner("Thinking..."):
            try:
                response = agent.invoke({"input": prompt})
                response_content = response["output"]
            except Exception as e:
                response_content = f"Sorry, I encountered an error: {e}"

        with st.chat_message("assistant"):
            st.markdown(response_content)
        st.session_state.qa_messages.append({"role": "assistant", "content": response_content})
