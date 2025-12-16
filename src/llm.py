import os
from dotenv import load_dotenv
from src.db import Database
from typing import List, Optional
from pydantic import BaseModel, Field

load_dotenv()


class CompetitorInsights(BaseModel):
    asin: str
    title: Optional[str]
    price: Optional[float]
    currency: Optional[str]
    rating: Optional[float]
    key_points: List[str] = Field(default_factory=list)


class AnalysisOutput(BaseModel):
    summary: str
    positioning: str
    top_competitors: List[CompetitorInsights]
    recommendations: List[str]


def format_competitors(db, parent_asin):
    comps = db.search_products({"parent_asin": parent_asin})
    return [
        {
            "asin": c["asin"],
            "title": c["title"],
            "price": c["price"],
            "currency": c.get("currency"),
            "rating": c["rating"],
            "amazon_domain": c.get("amazon_domain")
        }
        for c in comps
    ]


def analyze_competitors(asin):
    from langchain_groq import ChatGroq
    from langchain_core.prompts import PromptTemplate
    from langchain_core.output_parsers import PydanticOutputParser

    db = Database()
    product = db.get_product(asin)
    competitors = format_competitors(db, asin)

    parser = PydanticOutputParser(pydantic_object=AnalysisOutput)

    template = (
        "You are a market analyst. Given a product and its competitor list, "
        "write a concise analysis. Pay attention to currency and pricing context.\n\n"
        "Product Title: {product_title}\n"
        "Brand: {brand}\n"
        "Price: {currency} {price}\n"
        "Rating: {rating}\n"
        "Categories: {categories}\n"
        "Amazon Domain: {amazon_domain}\n\n"
        "Competitors (JSON): {competitors}\n\n"
        "IMPORTANT: All prices should be displayed with their correct currency symbol. "
        "When comparing prices, ensure you're using the same currency context.\n\n"
        "{format_instructions}"
    )

    prompt = PromptTemplate(
        template=template,
        input_variables=[
            "product_title",
            "brand",
            "price",
            "currency",
            "rating",
            "categories",
            "amazon_domain",
            "competitors",
        ],
        partial_variables={
            "format_instructions": parser.get_format_instructions()
        }
    )

    if not os.getenv("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY not found in .env. Please set your API key.")

    llm = ChatGroq(
        model="llama3-8b-8192",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0
    )

    chain = prompt | llm | parser

    result = chain.invoke(
        {
            "product_title": product["title"] if product else asin,
            "brand": product.get("brand") if product else None,
            "price": product.get("price") if product else None,
            "currency": product.get("currency") if product else "",
            "rating": product.get("rating") if product else None,
            "categories": product.get("categories") if product else None,
            "amazon_domain": product.get("amazon_domain") if product else "com",
            "competitors": competitors,
        }
    )

    lines = [
        "Summary:\n" + result.summary,
        "\nPositioning:\n" + result.positioning,
        "\nCompetitors:"
    ]

    for c in result.top_competitors:
        pts = "; ".join(c.key_points) if c.key_points else ""
        currency = c.currency or ""
        price_str = f"{currency} {c.price}" if c.price else "N/A"
        lines.append(f"- {c.asin} | {c.title} | {price_str} | {c.rating} | {pts}")

    if result.recommendations:
        lines.append("\nRecommendations:")
        for r in result.recommendations:
            lines.append(f"- {r}")

    return "\n".join(lines)
