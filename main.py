import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode [[1]](https://apidog.com/blog/crawl4ai-tutorial/)

# Import AdaptiveCrawler if available (v0.4.0+)
try:
    from crawl4ai import AdaptiveCrawler
except ImportError:
    AdaptiveCrawler = None

app = FastAPI()

# --- Data Models for n8n ---
class AdaptiveRequest(BaseModel):
    url: str
    query: str  # What the AI should look for
    max_pages: int = 5
    openai_api_key: str # Pass key from n8n or set as Env Var

class RecursiveRequest(BaseModel):
    url: str
    max_depth: int = 2
    max_pages: int = 10

# --- Endpoint 1: Adaptive Crawler ---
@app.post("/crawl/adaptive")
async def crawl_adaptive(request: AdaptiveRequest):
    if not AdaptiveCrawler:
        raise HTTPException(status_code=501, detail="AdaptiveCrawler not available in this version.")
    
    print(f"🧠 Starting Adaptive Crawl for: {request.query}")
    
    # Initialize the Adaptive Crawler
    # Note: In production, use os.environ["OPENAI_API_KEY"] instead of passing it in JSON
    async with AsyncWebCrawler(verbose=True) as crawler:
        adaptive_crawler = AdaptiveCrawler(
            crawler=crawler,
            openai_api_key=request.openai_api_key
        )
        
        result = await adaptive_crawler.run(
            url=request.url,
            query=request.query,
            max_pages=request.max_pages
        )
        
    return {"status": "success", "data": result}

# --- Endpoint 2: Simple Recursive Crawler (BFS) ---
@app.post("/crawl/recursive")
async def crawl_recursive(request: RecursiveRequest):
    print(f"🕸️ Starting Recursive Crawl: {request.url} (Depth: {request.max_depth})")
    
    visited = set()
    queue = [(request.url, 0)] # Tuple: (url, current_depth)
    results = []
    
    async with AsyncWebCrawler() as crawler:
        while queue and len(results) < request.max_pages:
            current_url, depth = queue.pop(0)
            
            if current_url in visited or depth > request.max_depth:
                continue
            
            visited.add(current_url)
            
            # Crawl the page
            result = await crawler.arun(
                url=current_url,
                config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
            )
            
            if result.success:
                results.append({
                    "url": current_url,
                    "markdown": result.markdown[:500] + "..." # Truncate for preview
                })
                
                # If not at max depth, add internal links to queue
                if depth < request.max_depth:
                    # Filter for internal links only to stay on domain
                    internal_links = result.links.get("internal", [])
                    for link in internal_links:
                        if link['href'] not in visited:
                            queue.append((link['href'], depth + 1))
                            
    return {"status": "success", "pages_crawled": len(results), "data": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)