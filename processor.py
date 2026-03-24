import pandas as pd
import time
from extractor import BrandExtractor
from searcher import search_brand


def process_brands(brands: list, groq_api_key: str,
                   progress_callback=None, status_callback=None) -> pd.DataFrame:
    """
    Process a list of brand names and extract taxonomy data.

    Args:
        brands: List of brand name strings
        groq_api_key: Groq API key
        progress_callback: Optional function(current, total) for progress updates
        status_callback: Optional function(brand, status) for status updates

    Returns:
        DataFrame with all extracted data
    """
    extractor = BrandExtractor(groq_api_key)
    results = []
    total = len(brands)

    for i, brand in enumerate(brands):
        brand = brand.strip()
        if not brand:
            continue

        if status_callback:
            status_callback(brand, "searching")

        # Step 1: Web search
        search_context = search_brand(brand)

        if status_callback:
            status_callback(brand, "extracting")

        # Step 2: LLM extraction
        extracted = extractor.extract(brand, search_context)

        # Step 3: Confidence scoring
        if extracted["status"] == "success":
            confidence = extractor.get_confidence(brand, extracted, search_context)
            extracted["confidence_score"] = confidence.get("confidence_score", 3)
            extracted["confidence_reason"] = confidence.get("confidence_reason", "")
        else:
            extracted["confidence_score"] = 0
            extracted["confidence_reason"] = extracted.get("error", "Failed")

        results.append(extracted)

        if progress_callback:
            progress_callback(i + 1, total)

        # Rate limiting
        time.sleep(0.3)

    return build_dataframe(results)


def build_dataframe(results: list) -> pd.DataFrame:
    """Convert list of result dicts to clean DataFrame."""
    df = pd.DataFrame(results)

    # Reorder columns
    col_order = [
        "brand_name", "parent_company", "stock_ticker",
        "naics_code", "industry_description", "country_of_origin",
        "company_type", "brief_description",
        "confidence_score", "confidence_reason", "status"
    ]
    existing_cols = [c for c in col_order if c in df.columns]
    other_cols = [c for c in df.columns if c not in col_order]
    df = df[existing_cols + other_cols]

    return df


def get_summary_stats(df: pd.DataFrame) -> dict:
    """Get summary statistics of processing results."""
    total = len(df)
    successful = len(df[df["status"] == "success"]) if "status" in df.columns else total
    failed = total - successful

    filled_counts = {}
    for col in ["parent_company", "stock_ticker", "naics_code",
                "country_of_origin", "company_type"]:
        if col in df.columns:
            filled = df[col].notna().sum()
            filled_counts[col] = {
                "filled": int(filled),
                "pct": round(filled / total * 100, 1) if total > 0 else 0
            }

    avg_confidence = df["confidence_score"].mean() if "confidence_score" in df.columns else 0

    return {
        "total": total,
        "successful": successful,
        "failed": failed,
        "success_rate": round(successful / total * 100, 1) if total > 0 else 0,
        "avg_confidence": round(avg_confidence, 1),
        "field_fill_rates": filled_counts
    }


def load_brands_from_csv(file) -> list:
    """Load brand names from uploaded CSV file."""
    df = pd.read_csv(file)

    # Try to find brand column automatically
    brand_col = None
    for col in df.columns:
        if any(x in col.lower() for x in ['brand', 'company', 'name', 'firm']):
            brand_col = col
            break

    if brand_col is None:
        brand_col = df.columns[0]  # Use first column

    brands = df[brand_col].dropna().astype(str).tolist()
    return brands, brand_col