import requests
from bs4 import BeautifulSoup


def fetch_page(url: str) -> str:
    response = requests.get(
        url,
        timeout=15,
        headers={"User-Agent": "MarketMonitor/1.0"}
    )
    response.raise_for_status()

    return response.text


def parse_product(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title_element = soup.select_one("h3 a")
    price_element = soup.select_one("p.price_color")
    rating_element = soup.select_one("p.star-rating")
    stock_element = soup.select_one("p.availability")

    title = (
        title_element.get("title") or title_element.get_text(strip=True)
        if title_element else None
    )

    price = None
    if price_element:
        price_text = price_element.get_text(strip=True)
        price = float(price_text.replace("£", "").replace("Â", ""))

    rating = None
    if rating_element:
        rating_classes = rating_element.get("class", [])
        rating_mapping = {
            "One": 1,
            "Two": 2,
            "Three": 3,
            "Four": 4,
            "Five": 5
        }
        for cls in rating_classes:
            if cls != "star-rating":
                rating = rating_mapping.get(cls)
                break

    stock = None
    if stock_element:
        stock = stock_element.get_text(strip=True) if stock_element else None

    return {
        "title": title,
        "price": price,
        "rating": rating,
        "stock": stock
    }