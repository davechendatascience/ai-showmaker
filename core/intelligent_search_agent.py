#!/usr/bin/env python3
"""
Intelligent Search Agent

This module provides an enhanced agent that automatically detects when web search
is needed and integrates it seamlessly into the workflow.
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from core.intelligent_reliable_agent import IntelligentReliableAIShowmakerAgent
from core.config import ConfigManager


@dataclass
class SearchIntent:
    """Represents a detected search intent."""
    query: str
    intent_type: str  # 'debugging', 'research', 'comparison', 'current_events', 'documentation'
    confidence: float
    suggested_queries: List[str]
    context: Dict[str, Any]


class IntelligentSearchAgent:
    """
    Enhanced agent that automatically detects when web search is needed.
    """
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.agent = None
        self.logger = logging.getLogger("ai_showmaker.intelligent_search")
        
        # Search intent patterns
        self.search_patterns = {
            'debugging': [
                r'error\s+(?:message|code|occurred)',
                r'exception\s+(?:thrown|raised)',
                r'failed\s+to\s+(?:start|run|execute)',
                r'stack\s+trace',
                r'segmentation\s+fault',
                r'null\s+pointer',
                r'undefined\s+(?:variable|function)',
                r'import\s+error',
                r'module\s+not\s+found',
                r'permission\s+denied',
                r'connection\s+(?:refused|timeout)',
                r'file\s+not\s+found',
                r'syntax\s+error',
                r'type\s+error',
                r'attribute\s+error'
            ],
            'research': [
                r'what\s+is\s+(\w+)',
                r'how\s+to\s+(\w+)',
                r'best\s+practices\s+for',
                r'latest\s+(?:developments|trends)',
                r'current\s+(?:state|status)',
                r'recent\s+(?:changes|updates)',
                r'new\s+(?:features|capabilities)',
                r'future\s+(?:plans|roadmap)'
            ],
            'comparison': [
                r'compare\s+(\w+)\s+vs?\s+(\w+)',
                r'(\w+)\s+vs?\s+(\w+)',
                r'difference\s+between\s+(\w+)\s+and\s+(\w+)',
                r'which\s+is\s+better\s+(\w+)\s+or\s+(\w+)',
                r'pros\s+and\s+cons\s+of',
                r'advantages\s+and\s+disadvantages'
            ],
            'current_events': [
                r'latest\s+news',
                r'recent\s+announcements',
                r'what\s+happened\s+(?:today|this\s+week)',
                r'breaking\s+news',
                r'latest\s+release',
                r'new\s+version\s+of'
            ],
            'documentation': [
                r'api\s+documentation',
                r'how\s+to\s+use\s+(\w+)',
                r'(\w+)\s+documentation',
                r'installation\s+guide',
                r'setup\s+instructions',
                r'configuration\s+guide'
            ]
        }
        
        # Knowledge cutoff date (approximate)
        self.knowledge_cutoff = "2023-12-31"
        
    async def initialize(self):
        """Initialize the intelligent search agent."""
        self.agent = IntelligentReliableAIShowmakerAgent(self.config)
        await self.agent.initialize()
        self.logger.info("IntelligentSearchAgent initialized")
    
    def detect_search_intent(self, query: str) -> Optional[SearchIntent]:
        """
        Automatically detect if a query requires web search.
        """
        query_lower = query.lower()
        
        # Check for explicit search requests
        if any(phrase in query_lower for phrase in [
            'search the web', 'search for', 'find information about',
            'look up', 'research', 'google', 'search online'
        ]):
            return SearchIntent(
                query=query,
                intent_type='explicit_search',
                confidence=1.0,
                suggested_queries=[query],
                context={'explicit_request': True}
            )
        
        # Check for time-sensitive information
        current_year = datetime.now().year
        if any(year in query for year in [str(current_year), 'latest', 'recent', 'new']):
            return SearchIntent(
                query=query,
                intent_type='current_events',
                confidence=0.8,
                suggested_queries=[f"{query} {current_year}"],
                context={'time_sensitive': True, 'year': current_year}
            )
        
        # Check for debugging patterns
        for intent_type, patterns in self.search_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    suggested_queries = self._generate_search_queries(query, intent_type)
                    return SearchIntent(
                        query=query,
                        intent_type=intent_type,
                        confidence=0.7,
                        suggested_queries=suggested_queries,
                        context={'pattern_matched': pattern, 'intent_type': intent_type}
                    )
        
        # Check for knowledge gaps
        if self._has_potential_knowledge_gap(query):
            return SearchIntent(
                query=query,
                intent_type='knowledge_gap',
                confidence=0.6,
                suggested_queries=[query],
                context={'potential_gap': True}
            )
        
        return None
    
    def _generate_search_queries(self, original_query: str, intent_type: str) -> List[str]:
        """Generate optimized search queries based on intent type."""
        queries = []
        
        if intent_type == 'debugging':
            # Extract error messages and technical terms
            error_patterns = [
                r'error[:\s]+([^.!?]+)',
                r'exception[:\s]+([^.!?]+)',
                r'failed[:\s]+([^.!?]+)',
                r'(\w+Exception)',
                r'(\w+Error)'
            ]
            
            for pattern in error_patterns:
                matches = re.findall(pattern, original_query, re.IGNORECASE)
                for match in matches:
                    queries.append(f'"{match}" stackoverflow')
                    queries.append(f'"{match}" error solution')
                    queries.append(f'"{match}" troubleshooting')
        
        elif intent_type == 'comparison':
            # Extract comparison terms
            comparison_patterns = [
                r'compare\s+(\w+)\s+vs?\s+(\w+)',
                r'(\w+)\s+vs?\s+(\w+)',
                r'difference\s+between\s+(\w+)\s+and\s+(\w+)'
            ]
            
            for pattern in comparison_patterns:
                matches = re.findall(pattern, original_query, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        queries.append(f'"{match[0]}" vs "{match[1]}" comparison')
                        queries.append(f'"{match[0]}" vs "{match[1]}" pros cons')
                    else:
                        queries.append(f'"{match}" comparison')
        
        elif intent_type == 'research':
            # Extract research topics
            research_patterns = [
                r'what\s+is\s+(\w+)',
                r'how\s+to\s+(\w+)',
                r'best\s+practices\s+for\s+(\w+)'
            ]
            
            for pattern in research_patterns:
                matches = re.findall(pattern, original_query, re.IGNORECASE)
                for match in matches:
                    queries.append(f'"{match}" guide tutorial')
                    queries.append(f'"{match}" best practices')
                    queries.append(f'"{match}" documentation')
        
        # Add the original query as fallback
        if not queries:
            queries.append(original_query)
        
        return queries[:5]  # Limit to 5 queries
    
    def _has_potential_knowledge_gap(self, query: str) -> bool:
        """Check if query might require information beyond training data."""
        current_year = datetime.now().year
        
        # Check for recent years
        if str(current_year) in query or str(current_year - 1) in query:
            return True
        
        # Check for current technology terms
        current_tech_terms = [
            'gpt-4', 'claude', 'llama', 'mistral', 'gemini',
            'react 19', 'vue 4', 'angular 17', 'python 3.12',
            'docker compose', 'kubernetes', 'terraform',
            'next.js 14', 'nuxt 3', 'sveltekit'
        ]
        
        if any(term in query.lower() for term in current_tech_terms):
            return True
        
        # Check for current events indicators
        current_indicators = [
            'latest', 'recent', 'new', 'updated', 'current',
            'announced', 'released', 'launched', 'introduced'
        ]
        
        if any(indicator in query.lower() for indicator in current_indicators):
            return True
        
        return False
    
    async def query_with_intelligent_search(self, query: str) -> str:
        """
        Query the agent with automatic search detection and integration.
        """
        # First, detect if search is needed
        search_intent = self.detect_search_intent(query)
        
        if search_intent:
            self.logger.info(f"Detected search intent: {search_intent.intent_type} (confidence: {search_intent.confidence})")
            
            # Perform web search
            search_results = await self._perform_intelligent_search(search_intent)
            
            # Combine search results with original query
            enhanced_query = self._create_enhanced_query(query, search_results, search_intent)
            
            # Query the agent with enhanced context
            result = await self.agent.query(enhanced_query)
            
            return self._format_result_with_sources(result, search_results, search_intent)
        else:
            # No search needed, proceed normally
            return await self.agent.query(query)
    
    async def _perform_intelligent_search(self, search_intent: SearchIntent) -> Dict[str, Any]:
        """Perform intelligent web search based on detected intent."""
        search_results = {
            'intent': search_intent.intent_type,
            'queries_executed': [],
            'results': [],
            'sources': []
        }
        
        for query in search_intent.suggested_queries[:3]:  # Limit to 3 queries
            try:
                self.logger.info(f"Executing search query: {query}")
                
                # Use the web search tool
                search_result = await self.agent.query(f"Search the web for: {query}")
                
                if search_result and "Error:" not in search_result:
                    search_results['queries_executed'].append(query)
                    search_results['results'].append({
                        'query': query,
                        'result': search_result,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # Extract sources if available
                    if 'source:' in search_result.lower():
                        sources = re.findall(r'source:\s*([^\n]+)', search_result, re.IGNORECASE)
                        search_results['sources'].extend(sources)
                
            except Exception as e:
                self.logger.error(f"Search query failed: {query} - {str(e)}")
        
        return search_results
    
    def _create_enhanced_query(self, original_query: str, search_results: Dict[str, Any], search_intent: SearchIntent) -> str:
        """Create an enhanced query that includes search results."""
        if not search_results['results']:
            return original_query
        
        # Build context from search results
        context_parts = []
        
        if search_intent.intent_type == 'debugging':
            context_parts.append("Based on recent web search results for similar issues:")
        elif search_intent.intent_type == 'comparison':
            context_parts.append("Based on current web research comparing the technologies:")
        elif search_intent.intent_type == 'research':
            context_parts.append("Based on current web research about this topic:")
        else:
            context_parts.append("Based on recent web search results:")
        
        # Add search results
        for result in search_results['results']:
            context_parts.append(f"Search: {result['query']}")
            context_parts.append(f"Result: {result['result'][:500]}...")  # Limit length
        
        context = "\n".join(context_parts)
        
        enhanced_query = f"""
{context}

