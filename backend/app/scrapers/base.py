import asyncio
import re
from urllib.parse import urlparse
from playwright.async_api import async_playwright

# Stock Sneaker Images on Unsplash
SNEAKER_IMAGES = {
    "jordan": "https://images.unsplash.com/photo-1552346154-21d32810aba3?w=600&auto=format&fit=crop&q=80",
    "dunk": "https://images.unsplash.com/photo-1606107557195-0e29a4b5b4aa?w=600&auto=format&fit=crop&q=80",
    "run": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&auto=format&fit=crop&q=80",
    "adidas": "https://images.unsplash.com/photo-1539185441755-769473a23570?w=600&auto=format&fit=crop&q=80",
    "casual": "https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=600&auto=format&fit=crop&q=80",
    "default": "https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=600&auto=format&fit=crop&q=80"
}

class BaseScraper:
    def __init__(self, url: str, size: str = "9.5"):
        self.url = url
        self.size = size
        self.store = self.detect_store()
        self.slug = self.extract_slug()
        self.name, self.brand = self.parse_slug()
        self.image = self.get_sneaker_image()

    def detect_store(self) -> str:
        try:
            parsed = urlparse(self.url)
            host = (parsed.hostname or "").lower()
            path = parsed.path.lower()
            
            if "nike.com" in host:
                if "/in" in path or "/in/" in path:
                    return "Nike India"
                return "Nike"
            if "adidas.co.in" in host or "adidas.in" in host:
                return "Adidas India"
            if "vegnonveg.com" in host:
                return "VegNonVeg"
            if "superkicks.in" in host:
                return "Superkicks"
            if "themainstreet.in" in host:
                return "Mainstreet Store"
            if "crepdogcrew.com" in host:
                return "Crepdog Crew"
            if "in.puma.com" in host:
                return "Puma India"
            if "adidas.com" in host: return "Adidas"
            if "stockx.com" in host: return "StockX"
            if "goat.com" in host: return "GOAT"
            if "footlocker.com" in host: return "Foot Locker"
            return "Custom Store"
        except Exception:
            return "Unknown Store"

    def extract_slug(self) -> str:
        try:
            parsed = urlparse(self.url)
            path = parsed.path
            parts = [p for p in path.split("/") if p]
            if not parts:
                return "custom-sneaker"
            
            # Find the segment with hyphens indicating a slug
            candidates = [p for p in parts if "-" in p and len(p) > 4]
            slug = candidates[-1] if candidates else parts[-1]
            
            # Clean suffix
            slug = re.sub(r'\.html$', '', slug, flags=re.IGNORECASE)
            slug = re.sub(r'-shoes$', '', slug, flags=re.IGNORECASE)
            slug = re.sub(r'-sneakers$', '', slug, flags=re.IGNORECASE)
            return slug
        except Exception:
            return "custom-sneaker"

    def parse_slug(self):
        slug_clean = self.slug.replace("-", " ")
        words = []
        for word in slug_clean.split():
            # Skip code identifiers (e.g. DZ5485)
            if re.match(r'^[a-z0-9]{6,10}$', word, re.IGNORECASE):
                continue
            words.append(word.capitalize())
            
        name = " ".join(words) if words else "Premium Sneaker"
        
        # Determine Brand
        name_lower = name.lower()
        if "jordan" in name_lower: brand = "Jordan"
        elif "yeezy" in name_lower: brand = "Yeezy"
        elif "adidas" in name_lower or "ultraboost" in name_lower: brand = "Adidas"
        elif "nike" in name_lower or "dunk" in name_lower: brand = "Nike"
        elif "new balance" in name_lower: brand = "New Balance"
        elif "puma" in name_lower: brand = "Puma"
        else: brand = self.store if self.store not in ["Custom Store", "Unknown Store"] else "Premium"
        
        return name, brand

    def get_sneaker_image(self) -> str:
        slug_lower = self.slug.lower()
        if any(k in slug_lower for k in ["jordan", "retro-high", "air-force"]):
            return SNEAKER_IMAGES["jordan"]
        if any(k in slug_lower for k in ["dunk", "sb"]):
            return SNEAKER_IMAGES["dunk"]
        if any(k in slug_lower for k in ["yeezy", "ultraboost", "nmd"]):
            return SNEAKER_IMAGES["adidas"]
        if any(k in slug_lower for k in ["max", "zoom", "run", "pegasus"]):
            return SNEAKER_IMAGES["run"]
        if any(k in slug_lower for k in ["casual", "blazer", "stan-smith"]):
            return SNEAKER_IMAGES["casual"]
        return SNEAKER_IMAGES["default"]

    def generate_mock_price(self) -> float:
        # Base retail estimate in Indian Rupees (INR)
        price = 11999.0
        if self.brand == "Jordan": price = 16995.0
        elif self.brand == "Yeezy": price = 22999.0
        elif self.brand == "Nike": price = 9995.0
        elif self.brand == "Adidas": price = 10999.0
        elif self.brand == "Puma": price = 8999.0
        elif self.brand == "New Balance": price = 12999.0
        return price

    async def get_browser_context(self, playwright):
        # Setup modern stealth headers
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            device_scale_factor=1,
            has_touch=False,
            is_mobile=False
        )
        return browser, context

    async def scrape(self) -> dict:
        """Override in subclass. Fallback is provided below."""
        print(f"[BaseScraper] Simulating scraping for {self.url}")
        await asyncio.sleep(0.5) # Simulate latency
        
        orig_price = self.generate_mock_price()
        current_price = orig_price
        
        return {
            "name": self.name,
            "brand": self.brand,
            "store": self.store,
            "url": self.url,
            "image": self.image,
            "size": self.size,
            "original_price": orig_price,
            "current_price": current_price,
            "updates_type": "Simulated Crawler",
            "status": "Stable"
        }
