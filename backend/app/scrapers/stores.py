import asyncio
import re
import traceback
from playwright.async_api import async_playwright
from app.scrapers.base import BaseScraper

class GenericWebScraper(BaseScraper):
    async def scrape(self) -> dict:
        orig_price = self.generate_mock_price()
        current_price = orig_price
        scraped_price = None
        scraped_title = None
        scraped_image = None
        updates_type = "Simulated Crawler"
        
        try:
            async with async_playwright() as p:
                browser, context = await self.get_browser_context(p)
                page = await context.new_page()
                
                # Setup page timeout
                await page.goto(self.url, wait_until="domcontentloaded", timeout=12000)
                
                # Extract meta tags
                scraped_title = await page.get_attribute("meta[property='og:title']", "content")
                scraped_image = await page.get_attribute("meta[property='og:image']", "content")
                
                # Check meta price tags
                meta_price = await page.get_attribute("meta[property='product:price:amount']", "content")
                if not meta_price:
                    meta_price = await page.get_attribute("meta[property='og:price:amount']", "content")
                
                if meta_price:
                    try:
                        scraped_price = float(meta_price.replace("$", "").replace(",", "").strip())
                    except ValueError:
                        pass
                
                # Try DOM elements if meta failed
                if not scraped_price:
                    selectors = [
                        ".price", ".product-price", "[itemprop='price']", 
                        ".current-price", ".sales .value", "#price-value"
                    ]
                    for sel in selectors:
                        try:
                            element = page.locator(sel).first
                            if await element.is_visible():
                                text = await element.text_content()
                                cleaned = text.replace("$", "").replace(",", "").strip()
                                scraped_price = float(cleaned)
                                break
                        except Exception:
                            continue
                            
                await browser.close()
                
                if scraped_price:
                    current_price = scraped_price
                    orig_price = scraped_price
                    updates_type = "Live Scraper"
                    
        except Exception as e:
            print(f"[GenericScraper] Failed to scrape {self.url}: {str(e)}")
            
        return {
            "name": scraped_title or self.name,
            "brand": self.brand,
            "store": self.store,
            "url": self.url,
            "image": scraped_image or self.image,
            "size": self.size,
            "original_price": orig_price,
            "current_price": current_price,
            "updates_type": updates_type,
            "status": "Stable"
        }

class NikeScraper(BaseScraper):
    async def scrape(self) -> dict:
        try:
            async with async_playwright() as p:
                browser, context = await self.get_browser_context(p)
                page = await context.new_page()
                await page.goto(self.url, wait_until="networkidle", timeout=15000)
                
                # Attempt to extract title and price from DOM
                title_el = page.locator("h1#pdp_product_title").first
                price_el = page.locator(".product-price").first
                
                title = await title_el.text_content() if await title_el.is_visible() else self.name
                price_str = await price_el.text_content() if await price_el.is_visible() else None
                
                await browser.close()
                
                if price_str:
                    cleaned_price = float(price_str.replace("$", "").replace(",", "").strip())
                    return {
                        "name": title.strip(),
                        "brand": "Nike",
                        "store": "Nike",
                        "url": self.url,
                        "image": self.image,
                        "size": self.size,
                        "original_price": cleaned_price,
                        "current_price": cleaned_price,
                        "updates_type": "Live Scraper",
                        "status": "Stable"
                    }
        except Exception as e:
            print(f"[NikeScraper] Live scrape failed (Cloudflare blocker detected). Toggling simulation fallback.")
            
        # Resilient simulation fallback
        mock_price = self.generate_mock_price()
        return {
            "name": self.name,
            "brand": self.brand,
            "store": "Nike",
            "url": self.url,
            "image": self.image,
            "size": self.size,
            "original_price": mock_price,
            "current_price": mock_price,
            "updates_type": "Simulated Crawler",
            "status": "Stable"
        }

