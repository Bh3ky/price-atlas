from src.services import scrape_and_store_product, fetch_and_store_competitors


def scrape_product(asin: str, geo: str, domain: str):
    return scrape_and_store_product(asin, geo, domain)


def refresh_competitors(asin: str, geo: str, domain: str):
    return fetch_and_store_competitors(asin, domain, geo)