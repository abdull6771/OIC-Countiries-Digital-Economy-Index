import streamlit as st
from pathlib import Path
import sqlite3
import pandas as pd
import plotly.express as px

# LangChain imports for the chatbot
from langchain_community.utilities import SQLDatabase

# --- Import your modularized functions ---
from agent_logic import get_llm, get_sql_agent
from profile_generator import (
    get_country_list,
    get_country_profile_data,
    create_radar_chart,
    create_multi_radar_chart,
    get_comparison_data,
    get_leaderboard_data,
    get_average_pillar_scores,
    get_map_data,
    get_pillar_rankings,
    get_all_pillar_names,
    get_geo_pillar_data,
    get_pillar_correlation_matrix,
    get_oic_aggregate_stats,
    get_country_strengths_weaknesses,
    get_peer_region_data,
    get_regional_aggregation,
    get_rankings_explorer_data,
    get_country_region,
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
- **🌍 Global Overview:** Leaderboards, world map, OIC aggregate scorecard, and pillar correlation heatmap.
- **📄 Country Profiles:** Detailed per-country report with strengths & weaknesses and regional peer comparison.
- **🆚 Compare Countries:** Side-by-side bar charts and radar overlay for multiple countries.
- **🏛️ Pillar Analysis:** Drill into any of the 9 pillars — rankings, bar chart, and sub-indicator heatmap.
- **🗺️ Geographic Analysis:** Choropleth maps, score distributions, and regional aggregation.
- **📈 Trends & Progress:** 2025 baseline snapshot — box plots, country ladder, and downloadable stats.
- **🏆 Rankings Explorer:** Sortable full table of all 57 countries across all 9 pillar scores with CSV export.
- **💬 Chatbot Q&A:** Ask complex questions in plain English backed by the live database.
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🌍 Global Overview",
    "📄 Country Profiles",
    "🆚 Compare Countries",
    "🏛️ Pillar Analysis",
    "🗺️ Geographic Analysis",
    "📈 Trends & Progress",
    "🏆 Rankings Explorer",
    "💬 Chatbot Q&A",
])

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
    st.plotly_chart(fig, width="stretch")

    st.divider()

    # Leaderboards
    st.subheader("Country Rankings")
    top_10, bottom_10 = get_leaderboard_data(raw_conn)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Top 10 Countries by ADEI Rank")
        st.dataframe(top_10.set_index("adei_rank"), width="stretch")
    with col2:
        st.markdown("##### Bottom 10 Countries by ADEI Rank")
        st.dataframe(bottom_10.set_index("adei_rank"), width="stretch")

    st.divider()

    # OIC Aggregate Scorecard
    st.subheader("OIC Aggregate Scorecard — Pillar Statistics")
    st.caption("Mean, Median, Q1 and Q3 calculated across all 57 OIC member states (2025 baseline).")
    oic_stats = get_oic_aggregate_stats(raw_conn)
    st.dataframe(
        oic_stats.rename(columns={"pillar_name": "Pillar"})
        .set_index("Pillar")
        .style.format("{:.1f}"),
        width="stretch",
    )

    st.divider()

    # Pillar Correlation Heatmap
    st.subheader("Pillar Correlation Heatmap")
    st.caption("Pearson correlation of pillar scores across all 57 countries. Values close to 1 indicate pillars that tend to move together.")
    corr_matrix = get_pillar_correlation_matrix(raw_conn)
    fig_corr = px.imshow(
        corr_matrix,
        color_continuous_scale=px.colors.diverging.RdYlGn,
        zmin=-1, zmax=1,
        text_auto=".2f",
        aspect="auto",
    )
    fig_corr.update_layout(margin={"t": 10, "b": 10})
    st.plotly_chart(fig_corr, width="stretch")

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
            st.plotly_chart(radar_chart, width="stretch")
        with col2:
            st.markdown("##### Pillar Scores (Bar Chart)")
            pillars_df_sorted = pillars_df.sort_values(by="total_pillar_score", ascending=False)
            st.bar_chart(pillars_df_sorted, x="pillar_name", y="total_pillar_score", color="#ffaa00")

        st.divider()
        
        st.subheader("Detailed Scores")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Pillar Scores (Table)")
            st.dataframe(pillars_df.style.format({'total_pillar_score': '{:.2f}'}), width="stretch", hide_index=True)
        with col2:
            st.markdown("##### Detailed Indicator Scores")
            st.dataframe(sub_pillars_df.style.format({'score': '{:.2f}'}), width="stretch", hide_index=True, height=400)

        st.divider()

        # Strengths & Weaknesses
        st.subheader("Strengths & Weaknesses")
        strengths, weaknesses = get_country_strengths_weaknesses(selected_country, raw_conn)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### 🟢 Top 5 Indicators")
            for _, r in strengths.iterrows():
                st.metric(
                    label=f"{r['indicator']} ({r['pillar_name']})",
                    value=f"{r['score']:.1f}",
                )
        with col2:
            st.markdown("##### 🔴 Bottom 5 Indicators")
            for _, r in weaknesses.iterrows():
                st.metric(
                    label=f"{r['indicator']} ({r['pillar_name']})",
                    value=f"{r['score']:.1f}",
                )

        st.divider()

        # Peer Group Comparison
        peer_df, peer_region = get_peer_region_data(selected_country, raw_conn)
        st.subheader(f"Peer Group Comparison — {peer_region} Region")
        if len(peer_df['name'].unique()) > 1:
            fig_peer = px.bar(
                peer_df,
                x="pillar_name",
                y="total_pillar_score",
                color="group",
                barmode="group",
                labels={"pillar_name": "Pillar", "total_pillar_score": "Score", "group": ""},
                color_discrete_map={
                    selected_country: "#636EFA",
                    f"{peer_region} Avg": "#FFA15A",
                },
            )
            fig_peer.update_layout(xaxis_tickangle=-30, margin={"t": 10, "b": 100})
            st.plotly_chart(fig_peer, width="stretch")
        else:
            st.info("No regional peers found in the dataset for this country.")

