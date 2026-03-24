import json
import re
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate


# ── Extraction Prompt ─────────────────────────────────────────────────────────
EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a business intelligence analyst specialising in brand and company taxonomy.
Your job is to extract structured information about brands from web search results.

Always respond with ONLY a valid JSON object — no explanation, no markdown, no backticks.
If you are not sure about a value, use null.
For NAICS codes use the standard 6-digit US NAICS classification.

JSON format:
{{
  "parent_company": "string or null",
  "stock_ticker": "string or null (e.g. GOOGL, META) or null if private",
  "naics_code": "string or null (6-digit code)",
  "industry_description": "string or null",
  "country_of_origin": "string or null",
  "company_type": "Public or Private or null",
  "brief_description": "string (1-2 sentences about what this brand does)"
}}
"""),
    ("human", """Brand: {brand_name}

Web Search Context:
{search_context}

Extract the taxonomy information for this brand. Return ONLY the JSON object.""")
])


# ── Confidence Scoring Prompt ─────────────────────────────────────────────────
CONFIDENCE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a data quality analyst.
Rate the confidence of extracted brand taxonomy data on a scale of 1-5:
1 = Very uncertain, mostly guessed
2 = Low confidence, some information found
3 = Moderate confidence, most fields filled
4 = High confidence, most fields verified
5 = Very high confidence, all fields verified from reliable sources

Respond with ONLY a JSON object:
{{"confidence_score": number, "confidence_reason": "brief explanation"}}
"""),
    ("human", """Brand: {brand_name}
Extracted Data: {extracted_data}
Search Context: {search_context}

Rate the confidence of this extraction.""")
])


class BrandExtractor:
    def __init__(self, groq_api_key: str):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            groq_api_key=groq_api_key
        )
        self.extraction_chain = EXTRACTION_PROMPT | self.llm
        self.confidence_chain = CONFIDENCE_PROMPT | self.llm

    def extract(self, brand_name: str, search_context: str) -> dict:
        """Extract taxonomy data for a single brand."""
        try:
            response = self.extraction_chain.invoke({
                "brand_name": brand_name,
                "search_context": search_context
            })

            raw = response.content.strip()

            # Clean markdown if present
            raw = re.sub(r'```json\s*', '', raw)
            raw = re.sub(r'```\s*', '', raw)
            raw = raw.strip()

            data = json.loads(raw)

            # Ensure all expected fields exist
            expected_fields = [
                "parent_company", "stock_ticker", "naics_code",
                "industry_description", "country_of_origin",
                "company_type", "brief_description"
            ]
            for field in expected_fields:
                if field not in data:
                    data[field] = None

            data["brand_name"] = brand_name
            data["status"] = "success"
            return data

        except json.JSONDecodeError:
            return self._fallback(brand_name, "JSON parsing failed")
        except Exception as e:
            return self._fallback(brand_name, str(e))

    def get_confidence(self, brand_name: str, extracted_data: dict,
                       search_context: str) -> dict:
        """Get confidence score for extracted data."""
        try:
            response = self.confidence_chain.invoke({
                "brand_name": brand_name,
                "extracted_data": json.dumps(extracted_data),
                "search_context": search_context[:500]
            })

            raw = response.content.strip()
            raw = re.sub(r'```json\s*', '', raw)
            raw = re.sub(r'```\s*', '', raw).strip()

            return json.loads(raw)

        except Exception:
            return {"confidence_score": 3, "confidence_reason": "Auto-scored"}

    def _fallback(self, brand_name: str, error: str) -> dict:
        """Return empty result on failure."""
        return {
            "brand_name": brand_name,
            "parent_company": None,
            "stock_ticker": None,
            "naics_code": None,
            "industry_description": None,
            "country_of_origin": None,
            "company_type": None,
            "brief_description": None,
            "status": "failed",
            "error": error
        }