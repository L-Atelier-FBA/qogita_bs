import asyncio
import logging
import json
import os
import random
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from core.login import QogitaLogin
from core.requester import Requester

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

JSON_FILE = "products.json"
STATE_FILE = "category_state.json"
CATEGORIES = [
    "https://www.qogita.com/categories/health-beauty/health/?size=72&page={}",
    "https://www.qogita.com/categories/health-beauty/body/?size=72&page={}",
    "https://www.qogita.com/categories/health-beauty/face/?size=72&page={}",
    "https://www.qogita.com/categories/health-beauty/hair/?size=72&page={}",
    "https://www.qogita.com/categories/health-beauty/makeup/?size=72&page={}",
    "https://www.qogita.com/categories/health-beauty/home-lifestyle/?size=72&page={}",
]

def load_state() -> int:
    if not os.path.exists(STATE_FILE):
        save_state(0)
        return 0
    with open(STATE_FILE, "r") as f:
        return json.load(f).get("current_index", 0)

def save_state(index: int) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump({"current_index": index}, f)

def parse_price(price_text: str) -> float:
    try:
        return float(price_text.replace("€", "").replace(",", "").strip())
    except Exception:
        return 0.0

async def qogita_scraper():
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")
    proxy = os.getenv("PROXY")

    if not email or not password:
        raise ValueError("Missing credential in .env")

    logger.info("Logging in...")
    login = QogitaLogin(email=email, password=password, headless=True)
    cookies = await login.login()
    if not cookies:
        raise RuntimeError("Login failed. No cookies returned.")

    current_index = load_state()
    category_url_template = CATEGORIES[current_index]
    logger.info(f"Scraping category {current_index + 1}/{len(CATEGORIES)}")

    product_data = []
    existing_gtins = set()

    async with Requester(referrer="https://www.qogita.com/categories/", cookies=cookies, proxy=proxy) as session:
        page = 1
        while True:
            url = category_url_template.format(page)
            logger.info(f"Scraping page {page}...")

            try:
                response = await session.fetch_get(url)
                if not response or response.status_code != 200:
                    logger.warning(f"Stopping. Status code: {getattr(response, 'status_code', None)}")
                    break
            except Exception as e:
                logger.error(f"Request failed on page {page}: {e}")
                break

            soup = BeautifulSoup(response.text, "lxml")
            print(soup.title.string)

            names = soup.select("a.line-clamp-2")
            prices = soup.select("span.whitespace-nowrap.font-figtree")
            gtins = soup.select("p[data-dd-action-name='Product Card GTIN']")
            brands = soup.select("a.font-outfit")

            if not names:
                logger.info("No products found. Ending pagination.")
                break

            min_len = min(len(names), len(prices), len(gtins), len(brands))
            for idx in range(min_len):
                gtin_text = gtins[idx].get_text(strip=True)
                if not gtin_text or gtin_text in existing_gtins:
                    continue

                link = names[idx].get("href", "")
                if link.startswith("/"):
                    link = f"https://www.qogita.com{link}"

                product_data.append({
                    "product_name": names[idx].get_text(strip=True),
                    "product_gtin": gtin_text,
                    "supplier_price": parse_price(prices[idx].get_text()),
                    "product_link": link,
                    "brand": brands[idx].get_text(strip=True)
                })
                existing_gtins.add(gtin_text)

            logger.info(f"Collected so far: {len(product_data)} products")

            page += 1
            delay = random.uniform(1.5, 4.0)
            logger.info(f"Sleeping for {delay:.2f}s")
            await asyncio.sleep(delay)

    try:
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(product_data, f, ensure_ascii=False, indent=4)
        logger.info(f"Finished. Total products: {len(product_data)}")
    except Exception as e:
        logger.error(f"Failed to write JSON file: {e}")

    next_index = (current_index + 1) % len(CATEGORIES)
    save_state(next_index)
    logger.info(f"Next category index saved: {next_index}")


if __name__ == "__main__":
    asyncio.run(qogita_scraper())