# --- Tab 3: Compare Countries ---
with tab3:
    st.header("Compare Countries Side-by-Side")
    
    country_list_for_compare = get_country_list(raw_conn)
    
    _preferred_defaults = ["United Arab Emirates", "Saudi Arabia", "Malaysia", "Turkey"]
    _safe_defaults = [c for c in _preferred_defaults if c in country_list_for_compare]
    selected_countries = st.multiselect(
        "Select two or more countries to compare:",
        options=country_list_for_compare,
        default=_safe_defaults,
    )

    if len(selected_countries) >= 2:
        main_stats_df, pillars_df = get_comparison_data(selected_countries, raw_conn)

        st.subheader("Overall Score & Rank Comparison")
        st.dataframe(main_stats_df.set_index("name"), width="stretch")

        st.divider()

        st.subheader("Pillar Score Comparison (Grouped Bar Chart)")
        pivot_df = pillars_df.pivot_table(index='pillar_name', columns='name', values='total_pillar_score')
        st.bar_chart(pivot_df, height=500)

        st.divider()

        st.subheader("Pillar Performance Radar — Overlay")
        multi_radar = create_multi_radar_chart(pillars_df)
        st.plotly_chart(multi_radar, width="stretch")

        st.divider()

        st.markdown("##### Raw Pillar Data Table")
        st.dataframe(pivot_df.style.format("{:.2f}"), width="stretch")

    else:
        st.warning("Please select at least two countries to start the comparison.")

