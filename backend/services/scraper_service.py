from config import get_settings

settings = get_settings()


class ScraperService:
    def __init__(self):
        self.api_key = settings.serpapi_key or None

    async def fetch_prices_api(self, clean_query: str) -> list[dict]:
        if not self.api_key:
            return []

        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_shopping",
            "q": clean_query,
            "google_domain": "google.co.in",
            "hl": "en",
            "gl": "in",
            "api_key": self.api_key,
        }

        results = []
        import httpx
        from urllib.parse import quote

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, timeout=15.0)
                if response.status_code != 200:
                    return []

                data = response.json()
                for item in data.get("shopping_results", []):
                    raw_price = item.get("price", "0")
                    clean_price = "".join(c for c in raw_price if c.isdigit() or c == ".")
                    price_float = float(clean_price) if clean_price else 0.0

                    merchant_name = item.get("source", "Online Retailer")
                    merchant_url = item.get("product_link") or item.get("link") or "#"

                    if "offers" in item and item["offers"]:
                        first_offer = item["offers"][0]
                        if first_offer.get("link"):
                            merchant_name = first_offer.get("store_name", merchant_name)
                            merchant_url = first_offer.get("link")

                    if price_float == 0.0 or merchant_url == "#":
                        continue

                    merchant_lower = merchant_name.lower()
                    title_text = item.get("title", clean_query)
                    encoded_title = quote(title_text)

                    deep_product_url = None
                    for store in item.get("online_stores", []):
                        if merchant_lower in store.get("name", "").lower() and store.get("link"):
                            deep_product_url = store.get("link")
                            break

                    if not deep_product_url:
                        for offer in item.get("offers", []):
                            if merchant_lower in offer.get("store_name", "").lower() and offer.get("link"):
                                deep_product_url = offer.get("link")
                                break

                    if deep_product_url and "google.com" not in deep_product_url:
                        merchant_url = deep_product_url
                    elif "amazon" in merchant_lower:
                        merchant_url = f"https://www.amazon.in/s?k={encoded_title}"
                    elif "flipkart" in merchant_lower:
                        merchant_url = f"https://www.flipkart.com/search?q={encoded_title}"

                    results.append({
                        "title": title_text,
                        "price": price_float,
                        "currency": "INR" if ("₹" in raw_price or "rs" in raw_price.lower()) else "USD",
                        "source_website": merchant_name,
                        "product_url": merchant_url,
                        "thumbnail_url": item.get("thumbnail"),
                    })

                    if len(results) >= 8:
                        break
            except Exception:
                return []

        return results


scraper_service = ScraperService()
