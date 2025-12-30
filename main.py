import asyncio
import re
import subprocess
import sys
from typing import List, Set
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# --- FIX: Install Browser if missing ---
def install_playwright():
    """
    Checks if Playwright browsers are installed.
    If not, installs them. This fixes the 'Executable doesn't exist' error on Zeabur.
    """
    print("🔧 Checking Playwright browser installation...")
    try:
        # Try to run a simple playwright command to see if it works
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("✅ Playwright browsers installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install browsers: {e}")
        # We continue anyway, hoping they are already there, 
        # otherwise the crawler will crash with the original error.

class RecursiveCrawler:
    def __init__(self, start_url: str, max_depth: int = 3, max_pages: int = 100, include_regex: str = None):
        self.start_url = start_url
        self.base_domain = urlparse(start_url).netloc
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.include_regex = re.compile(include_regex) if include_regex else None
        
        # State tracking
        self.visited: Set[str] = set()
        self.urls_to_crawl: List[str] = [start_url]
        self.crawled_count = 0

    def is_valid_link(self, url: str) -> bool:
        """
        Filters URLs to ensure they are:
        1. Internal (same domain)
        2. Not visited
        3. Match the specific regex (if provided)
        """
        parsed = urlparse(url)
        
        # 1. Check if it's the same domain
        if parsed.netloc != self.base_domain:
            return False
            
        # 2. Check if already visited
        if url in self.visited:
            return False
            
        # 3. Check "What I want" (Regex filter)
        if self.include_regex and url != self.start_url:
            if not self.include_regex.search(url):
                return False
                
        # Exclude common non-html files
        if any(url.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.pdf', '.css', '.js', '.ico']):
            return False

        return True

    async def run(self):
        print(f"🚀 Starting crawl on {self.start_url}")
        print(f"🎯 Filter pattern: {self.include_regex.pattern if self.include_regex else 'Entire Website'}")

        # Configure Browser (Global)
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            text_mode=True 
        )

        # Configure Run (Per page)
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.ENABLED,
            exclude_external_links=True,
            word_count_threshold=10,
            stream=True
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            current_depth = 0
            
            while current_depth <= self.max_depth and self.crawled_count < self.max_pages and self.urls_to_crawl:
                
                print(f"\n--- Depth {current_depth}: Processing {len(self.urls_to_crawl)} URLs ---")
                
                next_depth_urls = set()
                
                results = await crawler.arun_many(
                    urls=self.urls_to_crawl,
                    config=run_config
                )

                for result in results:
                    if not result.success:
                        print(f"❌ Failed: {result.url} - {result.error_message}")
                        continue

                    self.visited.add(result.url)
                    self.crawled_count += 1
                    print(f"✅ Crawled ({self.crawled_count}): {result.url}")

                    internal_links = result.links.get("internal", [])
                    
                    for link_data in internal_links:
                        href = link_data.get('href')
                        if href and self.is_valid_link(href):
                            next_depth_urls.add(href)

                    if self.crawled_count >= self.max_pages:
                        break

                self.urls_to_crawl = list(next_depth_urls)
                current_depth += 1

        print(f"\n🏁 Crawl Finished. Total pages visited: {self.crawled_count}")

async def main():
    # Example: Crawl the Crawl4AI documentation
    spider = RecursiveCrawler(
        start_url="https://docs.crawl4ai.com",
        max_depth=3,
        max_pages=50,
        include_regex=r"api"
    )
    await spider.run()

if __name__ == "__main__":
    # 1. Install browsers first
    install_playwright()
    
    # 2. Run the main async loop
    asyncio.run(main())