# --- Tab 4: Pillar Analysis ---
with tab4:
    st.header("Pillar-by-Pillar Analysis Across All OIC Countries")

    all_pillar_names = get_all_pillar_names(raw_conn)
    pillar_labels = [n.split(": ", 1)[-1] if ": " in n else n for n in all_pillar_names]
    pillar_label_to_full = dict(zip(pillar_labels, all_pillar_names))

    selected_pillar_label = st.selectbox(
        "Select a pillar to analyse:",
        options=pillar_labels,
    )
    selected_pillar_full = pillar_label_to_full[selected_pillar_label]

    pillar_countries_df, pillar_sub_df = get_pillar_rankings(selected_pillar_full, raw_conn)

    st.subheader(f"Country Rankings — {selected_pillar_label}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Top Scorer", pillar_countries_df.iloc[0]['name'],
                f"{pillar_countries_df.iloc[0]['total_pillar_score']:.1f}")
    col2.metric("Median Score",
                f"{pillar_countries_df['total_pillar_score'].median():.1f}")
    col3.metric("Lowest Score", pillar_countries_df.iloc[-1]['name'],
                f"{pillar_countries_df.iloc[-1]['total_pillar_score']:.1f}")

    st.divider()

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("##### Score Distribution (All Countries)")
        fig_bar = px.bar(
            pillar_countries_df,
            x="name",
            y="total_pillar_score",
            color="total_pillar_score",
            color_continuous_scale=px.colors.sequential.Plasma,
            labels={"name": "Country", "total_pillar_score": "Score"},
        )
        fig_bar.update_layout(
            xaxis_tickangle=-45,
            coloraxis_showscale=False,
            margin={"t": 10, "b": 120},
        )
        st.plotly_chart(fig_bar, width="stretch")
    with col2:
        st.markdown("##### Full Country Ranking")
        st.dataframe(
            pillar_countries_df.set_index("pillar_rank")
            .rename(columns={"name": "Country", "total_pillar_score": "Score", "adei_rank": "ADEI Rank"})
            .style.format({"Score": "{:.2f}"}),
            width="stretch",
            height=420,
        )

    st.divider()

    st.subheader(f"Sub-Indicator Heatmap — {selected_pillar_label}")
    if not pillar_sub_df.empty:
        heatmap_pivot = pillar_sub_df.pivot_table(
            index="indicator", columns="name", values="score"
        )
        # Sort columns by pillar score (best to worst)
        ordered_countries = pillar_countries_df["name"].tolist()
        heatmap_pivot = heatmap_pivot[[c for c in ordered_countries if c in heatmap_pivot.columns]]

        fig_heat = px.imshow(
            heatmap_pivot,
            color_continuous_scale=px.colors.diverging.RdYlGn,
            aspect="auto",
            labels={"color": "Score"},
            zmin=0,
            zmax=100,
        )
        fig_heat.update_layout(margin={"t": 10, "b": 10})
        st.plotly_chart(fig_heat, width="stretch")


