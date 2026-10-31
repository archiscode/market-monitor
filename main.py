from src.scraper import fetch_page, parse_product


def main():
    url = "https://books.toscrape.com/"

    try:
        html = fetch_page(url)
        product = parse_product(html)

        print(product)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
