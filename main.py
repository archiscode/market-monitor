import json
from src.scraper import scrape_catalog


def main():
    books = scrape_catalog()

    print(f"Scraped {len(books)} books.")

    with open("books.json", "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=2)
    

if __name__ == "__main__":
    main()