# --- Tab 5: Geographic Analysis ---
with tab5:
    st.header("Geographic Analysis of the OIC Digital Economy")

    geo_pillar_names = get_all_pillar_names(raw_conn)
    geo_pillar_labels = [n.split(": ", 1)[-1] if ": " in n else n for n in geo_pillar_names]
    geo_label_to_full = dict(zip(geo_pillar_labels, geo_pillar_names))

    geo_options = ["Overall ADEI Score"] + geo_pillar_labels
    selected_geo_metric = st.selectbox(
        "Select metric to map:",
        options=geo_options,
        key="geo_metric",
    )

    if selected_geo_metric == "Overall ADEI Score":
        geo_df = get_geo_pillar_data(None, raw_conn)
        metric_label = "Overall ADEI Score"
    else:
        geo_df = get_geo_pillar_data(geo_label_to_full[selected_geo_metric], raw_conn)
        metric_label = selected_geo_metric

    st.divider()

    # --- Choropleth ---
    st.subheader(f"Choropleth Map — {metric_label}")
    fig_choro = px.choropleth(
        geo_df,
        locations="iso_alpha",
        color="score",
        hover_name="name",
        color_continuous_scale=px.colors.sequential.Plasma,
        labels={"score": metric_label},
    )
    fig_choro.update_layout(margin={"r": 0, "t": 10, "l": 0, "b": 0})
    st.plotly_chart(fig_choro, width="stretch")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        # --- Score distribution histogram ---
        st.subheader("Score Distribution")
        fig_hist = px.histogram(
            geo_df,
            x="score",
            nbins=15,
            labels={"score": metric_label, "count": "# Countries"},
            color_discrete_sequence=["#636EFA"],
        )
        fig_hist.update_layout(bargap=0.05, margin={"t": 10})
        st.plotly_chart(fig_hist, width="stretch")

    with col2:
        # --- Top / Bottom bar ---
        st.subheader("Top 10 vs Bottom 10")
        geo_sorted = geo_df.sort_values("score", ascending=False)
        top10_geo = geo_sorted.head(10).copy()
        top10_geo["group"] = "Top 10"
        bot10_geo = geo_sorted.tail(10).copy()
        bot10_geo["group"] = "Bottom 10"
        tb_df = pd.concat([top10_geo, bot10_geo])
        fig_tb = px.bar(
            tb_df,
            x="name",
            y="score",
            color="group",
            color_discrete_map={"Top 10": "#00CC96", "Bottom 10": "#EF553B"},
            labels={"name": "Country", "score": metric_label, "group": ""},
        )
        fig_tb.update_layout(xaxis_tickangle=-45, margin={"t": 10, "b": 120})
        st.plotly_chart(fig_tb, width="stretch")

    st.divider()

    # --- Scatter: selected metric vs Overall ADEI ---
    if selected_geo_metric != "Overall ADEI Score":
        st.subheader(f"Pillar Score vs Overall ADEI — {metric_label}")
        overall_df = get_geo_pillar_data(None, raw_conn).rename(columns={"score": "adei_score_val"})
        scatter_df = geo_df.merge(overall_df[["name", "adei_score_val"]], on="name", how="inner")
        fig_scatter = px.scatter(
            scatter_df,
            x="score",
            y="adei_score_val",
            hover_name="name",
            labels={"score": metric_label, "adei_score_val": "Overall ADEI Score"},
            trendline="ols",
            color="score",
            color_continuous_scale=px.colors.sequential.Plasma,
        )
        fig_scatter.update_layout(coloraxis_showscale=False, margin={"t": 10})
        st.plotly_chart(fig_scatter, width="stretch")

    st.divider()

    # Regional Aggregation
    st.subheader("Regional Aggregation")
    adei_avg, pillar_avg = get_regional_aggregation(raw_conn)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Average ADEI Score by Region")
        fig_reg = px.bar(
            adei_avg.sort_values("avg_adei", ascending=True),
            x="avg_adei",
            y="region",
            orientation="h",
            color="avg_adei",
            color_continuous_scale=px.colors.sequential.Plasma,
            text="avg_adei",
            labels={"avg_adei": "Avg ADEI Score", "region": "Region", "country_count": "Countries"},
            hover_data=["country_count"],
        )
        fig_reg.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig_reg.update_layout(coloraxis_showscale=False, margin={"t": 10, "l": 10})
        st.plotly_chart(fig_reg, width="stretch")
    with col2:
        st.markdown("##### Regions by Country Count")
        fig_pie = px.pie(
            adei_avg,
            names="region",
            values="country_count",
            hole=0.4,
        )
        fig_pie.update_layout(margin={"t": 10})
        st.plotly_chart(fig_pie, width="stretch")

    st.markdown("##### Average Pillar Scores by Region (Heatmap)")
    reg_pivot = pillar_avg.pivot_table(index="region", columns="pillar_name", values="total_pillar_score")
    fig_reg_heat = px.imshow(
        reg_pivot,
        color_continuous_scale=px.colors.diverging.RdYlGn,
        aspect="auto",
        text_auto=".1f",
        zmin=0, zmax=100,
    )
    fig_reg_heat.update_layout(margin={"t": 10, "b": 10})
    st.plotly_chart(fig_reg_heat, width="stretch")


