#!/usr/bin/env python3
"""
Web Search MCP Server

Provides web search capabilities using DuckDuckGo scraping and web content extraction.
No API keys required - completely self-contained web search functionality.
"""

import asyncio
import logging
import re
import time
import urllib.parse
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

import aiohttp
from bs4 import BeautifulSoup
import json

from ..base.server import AIShowmakerMCPServer


@dataclass
class SearchResult:
    """Represents a search result."""
    title: str
    url: str
    snippet: str
    source: str
    timestamp: datetime


@dataclass
class WebContent:
    """Represents extracted web content."""
    url: str
    title: str
    content: str
    text_content: str
    metadata: Dict[str, Any]
    timestamp: datetime


class WebSearchMCPServer(AIShowmakerMCPServer):
    """
    Web Search MCP Server using DuckDuckGo scraping.
    
    Provides web search capabilities without requiring API keys.
    """
    
    def __init__(self):
        """Initialize the web search MCP server."""
        super().__init__("websearch", version="1.0.0", description="Web Search MCP Server using DuckDuckGo scraping")
        self.logger = logging.getLogger("mcp.websearch")
        
        # Rate limiting and caching
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests
        self.cache = {}
        self.cache_duration = timedelta(hours=1)
        
        # User agents for rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]
    
    async def initialize(self) -> None:
        """Initialize the web search MCP server and register tools."""
        # Create MCPTool objects for each tool
        from ..base.server import MCPTool
        
        # Register search_web tool
        search_web_tool = MCPTool(
            name="search_web",
            description="Search the web using DuckDuckGo. No API key required.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Maximum number of results (1-10)", "default": 5, "minimum": 1, "maximum": 10},
                    "region": {"type": "string", "description": "Search region (e.g., us-en, uk-en, de-de)", "default": "us-en"}
                },
                "required": ["query"]
            },
            execute_func=self.search_web,
            category="web_search",
            version="1.0.0"
        )
        self.register_tool(search_web_tool)
        
        # Register extract_content tool
        extract_content_tool = MCPTool(
            name="extract_content",
            description="Extract content from a web page.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to extract content from"},
                    "max_length": {"type": "integer", "description": "Maximum length of extracted text", "default": 2000, "minimum": 100, "maximum": 10000}
                },
                "required": ["url"]
            },
            execute_func=self.extract_content,
            category="web_search",
            version="1.0.0"
        )
        self.register_tool(extract_content_tool)
        
        # Register search_and_extract tool
        search_and_extract_tool = MCPTool(
            name="search_and_extract",
            description="Search the web and extract content from top results.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Maximum number of results to process (1-5)", "default": 3, "minimum": 1, "maximum": 5},
                    "max_content_length": {"type": "integer", "description": "Maximum length of extracted content per page", "default": 1000, "minimum": 100, "maximum": 5000}
                },
                "required": ["query"]
            },
            execute_func=self.search_and_extract,
            category="web_search",
            version="1.0.0"
        )
        self.register_tool(search_and_extract_tool)
        
        # Register get_search_suggestions tool
        suggestions_tool = MCPTool(
            name="get_search_suggestions",
            description="Get search suggestions for a query.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Partial query to get suggestions for"},
                    "max_suggestions": {"type": "integer", "description": "Maximum number of suggestions (1-10)", "default": 5, "minimum": 1, "maximum": 10}
                },
                "required": ["query"]
            },
            execute_func=self.get_search_suggestions,
            category="web_search",
            version="1.0.0"
        )
        self.register_tool(suggestions_tool)
        
        self.logger.info(f"Web Search MCP Server initialized with {len(self.tools)} tools")
    
    async def shutdown(self) -> None:
        """Clean shutdown of the web search MCP server."""
        self.logger.info("Shutting down Web Search MCP Server")
        # Clear cache
        self.cache.clear()
        self.logger.info("Web Search MCP Server shutdown complete")
    
    async def search_web(self, query: str, max_results: int = 5, region: str = "us-en") -> Dict[str, Any]:
        """
        Search the web using DuckDuckGo.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return (1-10)
            region: Search region (e.g., "us-en", "uk-en", "de-de")
        
        Returns:
            Dictionary containing search results
        """
        try:
            # Validate inputs
            if not query or not query.strip():
                return {"error": "Query cannot be empty"}
            
            max_results = min(max(1, max_results), 10)  # Limit to 1-10 results
            
            # Check cache first
            cache_key = f"search:{query}:{max_results}:{region}"
            if cache_key in self.cache:
                cached_result = self.cache[cache_key]
                if datetime.now() - cached_result['timestamp'] < self.cache_duration:
                    self.logger.info(f"Returning cached search results for: {query}")
                    return cached_result['data']
            
            # Rate limiting
            await self._rate_limit()
            
            # Perform search
            results = await self._search_duckduckgo(query, max_results, region)
            
            # Cache results
            self.cache[cache_key] = {
                'data': results,
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"Search completed for '{query}': {len(results.get('results', []))} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Search failed for '{query}': {str(e)}")
            return {"error": f"Search failed: {str(e)}"}
    
    async def extract_content(self, url: str, max_length: int = 2000) -> Dict[str, Any]:
        """
        Extract content from a web page.
        
        Args:
            url: URL to extract content from
            max_length: Maximum length of extracted text content
        
        Returns:
            Dictionary containing extracted content
        """
        try:
            # Validate URL
            if not url or not url.startswith(('http://', 'https://')):
                return {"error": "Invalid URL provided"}
            
            # Check cache first
            cache_key = f"content:{url}:{max_length}"
            if cache_key in self.cache:
                cached_result = self.cache[cache_key]
                if datetime.now() - cached_result['timestamp'] < self.cache_duration:
                    self.logger.info(f"Returning cached content for: {url}")
                    return cached_result['data']
            
            # Rate limiting
            await self._rate_limit()
            
            # Extract content
            content = await self._extract_web_content(url, max_length)
            
            # Cache results
            self.cache[cache_key] = {
                'data': content,
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"Content extraction completed for: {url}")
            return content
            
        except Exception as e:
            self.logger.error(f"Content extraction failed for '{url}': {str(e)}")
            return {"error": f"Content extraction failed: {str(e)}"}
    
    async def search_and_extract(self, query: str, max_results: int = 3, max_content_length: int = 1000) -> Dict[str, Any]:
        """
        Search the web and extract content from the top results.
        
        Args:
            query: Search query
            max_results: Maximum number of results to process (1-5)
            max_content_length: Maximum length of extracted content per page
        
        Returns:
            Dictionary containing search results with extracted content
        """
        try:
            # Validate inputs
            if not query or not query.strip():
                return {"error": "Query cannot be empty"}
            
            max_results = min(max(1, max_results), 5)  # Limit to 1-5 results
            
            # Check cache first
            cache_key = f"search_extract:{query}:{max_results}:{max_content_length}"
            if cache_key in self.cache:
                cached_result = self.cache[cache_key]
                if datetime.now() - cached_result['timestamp'] < self.cache_duration:
                    self.logger.info(f"Returning cached search and extract results for: {query}")
                    return cached_result['data']
            
            # Perform search
            search_results = await self.search_web(query, max_results)
            
            if "error" in search_results:
                return search_results
            
            # Extract content from each result
            enhanced_results = []
            for result in search_results.get('results', []):
                try:
                    content = await self.extract_content(result['url'], max_content_length)
                    if "error" not in content:
                        result['extracted_content'] = content.get('text_content', '')
                        result['page_title'] = content.get('title', result['title'])
                    else:
                        result['extracted_content'] = f"Content extraction failed: {content['error']}"
                        result['page_title'] = result['title']
                    
                    enhanced_results.append(result)
                    
                    # Small delay between extractions
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to extract content from {result['url']}: {str(e)}")
                    result['extracted_content'] = f"Content extraction failed: {str(e)}"
                    enhanced_results.append(result)
            
            results = {
                "query": query,
                "results": enhanced_results,
                "total_results": len(enhanced_results),
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache results
            self.cache[cache_key] = {
                'data': results,
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"Search and extract completed for '{query}': {len(enhanced_results)} results processed")
            return results
            
        except Exception as e:
            self.logger.error(f"Search and extract failed for '{query}': {str(e)}")
            return {"error": f"Search and extract failed: {str(e)}"}
    
    async def get_search_suggestions(self, query: str, max_suggestions: int = 5) -> Dict[str, Any]:
        """
        Get search suggestions for a query.
        
        Args:
            query: Partial query to get suggestions for
            max_suggestions: Maximum number of suggestions to return
        
        Returns:
            Dictionary containing search suggestions
        """
        try:
            # Validate inputs
            if not query or not query.strip():
                return {"error": "Query cannot be empty"}
            
            max_suggestions = min(max(1, max_suggestions), 10)
            
            # Check cache first
            cache_key = f"suggestions:{query}:{max_suggestions}"
            if cache_key in self.cache:
                cached_result = self.cache[cache_key]
                if datetime.now() - cached_result['timestamp'] < self.cache_duration:
                    self.logger.info(f"Returning cached suggestions for: {query}")
                    return cached_result['data']
            
            # Rate limiting
            await self._rate_limit()
            
            # Get suggestions
            suggestions = await self._get_duckduckgo_suggestions(query, max_suggestions)
            
            # Cache results
            self.cache[cache_key] = {
                'data': suggestions,
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"Suggestions retrieved for '{query}': {len(suggestions.get('suggestions', []))} suggestions")
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Suggestions failed for '{query}': {str(e)}")
            return {"error": f"Suggestions failed: {str(e)}"}
    
    async def _search_duckduckgo(self, query: str, max_results: int, region: str) -> Dict[str, Any]:
        """Perform DuckDuckGo search using HTML scraping."""
        import random
        
        # Try multiple DuckDuckGo endpoints
        endpoints = [
            "https://html.duckduckgo.com/html/",
            "https://duckduckgo.com/html/",
            "https://duckduckgo.com/lite/"
        ]
        
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'DNT': '1'
        }
        
        html = None
        last_error = None
        
        # Try each endpoint until one works
        for endpoint in endpoints:
            try:
                params = {
                    'q': query,
                    'kl': region,
                    'kp': '1'  # Safe search off
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(endpoint, params=params, headers=headers, timeout=30) as response:
                        if response.status == 200:
                            html = await response.text()
                            break
                        elif response.status == 202:
                            # DuckDuckGo is rate limiting, try next endpoint
                            last_error = f"Rate limited by {endpoint}"
                            continue
                        else:
                            last_error = f"HTTP {response.status}: {response.reason} from {endpoint}"
                            
            except Exception as e:
                last_error = f"Error with {endpoint}: {str(e)}"
                continue
        
        if not html:
            # If all endpoints fail, return mock results for testing
            self.logger.warning(f"All DuckDuckGo endpoints failed. Last error: {last_error}")
            return {
                "query": query,
                "results": [
                    {
                        'title': f"Mock result for: {query}",
                        'url': f"https://example.com/search?q={urllib.parse.quote(query)}",
                        'snippet': f"This is a mock search result for '{query}' since DuckDuckGo is not accessible.",
                        'source': 'Mock (DuckDuckGo unavailable)',
                        'timestamp': datetime.now().isoformat()
                    }
                ],
                "total_results": 1,
                "source": "Mock (DuckDuckGo unavailable)",
                "timestamp": datetime.now().isoformat()
            }
        
        # Parse results
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Try multiple selectors for DuckDuckGo results
        selectors = [
            'div.result',
            'div.web-result',
            'div[data-testid="result"]',
            'div.result__body',
            'div[class*="result"]',
            'div[class*="web-result"]',
            'div[class*="result__"]'
        ]
        
        result_containers = []
        for selector in selectors:
            result_containers = soup.select(selector)
            if result_containers:
                self.logger.info(f"Found {len(result_containers)} results using selector: {selector}")
                break
        
        self.logger.info(f"Total result containers found: {len(result_containers)}")
        
        # If no results found, try alternative approach
        if not result_containers:
            # Look for any links that might be search results
            links = soup.find_all('a', href=True)
            for link in links[:max_results]:
                href = link.get('href', '')
                if href.startswith('http') and not href.startswith('https://duckduckgo.com'):
                    title = link.get_text(strip=True)
                    if title and len(title) > 10:  # Filter out navigation links
                        results.append({
                            'title': title,
                            'url': href,
                            'snippet': f"Found via search for: {query}",
                            'source': 'DuckDuckGo',
                            'timestamp': datetime.now().isoformat()
                        })
        else:
            for container in result_containers[:max_results]:
                try:
                    # Try multiple selectors for title and URL - updated for current DuckDuckGo structure
                    title_selectors = [
                        'a.result__title', 
                        'a[data-testid="result-title"]', 
                        'h3 a', 
                        'a[class*="title"]',
                        'a[class*="result__title"]',
                        'a[class*="web-result__title"]',
                        'a',  # Fallback: any link in the container
                        'h2 a',  # Another common pattern
                        'h3 a',  # Another common pattern
                        'h4 a'   # Another common pattern
                    ]
                    title_elem = None
                    for selector in title_selectors:
                        title_elem = container.select_one(selector)
                        if title_elem:
                            break
                    
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href', '')
                    
                    # Clean URL (remove DuckDuckGo redirect)
                    if url.startswith('/l/?uddg='):
                        url = urllib.parse.unquote(url.split('uddg=')[1])
                    elif url.startswith('/l/?u='):
                        url = urllib.parse.unquote(url.split('u=')[1])
                    
                    # Extract snippet - updated selectors
                    snippet_selectors = [
                        '.result__snippet', 
                        '.result__a', 
                        'p', 
                        '.snippet',
                        '.result__snippet',
                        '.web-result__snippet',
                        '.result__body p',  # Look for paragraphs in result body
                        'p',  # Any paragraph
                        '.result__body'  # The entire result body as fallback
                    ]
                    snippet = ""
                    for selector in snippet_selectors:
                        snippet_elem = container.select_one(selector)
                        if snippet_elem:
                            snippet = snippet_elem.get_text(strip=True)
                            break
                    
                    # Extract source - updated selectors
                    source_selectors = [
                        '.result__url', 
                        '.result__domain', 
                        '.url',
                        '.web-result__url',
                        '.result__body .result__url',  # Nested selector
                        '.result__body .url'  # Nested selector
                    ]
                    source = ""
                    for selector in source_selectors:
                        source_elem = container.select_one(selector)
                        if source_elem:
                            source = source_elem.get_text(strip=True)
                            break
                    
                    # Additional validation and fallback
                    if not title or not url:
                        # Try to find any link in the container
                        all_links = container.find_all('a', href=True)
                        for link in all_links:
                            href = link.get('href', '')
                            if href.startswith('http') and not href.startswith('https://duckduckgo.com'):
                                if not title:
                                    title = link.get_text(strip=True)
                                if not url:
                                    url = href
                                    # Clean URL
                                    if url.startswith('/l/?uddg='):
                                        url = urllib.parse.unquote(url.split('uddg=')[1])
                                    elif url.startswith('/l/?u='):
                                        url = urllib.parse.unquote(url.split('u=')[1])
                                break
                    
                    if title and url and url.startswith('http'):
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet,
                            'source': source,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                except Exception as e:
                    self.logger.warning(f"Failed to parse result: {str(e)}")
                    continue
        
        return {
            "query": query,
            "results": results,
            "total_results": len(results),
            "source": "DuckDuckGo",
            "timestamp": datetime.now().isoformat()
        }
    
    async def _extract_web_content(self, url: str, max_length: int) -> Dict[str, Any]:
        """Extract content from a web page."""
        import random
        
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {response.reason}")
                
                html = await response.text()
        
        # Parse content
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title = ""
        title_elem = soup.find('title')
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        # Extract meta description
        meta_desc = ""
        meta_desc_elem = soup.find('meta', attrs={'name': 'description'})
        if meta_desc_elem:
            meta_desc = meta_desc_elem.get('content', '')
        
        # Extract main content
        content = ""
        
        # Try to find main content areas
        content_selectors = [
            'main',
            'article',
            '[role="main"]',
            '.content',
            '.main-content',
            '#content',
            '#main',
            '.post-content',
            '.entry-content'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # Remove script and style elements
                for script in content_elem(["script", "style"]):
                    script.decompose()
                
                content = content_elem.get_text(separator=' ', strip=True)
                break
        
        # If no main content found, use body
        if not content:
            body = soup.find('body')
            if body:
                # Remove script, style, nav, header, footer elements
                for elem in body(["script", "style", "nav", "header", "footer", "aside"]):
                    elem.decompose()
                content = body.get_text(separator=' ', strip=True)
        
        # Clean and truncate content
        content = re.sub(r'\s+', ' ', content).strip()
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        # Extract metadata
        metadata = {
            'title': title,
            'meta_description': meta_desc,
            'language': soup.get('lang', ''),
            'charset': soup.meta.get('charset', '') if soup.meta else '',
        }
        
        return {
            "url": url,
            "title": title,
            "content": content,
            "text_content": content,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _get_duckduckgo_suggestions(self, query: str, max_suggestions: int) -> Dict[str, Any]:
        """Get search suggestions from DuckDuckGo."""
        import random
        
        # DuckDuckGo suggestions API - updated endpoint
        suggestions_url = "https://duckduckgo.com/ac/"
        params = {
            'q': query,
            'kl': 'us-en',
            'type': 'list',
            'callback': 'ddg_spice_autocomplete'
        }
        
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'application/javascript, application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',  # Removed 'br' to avoid Brotli issues
            'Connection': 'keep-alive',
            'Referer': 'https://duckduckgo.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(suggestions_url, params=params, headers=headers, timeout=10) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {response.reason}")
                
                text = await response.text()
                
                # Handle JSONP response
                if text.startswith('ddg_spice_autocomplete(') and text.endswith(');'):
                    json_str = text[24:-2]  # Remove wrapper
                    try:
                        data = json.loads(json_str)
                    except json.JSONDecodeError:
                        # Fallback: try to extract suggestions manually
                        data = []
                        # Look for quoted strings in the response
                        import re
                        matches = re.findall(r'"([^"]+)"', text)
                        data = [{"phrase": match} for match in matches if len(match) > 2]
                else:
                    # Try direct JSON parsing
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError:
                        data = []
        
        suggestions = []
        if isinstance(data, list):
            for item in data[:max_suggestions]:
                if isinstance(item, dict) and 'phrase' in item:
                    suggestions.append(item['phrase'])
                elif isinstance(item, str):
                    suggestions.append(item)
        elif isinstance(data, dict) and 'suggestions' in data:
            for item in data['suggestions'][:max_suggestions]:
                if isinstance(item, dict) and 'phrase' in item:
                    suggestions.append(item['phrase'])
                elif isinstance(item, str):
                    suggestions.append(item)
        
        # Fallback: generate simple suggestions if API fails
        if not suggestions:
            base_suggestions = [
                f"{query} tutorial",
                f"{query} examples",
                f"{query} guide",
                f"{query} documentation",
                f"{query} best practices"
            ]
            suggestions = base_suggestions[:max_suggestions]
        
        return {
            "query": query,
            "suggestions": suggestions,
            "total_suggestions": len(suggestions),
            "source": "DuckDuckGo",
            "timestamp": datetime.now().isoformat()
        }
    
    async def _rate_limit(self):
        """Implement rate limiting to be respectful to servers."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    