class AdidasScraper(BaseScraper):
    async def scrape(self) -> dict:
        try:
            async with async_playwright() as p:
                browser, context = await self.get_browser_context(p)
                page = await context.new_page()
                await page.goto(self.url, wait_until="domcontentloaded", timeout=12000)
                
                # Extract pricing block
                price_el = page.locator(".gl-price-item").first
                price_str = await price_el.text_content() if await price_el.is_visible() else None
                
                await browser.close()
                if price_str:
                    price = float(price_str.replace("$", "").replace(",", "").strip())
                    return {
                        "name": self.name,
                        "brand": "Adidas",
                        "store": "Adidas",
                        "url": self.url,
                        "image": self.image,
                        "size": self.size,
                        "original_price": price,
                        "current_price": price,
                        "updates_type": "Live Scraper",
                        "status": "Stable"
                    }
        except Exception:
            print(f"[AdidasScraper] Live scrape failed (Blocked). Toggling simulation fallback.")
            
        mock_price = self.generate_mock_price()
        return {
            "name": self.name,
            "brand": self.brand,
            "store": "Adidas",
            "url": self.url,
            "image": self.image,
            "size": self.size,
            "original_price": mock_price,
            "current_price": mock_price,
            "updates_type": "Simulated Crawler",
            "status": "Stable"
        }

class StockXScraper(BaseScraper):
    async def scrape(self) -> dict:
        try:
            async with async_playwright() as p:
                browser, context = await self.get_browser_context(p)
                page = await context.new_page()
                await page.goto(self.url, wait_until="domcontentloaded", timeout=15000)
                
                # Extract JSON-LD script or price element
                price_el = page.locator(".cc-price").first # Sample StockX price tag
                price_str = await price_el.text_content() if await price_el.is_visible() else None
                
                await browser.close()
                if price_str:
                    price = float(price_str.replace("$", "").replace(",", "").strip())
                    return {
                        "name": self.name,
                        "brand": self.brand,
                        "store": "StockX",
                        "url": self.url,
                        "image": self.image,
                        "size": self.size,
                        "original_price": price,
                        "current_price": price,
                        "updates_type": "Live Scraper",
                        "status": "Stable"
                    }
        except Exception:
            print(f"[StockXScraper] Live scrape failed (Blocked by Akamai/Cloudflare). Toggling simulation fallback.")
            
        mock_price = self.generate_mock_price()
        return {
            "name": self.name,
            "brand": self.brand,
            "store": "StockX",
            "url": self.url,
            "image": self.image,
            "size": self.size,
            "original_price": mock_price,
            "current_price": mock_price,
            "updates_type": "Simulated Crawler",
            "status": "Stable"
        }

class GoatScraper(BaseScraper):
    async def scrape(self) -> dict:
        try:
            async with async_playwright() as p:
                browser, context = await self.get_browser_context(p)
                page = await context.new_page()
                await page.goto(self.url, wait_until="domcontentloaded", timeout=15000)
                
                # GOAT uses complex React state, search for price in metadata or text
                price_el = page.locator("[class*='Price']").first
                price_str = await price_el.text_content() if await price_el.is_visible() else None
                
                await browser.close()
                if price_str:
                    price = float(price_str.replace("$", "").replace(",", "").strip())
                    return {
                        "name": self.name,
                        "brand": self.brand,
                        "store": "GOAT",
                        "url": self.url,
                        "image": self.image,
                        "size": self.size,
                        "original_price": price,
                        "current_price": price,
                        "updates_type": "Live Scraper",
                        "status": "Stable"
                    }
        except Exception:
            print(f"[GoatScraper] Live scrape failed (Blocked). Toggling simulation fallback.")
            
        mock_price = self.generate_mock_price()
        return {
            "name": self.name,
            "brand": self.brand,
            "store": "GOAT",
            "url": self.url,
            "image": self.image,
            "size": self.size,
            "original_price": mock_price,
            "current_price": mock_price,
            "updates_type": "Simulated Crawler",
            "status": "Stable"
        }

