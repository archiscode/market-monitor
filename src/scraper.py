import time
from datetime import datetime, timezone
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup


BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"


def fetch_page(url: str) -> str:
    response = requests.get(
        url,
        timeout=15,
        headers={"User-Agent": "MarketMonitor/1.0"}
    )
    response.raise_for_status()
    return response.text


def parse_books(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    books = []

    for article in soup.select("article.product_pod"):
        title_element = article.select_one("h3 a")
        price_element = article.select_one(".price_color")
        rating_element = article.select_one(".star-rating")
        stock_element = article.select_one(".availability")

    rating = None
    if rating_element:
        rating_classes = rating_element.get("class", [])
        rating = next((cls for cls in rating_classes if cls != "star-rating"), None)

    price = None
    if price_element:
        price_text = price_element.text.strip()
        price = float(price_text.replace("£", "").replace("Â", ""))

    books.append({
        "title": title_element["title"] if title_element else None,
        "price": price,
        "rating": rating,
        "stock": stock_element.text.strip() if stock_element else None,
        "collected_at": datetime.now(timezone.utc).isoformat()
    })
    
    return books


def scrape_catalog(start_url: str = BASE_URL) -> list[dict]:
    url = start_url
    all_books = []

    while url:
        html = fetch_page(url)
        soup = BeautifulSoup(html, "html.parser")

        all_books.extend(parse_books(html))

        next_link = soup.select_one("li.next a")
        if next_link:
            url = urljoin(BASE_URL, next_link["href"])
        else:
            url = None
        if url:
            time.sleep(1)  # Be polite and avoid overwhelming the server

    return all_books