Now, please answer the original question: {original_query}

Provide a comprehensive answer that incorporates the search results above.
"""
        
        return enhanced_query
    
    def _format_result_with_sources(self, result: str, search_results: Dict[str, Any], search_intent: SearchIntent) -> str:
        """Format the result to include source information."""
        if not search_results['sources']:
            return result
        
        # Add source information
        sources_section = "\n\n---\n**Sources:**\n"
        for i, source in enumerate(set(search_results['sources']), 1):
            sources_section += f"{i}. {source}\n"
        
        # Add search context
        context_note = f"\n*This answer incorporates web search results for {search_intent.intent_type} intent.*"
        
        return result + context_note + sources_section
    
    async def shutdown(self):
        """Shutdown the agent."""
        if self.agent:
            await self.agent.shutdown()


# Example usage and testing
async def test_intelligent_search():
    """Test the intelligent search functionality."""
    print("🧠 Testing Intelligent Search Agent")
    print("=" * 50)
    
    config = ConfigManager()
    agent = IntelligentSearchAgent(config)
    
    try:
        await agent.initialize()
        
        # Test cases
        test_queries = [
            "How do I fix 'ModuleNotFoundError: No module named requests'?",
            "Compare React vs Vue.js for a new project",
            "What are the latest developments in AI in 2024?",
            "How to install Python 3.12 on Ubuntu?",
            "What is the current status of Docker Compose?",
            "Simple calculation: 2 + 2 = ?"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Query: {query}")
            
            # Detect search intent
            search_intent = agent.detect_search_intent(query)
            
            if search_intent:
                print(f"✅ Search intent detected: {search_intent.intent_type}")
                print(f"   Confidence: {search_intent.confidence}")
                print(f"   Suggested queries: {search_intent.suggested_queries[:2]}")
                
                # Perform intelligent search
                result = await agent.query_with_intelligent_search(query)
                print(f"📝 Result preview: {result[:200]}...")
            else:
                print("❌ No search intent detected")
                result = await agent.agent.query(query)
                print(f"📝 Direct result: {result[:200]}...")
        
        print(f"\n🎉 Intelligent search testing completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
    
    finally:
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(test_intelligent_search())
