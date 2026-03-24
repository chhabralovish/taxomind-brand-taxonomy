import streamlit as st
import pandas as pd
import os
import io
from dotenv import load_dotenv
from processor import process_brands, load_brands_from_csv, get_summary_stats
import plotly.express as px

load_dotenv()

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TaxoMind — Brand Taxonomy Automation",
    page_icon="🏷️",
    layout="wide"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid #4CAF50;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .metric-value { font-size: 2.5em; font-weight: bold; color: #4CAF50; }
    .metric-label { font-size: 0.85em; color: #aaaaaa; margin-top: 4px; }
    .highlight { color: #4CAF50; font-weight: bold; }
    .status-success { color: #4CAF50; }
    .status-failed  { color: #FF6B6B; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center; padding:20px 0'>
    <h1 style='font-size:3em; margin:0'>🏷️ TaxoMind</h1>
    <p style='color:#aaaaaa; font-size:1.1em'>
        LLM-Powered Brand Taxonomy Automation · Reduce Manual Research by 90%
    </p>
</div>
""", unsafe_allow_html=True)
st.divider()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")

    groq_api_key = st.text_input(
        "Groq API Key",
        type="password",
        placeholder="Enter your Groq API key",
        value=os.getenv("GROQ_API_KEY", "")
    )

    st.divider()
    st.markdown("**📊 What TaxoMind Extracts:**")
    st.markdown("- 🏢 Parent Company")
    st.markdown("- 📈 Stock Ticker")
    st.markdown("- 🔢 NAICS Code (6-digit)")
    st.markdown("- 🏭 Industry Description")
    st.markdown("- 🌍 Country of Origin")
    st.markdown("- 📋 Company Type (Public/Private)")
    st.markdown("- 📝 Brief Description")
    st.markdown("- ⭐ Confidence Score (1-5)")

    st.divider()
    st.markdown("Built by [Lovish Chhabra](https://www.linkedin.com/in/lovish-chhabra/)")

# ── Main Area ─────────────────────────────────────────────────────────────────
if not groq_api_key:
    st.info("👈 Enter your Groq API key in the sidebar to get started.")
    st.stop()

# ── Upload Section ────────────────────────────────────────────────────────────
st.subheader("📂 Upload Brand List")

col1, col2 = st.columns([2, 1])
with col1:
    uploaded_file = st.file_uploader(
        "Upload CSV file with brand names",
        type=["csv"],
        help="CSV should have a column named 'brand_name' or similar"
    )

with col2:
    use_sample = st.checkbox("Use sample dataset", value=False)
    if use_sample:
        st.caption("25 popular brands included")

# Load brands
brands = []
if uploaded_file:
    try:
        brands, brand_col = load_brands_from_csv(uploaded_file)
        st.success(f"✅ Loaded **{len(brands)}** brands from column `{brand_col}`")
        with st.expander("Preview brands"):
            st.write(brands[:10])
            if len(brands) > 10:
                st.caption(f"... and {len(brands) - 10} more")
    except Exception as e:
        st.error(f"Error loading CSV: {str(e)}")

elif use_sample:
    try:
        brands, _ = load_brands_from_csv("sample_data/brands.csv")
        st.success(f"✅ Loaded **{len(brands)}** sample brands")
    except Exception as e:
        st.error(f"Sample file not found: {str(e)}")

# ── Processing ────────────────────────────────────────────────────────────────
if brands:
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"Ready to process **{len(brands)}** brands. "
                f"Estimated time: ~{len(brands) * 8} seconds")
    with col2:
        start_btn = st.button(
            "🚀 Start Extraction",
            type="primary",
            use_container_width=True
        )

    if start_btn or "results_df" in st.session_state:

        if start_btn:
            # ── Run Processing ────────────────────────────────────────────────
            st.subheader("⚙️ Processing...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_placeholder = st.empty()

            live_results = []

            def update_progress(current, total):
                progress_bar.progress(current / total)

            def update_status(brand, status):
                icons = {"searching": "🔍", "extracting": "🤖"}
                icon = icons.get(status, "⚙️")
                status_text.markdown(
                    f"{icon} **{status.capitalize()}:** `{brand}`"
                )

            with st.spinner(""):
                df = process_brands(
                    brands=brands,
                    groq_api_key=groq_api_key,
                    progress_callback=update_progress,
                    status_callback=update_status
                )

            st.session_state["results_df"] = df
            status_text.markdown("✅ **Processing complete!**")
            progress_bar.progress(1.0)

        # ── Results ───────────────────────────────────────────────────────────
        df = st.session_state["results_df"]
        stats = get_summary_stats(df)

        st.divider()
        st.subheader("📊 Results Summary")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-value'>{stats['total']}</div>
                <div class='metric-label'>Total Brands</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-value'>{stats['success_rate']}%</div>
                <div class='metric-label'>Success Rate</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-value'>{stats['avg_confidence']}/5</div>
                <div class='metric-label'>Avg Confidence</div>
            </div>""", unsafe_allow_html=True)
        with c4:
            time_saved = stats['total'] * 15
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-value'>{time_saved}m</div>
                <div class='metric-label'>Minutes Saved</div>
            </div>""", unsafe_allow_html=True)

        # Field fill rates
        st.divider()
        st.subheader("📈 Field Fill Rates")
        fill_data = []
        for field, info in stats["field_fill_rates"].items():
            fill_data.append({
                "Field": field.replace("_", " ").title(),
                "Fill Rate (%)": info["pct"],
                "Filled": info["filled"]
            })

        if fill_data:
            fill_df = pd.DataFrame(fill_data)
            fig = px.bar(
                fill_df, x="Field", y="Fill Rate (%)",
                color="Fill Rate (%)",
                color_continuous_scale="Greens",
                template="plotly_dark",
                title="Percentage of Brands with Each Field Filled"
            )
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        # ── Results Table ─────────────────────────────────────────────────────
        st.divider()
        st.subheader("🗂️ Extracted Data")

        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            show_failed = st.checkbox("Show failed extractions", value=False)
        with col2:
            min_confidence = st.slider("Min confidence score", 1, 5, 1)

        display_df = df.copy()
        if not show_failed and "status" in display_df.columns:
            display_df = display_df[display_df["status"] == "success"]
        if "confidence_score" in display_df.columns:
            display_df = display_df[display_df["confidence_score"] >= min_confidence]

        # Colour code confidence
        def color_confidence(val):
            if val >= 4:
                return "background-color: #1a3a1a; color: #4CAF50"
            elif val >= 3:
                return "background-color: #3a3a1a; color: #FFC107"
            else:
                return "background-color: #3a1a1a; color: #FF6B6B"

        display_cols = [c for c in display_df.columns
                        if c not in ["status", "error", "confidence_reason"]]

        st.dataframe(
            display_df[display_cols],
            use_container_width=True,
            height=400
        )

        st.caption(f"Showing {len(display_df)} of {len(df)} brands")

        # ── Industry Distribution ─────────────────────────────────────────────
        if "industry_description" in df.columns:
            st.divider()
            st.subheader("🏭 Industry Distribution")
            industry_counts = df["industry_description"].value_counts().head(10)
            if not industry_counts.empty:
                fig2 = px.pie(
                    values=industry_counts.values,
                    names=industry_counts.index,
                    title="Top Industries in Dataset",
                    template="plotly_dark",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig2.update_layout(height=400)
                st.plotly_chart(fig2, use_container_width=True)

        # ── Country Distribution ──────────────────────────────────────────────
        if "country_of_origin" in df.columns:
            st.divider()
            st.subheader("🌍 Country Distribution")
            country_counts = df["country_of_origin"].value_counts().head(10)
            if not country_counts.empty:
                fig3 = px.bar(
                    x=country_counts.index,
                    y=country_counts.values,
                    title="Brands by Country of Origin",
                    template="plotly_dark",
                    color=country_counts.values,
                    color_continuous_scale="Blues"
                )
                fig3.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig3, use_container_width=True)

        # ── Export ────────────────────────────────────────────────────────────
        st.divider()
        st.subheader("📥 Export Results")

        col1, col2 = st.columns(2)

        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name="taxomind_results.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col2:
            try:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name="Brand Taxonomy")
                    # Summary sheet
                    summary_data = {
                        "Metric": ["Total Brands", "Success Rate", "Avg Confidence", "Minutes Saved"],
                        "Value": [stats['total'], f"{stats['success_rate']}%",
                                  f"{stats['avg_confidence']}/5", f"{stats['total']*15} min"]
                    }
                    pd.DataFrame(summary_data).to_excel(
                        writer, index=False, sheet_name="Summary"
                    )
                output.seek(0)

                st.download_button(
                    label="⬇️ Download Excel",
                    data=output,
                    file_name="taxomind_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception:
                st.info("Install openpyxl for Excel export: pip install openpyxl")

        # Clear results button
        if st.button("🗑️ Clear Results & Start Over"):
            del st.session_state["results_df"]
            st.rerun()