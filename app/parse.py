import csv
from dataclasses import dataclass, astuple, fields
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://webscraper.io/"

HOME_URL = urljoin(BASE_URL, "test-sites/e-commerce/more/")
COMPUTERS_URL = urljoin(HOME_URL, "computers/")
LAPTOPS_URL = urljoin(COMPUTERS_URL, "laptops")
TABLETS_URL = urljoin(COMPUTERS_URL, "tablets")

PHONES_URL = urljoin(HOME_URL, "phones/")
TOUCH_URL = urljoin(PHONES_URL, "touch")

WAIT_SECONDS = 5

CLS_CARD = "card-body"
CLS_ACCEPT_COOKIES = "acceptCookies"
CLS_LOAD_MORE = "ecomerce-items-scroll-more"
CLS_TITLE = "title"
CLS_DESC = "description"
CLS_PRICE = "price"
CLS_REVIEW_COUNT = "review-count"
CLS_STAR = "ws-icon-star"
CSS_RATING = "p[data-rating]"


@dataclass
class Product:
    title: str
    description: str
    price: float
    rating: int
    num_of_reviews: int


PRODUCT_FIELDS = [f.name for f in fields(Product)]

FILE_COLLECTION = {
    "home.csv": HOME_URL,
    "computers.csv": COMPUTERS_URL,
    "laptops.csv": LAPTOPS_URL,
    "tablets.csv": TABLETS_URL,
    "phones.csv": PHONES_URL,
    "touch.csv": TOUCH_URL,
}


def _safe_click_accept_cookies(driver: webdriver.Chrome, url: str) -> None:
    try:
        driver.find_element(By.CLASS_NAME, CLS_ACCEPT_COOKIES).click()
    except Exception:
        print(f"No cookies found on {url}. Skipping.")


def _extract_rating(card: WebElement) -> int:
    try:
        raw = card.find_element(By.CSS_SELECTOR, CSS_RATING).get_attribute("data-rating")
        return int(raw)
    except Exception:
        return len(card.find_elements(By.CLASS_NAME, CLS_STAR))


def _extract_reviews_count(card: WebElement) -> int:
    try:
        text = card.find_element(By.CLASS_NAME, CLS_REVIEW_COUNT).text
        return int(text.split()[0])
    except Exception:
        return 0


def create_product(card: WebElement) -> Product | None:
    try:
        title_el = card.find_element(By.CLASS_NAME, CLS_TITLE)
        price_text = card.find_element(By.CLASS_NAME, CLS_PRICE).text

        return Product(
            title=title_el.get_attribute("title"),
            description=card.find_element(By.CLASS_NAME, CLS_DESC).text,
            price=float(price_text.replace("$", "")),
            rating=_extract_rating(card),
            num_of_reviews=_extract_reviews_count(card),
        )
    except Exception as exc:
        print(f"Skipping a product due to error: {exc}")
        return None


def _load_all_items(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    while True:
        try:
            before = len(driver.find_elements(By.CLASS_NAME, CLS_CARD))
            btn = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, CLS_LOAD_MORE)))

            if not btn.is_displayed():
                return

            driver.execute_script("arguments[0].click();", btn)
            wait.until(lambda d: len(d.find_elements(By.CLASS_NAME, CLS_CARD)) > before)
        except Exception:
            return


def scrap_single_page(driver: webdriver.Chrome, url: str) -> list[Product]:
    driver.get(url)
    wait = WebDriverWait(driver, WAIT_SECONDS)

    _safe_click_accept_cookies(driver, url)

    try:
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, CLS_CARD)))
    except Exception:
        print(f"No products found on {url}. Skipping.")
        return []

    _load_all_items(driver, wait)

    cards = driver.find_elements(By.CLASS_NAME, CLS_CARD)
    print(f"Finished loading {url}. Total items: {len(cards)}")

    products = (create_product(card) for card in cards)
    return [p for p in products if p is not None]


def write_products_to_csv(products: list[Product], file_name: str) -> None:
    with open(file_name, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(PRODUCT_FIELDS)
        writer.writerows(astuple(p) for p in products)


def get_all_products() -> None:
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options,
    )

    try:
        for out_name, page_url in FILE_COLLECTION.items():
            items = scrap_single_page(driver=driver, url=page_url)
            write_products_to_csv(products=items, file_name=out_name)
    finally:
        driver.quit()


if __name__ == "__main__":
    get_all_products()
