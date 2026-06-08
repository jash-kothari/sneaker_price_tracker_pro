from urllib.parse import urlparse
from app.scrapers.base import BaseScraper
from app.scrapers.stores import (
    GenericWebScraper,
    NikeScraper,
    AdidasScraper,
    StockXScraper,
    GoatScraper,
    FootLockerScraper,
    VegNonVegScraper,
    SuperkicksScraper,
    AsicsScraper,
    OnitsukaTigerScraper
)

def get_scraper(url: str, size: str = "9.5") -> BaseScraper:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
    except Exception:
        return GenericWebScraper(url, size)

    if "nike.com" in host:
        return NikeScraper(url, size)
    elif "adidas.co.in" in host or "adidas.in" in host or "adidas.com" in host:
        return AdidasScraper(url, size)
    elif "asics.co.in" in host or "asics.com" in host:
        return AsicsScraper(url, size)
    elif "onitsukatiger.com" in host:
        return OnitsukaTigerScraper(url, size)
    elif "vegnonveg.com" in host:
        return VegNonVegScraper(url, size)
    elif "superkicks.in" in host:
        return SuperkicksScraper(url, size)
    elif "stockx.com" in host:
        return StockXScraper(url, size)
    elif "goat.com" in host:
        return GoatScraper(url, size)
    elif "footlocker.com" in host:
        return FootLockerScraper(url, size)
    else:
        return GenericWebScraper(url, size)

async def run_scraper(url: str, size: str = "9.5") -> dict:
    scraper = get_scraper(url, size)
    data = await scraper.scrape()
    if "image" in data and data["image"]:
        data["image"] = scraper.make_absolute_url(data["image"])
    return data