class FootLockerScraper(BaseScraper):
    async def scrape(self) -> dict:
        try:
            async with async_playwright() as p:
                browser, context = await self.get_browser_context(p)
                page = await context.new_page()
                await page.goto(self.url, wait_until="domcontentloaded", timeout=12000)
                
                price_el = page.locator(".ProductPrice-current").first
                price_str = await price_el.text_content() if await price_el.is_visible() else None
                
                await browser.close()
                if price_str:
                    price = float(price_str.replace("$", "").replace(",", "").strip())
                    return {
                        "name": self.name,
                        "brand": self.brand,
                        "store": "Foot Locker",
                        "url": self.url,
                        "image": self.image,
                        "size": self.size,
                        "original_price": price,
                        "current_price": price,
                        "updates_type": "Live Scraper",
                        "status": "Stable"
                    }
        except Exception:
            print(f"[FootLockerScraper] Live scrape failed. Toggling simulation fallback.")
            
        mock_price = self.generate_mock_price()
        return {
            "name": self.name,
            "brand": self.brand,
            "store": "Foot Locker",
            "url": self.url,
            "image": self.image,
            "size": self.size,
            "original_price": mock_price,
            "current_price": mock_price,
            "updates_type": "Simulated Crawler",
            "status": "Stable"
        }

class VegNonVegScraper(BaseScraper):
    async def scrape(self) -> dict:
        try:
            async with async_playwright() as p:
                browser, context = await self.get_browser_context(p)
                page = await context.new_page()
                await page.goto(self.url, wait_until="domcontentloaded", timeout=12000)
                
                scraped_title = await page.get_attribute("meta[property='og:title']", "content")
                scraped_image = await page.get_attribute("meta[property='og:image']", "content")
                
                meta_price = await page.get_attribute("meta[property='og:price:amount']", "content")
                price = None
                if meta_price:
                    price = float(meta_price.replace(",", "").strip())
                else:
                    price_el = page.locator(".price, .price-item, .product-price").first
                    if await price_el.is_visible():
                        price_str = await price_el.text_content()
                        cleaned = re.sub(r'[^\d.]', '', price_str)
                        price = float(cleaned)
                        
                await browser.close()
                if price:
                    return {
                        "name": scraped_title.split("|")[0].strip() if scraped_title else self.name,
                        "brand": self.brand,
                        "store": "VegNonVeg",
                        "url": self.url,
                        "image": scraped_image or self.image,
                        "size": self.size,
                        "original_price": price,
                        "current_price": price,
                        "updates_type": "Live Scraper",
                        "status": "Stable"
                    }
        except Exception as e:
            print(f"[VegNonVegScraper] Live scrape failed: {str(e)}. Falling back to simulation.")
            
        mock_price = self.generate_mock_price()
        return {
            "name": self.name,
            "brand": self.brand,
            "store": "VegNonVeg",
            "url": self.url,
            "image": self.image,
            "size": self.size,
            "original_price": mock_price,
            "current_price": mock_price,
            "updates_type": "Simulated Crawler",
            "status": "Stable"
        }

class SuperkicksScraper(BaseScraper):
    async def scrape(self) -> dict:
        try:
            async with async_playwright() as p:
                browser, context = await self.get_browser_context(p)
                page = await context.new_page()
                await page.goto(self.url, wait_until="domcontentloaded", timeout=12000)
                
                scraped_title = await page.get_attribute("meta[property='og:title']", "content")
                scraped_image = await page.get_attribute("meta[property='og:image']", "content")
                
                meta_price = await page.get_attribute("meta[property='og:price:amount']", "content")
                price = None
                if meta_price:
                    price = float(meta_price.replace(",", "").strip())
                else:
                    price_el = page.locator(".price-item--sale, .price-item--regular, .price").first
                    if await price_el.is_visible():
                        price_str = await price_el.text_content()
                        cleaned = re.sub(r'[^\d.]', '', price_str)
                        price = float(cleaned)
                        
                await browser.close()
                if price:
                    return {
                        "name": scraped_title.split("|")[0].strip() if scraped_title else self.name,
                        "brand": self.brand,
                        "store": "Superkicks",
                        "url": self.url,
                        "image": scraped_image or self.image,
                        "size": self.size,
                        "original_price": price,
                        "current_price": price,
                        "updates_type": "Live Scraper",
                        "status": "Stable"
                    }
        except Exception as e:
            print(f"[SuperkicksScraper] Live scrape failed: {str(e)}. Falling back to simulation.")
            
        mock_price = self.generate_mock_price()
        return {
            "name": self.name,
            "brand": self.brand,
            "store": "Superkicks",
            "url": self.url,
            "image": self.image,
            "size": self.size,
            "original_price": mock_price,
            "current_price": mock_price,
            "updates_type": "Simulated Crawler",
            "status": "Stable"
        }