# --- Tab 6: Trends & Progress ---
with tab6:
    st.header("Trends & Progress — 2025 Baseline")
    st.info(
        "The current dataset covers a single reference year (2025). "
        "This tab presents a comprehensive baseline snapshot. As future-year data becomes available, "
        "time-series trend lines will be activated automatically."
    )

    t6_pillar_names = get_all_pillar_names(raw_conn)
    t6_pillar_labels = [n.split(": ", 1)[-1] if ": " in n else n for n in t6_pillar_names]
    t6_label_to_full = dict(zip(t6_pillar_labels, t6_pillar_names))

    st.subheader("Score Distribution per Pillar (Box Plot)")
    all_pillar_q = """
    SELECT c.name, c.adei_rank, p.pillar_name, p.total_pillar_score
    FROM pillars p JOIN countries c ON p.country_id = c.id;
    """
    all_pillar_df = pd.read_sql_query(all_pillar_q, raw_conn)
    all_pillar_df['pillar_name'] = all_pillar_df['pillar_name'].str.replace(
        r'^\w+\sPillar:\s', '', regex=True)
    fig_box = px.box(
        all_pillar_df,
        x="pillar_name",
        y="total_pillar_score",
        points="all",
        hover_name="name",
        labels={"pillar_name": "Pillar", "total_pillar_score": "Score"},
        color="pillar_name",
    )
    fig_box.update_layout(showlegend=False, xaxis_tickangle=-30, margin={"t": 10, "b": 120})
    st.plotly_chart(fig_box, width="stretch")

    st.divider()

    st.subheader("Country Score Ladder — Select a Pillar")
    t6_selected_label = st.selectbox(
        "Pillar for ladder view:",
        options=["Overall ADEI Score"] + t6_pillar_labels,
        key="t6_pillar",
    )
    if t6_selected_label == "Overall ADEI Score":
        ladder_q = "SELECT name, adei_score AS score, adei_rank AS rank FROM countries ORDER BY adei_rank;"
        ladder_df = pd.read_sql_query(ladder_q, raw_conn)
        ladder_label = "Overall ADEI Score"
    else:
        t6_full = t6_label_to_full[t6_selected_label]
        ladder_q = """
        SELECT c.name, p.total_pillar_score AS score,
               RANK() OVER (ORDER BY p.total_pillar_score DESC) AS rank
        FROM pillars p JOIN countries c ON p.country_id = c.id
        WHERE p.pillar_name = ?
        ORDER BY p.total_pillar_score DESC;
        """
        ladder_df = pd.read_sql_query(ladder_q, raw_conn, params=(t6_full,))
        ladder_label = t6_selected_label

    fig_ladder = px.bar(
        ladder_df,
        x="score",
        y="name",
        orientation="h",
        color="score",
        color_continuous_scale=px.colors.sequential.Plasma,
        text="score",
        labels={"score": ladder_label, "name": "Country"},
        height=max(500, len(ladder_df) * 22),
    )
    fig_ladder.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig_ladder.update_layout(
        yaxis=dict(autorange="reversed"),
        coloraxis_showscale=False,
        margin={"t": 10, "r": 80},
    )
    st.plotly_chart(fig_ladder, width="stretch")

    st.divider()

    st.subheader("OIC Statistical Summary — All Pillars")
    oic_stats_t6 = get_oic_aggregate_stats(raw_conn)
    st.dataframe(
        oic_stats_t6.rename(columns={"pillar_name": "Pillar"}).set_index("Pillar")
        .style.format("{:.1f}"),
        width="stretch",
    )
    st.download_button(
        "⬇️ Download Summary CSV",
        data=oic_stats_t6.to_csv(index=False),
        file_name="oic_pillar_stats_2025.csv",
        mime="text/csv",
    )


# --- Tab 7: Rankings Explorer ---
with tab7:
    st.header("Rankings Explorer — All 57 Countries × 9 Pillars")
    st.caption("Click any column header to sort. Use the search box to filter countries.")

    rankings_df = get_rankings_explorer_data(raw_conn)

    search_query = st.text_input("🔍 Search country:", placeholder="e.g. Malaysia")
    if search_query:
        rankings_df = rankings_df[
            rankings_df['Country'].str.contains(search_query, case=False, na=False)
        ]

    pillar_cols = [c for c in rankings_df.columns if c not in ['Country', 'Rank', 'ADEI Score']]

    st.dataframe(
        rankings_df.set_index("Rank")
        .style.format({c: "{:.1f}" for c in ["ADEI Score"] + pillar_cols}),
        width="stretch",
        height=700,
    )

    st.download_button(
        "⬇️ Download Full Rankings CSV",
        data=rankings_df.to_csv(index=False),
        file_name="oic_full_rankings_2025.csv",
        mime="text/csv",
    )


# --- Tab 8: Chatbot Q&A ---
with tab8:
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
