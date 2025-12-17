from src.llm import analyze_competitors


def run_llm_analysis(asin: str) -> str:
    return analyze_competitors(asin)