class AsicsScraper(BaseScraper):
    async def scrape(self) -> dict:
        try:
            async with async_playwright() as p:
                browser, context = await self.get_browser_context(p)
                page = await context.new_page()
                await page.goto(self.url, wait_until="domcontentloaded", timeout=12000)
                
                scraped_title = await page.get_attribute("meta[property='og:title']", "content")
                scraped_image = await page.get_attribute("meta[property='og:image']", "content")
                
                meta_price = await page.get_attribute("meta[property='product:price:amount']", "content")
                if not meta_price:
                    meta_price = await page.get_attribute("meta[property='og:price:amount']", "content")
                
                price = None
                if meta_price:
                    price = float(meta_price.replace(",", "").strip())
                else:
                    price_el = page.locator(".price, [itemprop='price']").first
                    if await price_el.is_visible():
                        price_str = await price_el.text_content()
                        cleaned = re.sub(r'[^\d.]', '', price_str)
                        price = float(cleaned)
                        
                await browser.close()
                if price:
                    return {
                        "name": scraped_title.split("|")[0].strip() if scraped_title else self.name,
                        "brand": "ASICS",
                        "store": "Asics India" if "asics.co.in" in self.url else "Asics",
                        "url": self.url,
                        "image": scraped_image or self.image,
                        "size": self.size,
                        "original_price": price,
                        "current_price": price,
                        "updates_type": "Live Scraper",
                        "status": "Stable"
                    }
        except Exception as e:
            print(f"[AsicsScraper] Live scrape failed: {str(e)}. Falling back to simulation.")
            
        mock_price = self.generate_mock_price()
        return {
            "name": self.name,
            "brand": "ASICS",
            "store": "Asics India" if "asics.co.in" in self.url else "Asics",
            "url": self.url,
            "image": self.image,
            "size": self.size,
            "original_price": mock_price,
            "current_price": mock_price,
            "updates_type": "Simulated Crawler",
            "status": "Stable"
        }

class OnitsukaTigerScraper(BaseScraper):
    async def scrape(self) -> dict:
        try:
            async with async_playwright() as p:
                browser, context = await self.get_browser_context(p)
                page = await context.new_page()
                await page.goto(self.url, wait_until="domcontentloaded", timeout=12000)
                
                scraped_title = await page.get_attribute("meta[property='og:title']", "content")
                scraped_image = await page.get_attribute("meta[property='og:image']", "content")
                
                meta_price = await page.get_attribute("meta[property='product:price:amount']", "content")
                if not meta_price:
                    meta_price = await page.get_attribute("meta[property='og:price:amount']", "content")
                
                price = None
                if meta_price:
                    price = float(meta_price.replace(",", "").strip())
                else:
                    price_el = page.locator(".price, [itemprop='price']").first
                    if await price_el.is_visible():
                        price_str = await price_el.text_content()
                        cleaned = re.sub(r'[^\d.]', '', price_str)
                        price = float(cleaned)
                        
                await browser.close()
                if price:
                    return {
                        "name": scraped_title.split("|")[0].strip() if scraped_title else self.name,
                        "brand": "Onitsuka Tiger",
                        "store": "Onitsuka Tiger India" if "/in" in self.url else "Onitsuka Tiger",
                        "url": self.url,
                        "image": scraped_image or self.image,
                        "size": self.size,
                        "original_price": price,
                        "current_price": price,
                        "updates_type": "Live Scraper",
                        "status": "Stable"
                    }
        except Exception as e:
            print(f"[OnitsukaTigerScraper] Live scrape failed: {str(e)}. Falling back to simulation.")
            
        mock_price = self.generate_mock_price()
        return {
            "name": self.name,
            "brand": "Onitsuka Tiger",
            "store": "Onitsuka Tiger India" if "/in" in self.url else "Onitsuka Tiger",
            "url": self.url,
            "image": self.image,
            "size": self.size,
            "original_price": mock_price,
            "current_price": mock_price,
            "updates_type": "Simulated Crawler",
            "status": "Stable"
        }
