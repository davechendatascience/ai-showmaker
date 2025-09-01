#!/usr/bin/env python3
"""
Web Search Integration Demo

This demo shows how to use web search in real-world tasks and integrate
the results into the model's working memory for intelligent decision making.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our components
from core.intelligent_reliable_agent import IntelligentReliableAIShowmakerAgent
from core.config import ConfigManager


class WebSearchTaskExecutor:
    """
    Demonstrates web search integration with intelligent task planning.
    """
    
    def __init__(self):
        self.agent = None
        self.working_memory = {
            'research_results': [],
            'current_context': {},
            'task_progress': {},
            'web_search_history': []
        }
    
    async def initialize(self):
        """Initialize the agent with web search capabilities."""
        print("🚀 Initializing Web Search Task Executor...")
        
        config = ConfigManager()
        self.agent = IntelligentReliableAIShowmakerAgent(config)
        await self.agent.initialize()
        
        print("✅ Agent initialized with web search capabilities")
        print(f"📊 Available tools: {len(self.agent.get_tools_info())}")
    
    def update_working_memory(self, key: str, data: Any, source: str = "web_search"):
        """Update the model's working memory with new information."""
        timestamp = datetime.now().isoformat()
        
        if key not in self.working_memory:
            self.working_memory[key] = []
        
        memory_entry = {
            'data': data,
            'source': source,
            'timestamp': timestamp,
            'context': self.working_memory['current_context'].copy()
        }
        
        self.working_memory[key].append(memory_entry)
        
        # Keep only the last 10 entries to prevent memory overflow
        if len(self.working_memory[key]) > 10:
            self.working_memory[key] = self.working_memory[key][-10:]
        
        logger.info(f"📝 Updated working memory: {key} with {len(str(data))} chars from {source}")
    
    async def research_task(self, topic: str, research_questions: List[str]) -> Dict[str, Any]:
        """
        Perform comprehensive research using web search and integrate results.
        """
        print(f"\n🔍 Research Task: {topic}")
        print("=" * 60)
        
        research_results = {
            'topic': topic,
            'questions': research_questions,
            'findings': {},
            'sources': [],
            'recommendations': []
        }
        
        # Update working memory with research context
        self.working_memory['current_context'] = {
            'task_type': 'research',
            'topic': topic,
            'questions': research_questions,
            'start_time': datetime.now().isoformat()
        }
        
        for i, question in enumerate(research_questions, 1):
            print(f"\n📋 Research Question {i}: {question}")
            
            # Construct search query
            search_query = f"{topic} {question}"
            
            try:
                # Perform web search
                print(f"🔍 Searching for: {search_query}")
                search_result = await self.agent.query(f"Search the web for: {search_query}")
                
                # Extract and process results
                if search_result and "Error:" not in search_result:
                    # Update working memory with search results
                    self.update_working_memory('research_results', {
                        'question': question,
                        'search_query': search_query,
                        'result': search_result
                    })
                    
                    research_results['findings'][question] = search_result
                    research_results['sources'].append({
                        'query': search_query,
                        'result_preview': search_result[:200] + "..." if len(search_result) > 200 else search_result
                    })
                    
                    print(f"✅ Found information for question {i}")
                else:
                    print(f"⚠️  No results found for question {i}")
                    
            except Exception as e:
                logger.error(f"Error researching question {i}: {str(e)}")
                print(f"❌ Error researching question {i}: {str(e)}")
        
        # Generate recommendations based on research
        print(f"\n🤖 Generating recommendations based on research...")
        try:
            recommendations_query = f"""
            Based on the research about {topic}, provide 3 actionable recommendations.
            Consider the findings from the web search results.
            """
            
            recommendations = await self.agent.query(recommendations_query)
            research_results['recommendations'] = recommendations
            
            # Update working memory with final recommendations
            self.update_working_memory('recommendations', {
                'topic': topic,
                'recommendations': recommendations,
                'research_summary': research_results
            })
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            research_results['recommendations'] = "Error generating recommendations"
        
        return research_results
    
    async def technology_comparison_task(self, technologies: List[str]) -> Dict[str, Any]:
        """
        Compare multiple technologies using web search and provide insights.
        """
        print(f"\n⚖️  Technology Comparison Task")
        print("=" * 60)
        print(f"Comparing: {', '.join(technologies)}")
        
        comparison_results = {
            'technologies': technologies,
            'comparisons': {},
            'pros_cons': {},
            'recommendation': None
        }
        
        # Update working memory
        self.working_memory['current_context'] = {
            'task_type': 'technology_comparison',
            'technologies': technologies,
            'start_time': datetime.now().isoformat()
        }
        
        for tech in technologies:
            print(f"\n🔍 Researching {tech}...")
            
            try:
                # Search for pros and cons
                pros_cons_query = f"Search for pros and cons of {tech} technology"
                pros_cons_result = await self.agent.query(pros_cons_query)
                
                # Search for current trends
                trends_query = f"Search for current trends and popularity of {tech} in 2024"
                trends_result = await self.agent.query(trends_query)
                
                comparison_results['comparisons'][tech] = {
                    'pros_cons': pros_cons_result,
                    'trends': trends_result
                }
                
                # Update working memory
                self.update_working_memory('tech_research', {
                    'technology': tech,
                    'pros_cons': pros_cons_result,
                    'trends': trends_result
                })
                
                print(f"✅ Completed research for {tech}")
                
            except Exception as e:
                logger.error(f"Error researching {tech}: {str(e)}")
                print(f"❌ Error researching {tech}: {str(e)}")
        
        # Generate final recommendation
        print(f"\n🤖 Generating final recommendation...")
        try:
            recommendation_query = f"""
            Based on the research about {', '.join(technologies)}, 
            provide a detailed recommendation on which technology to choose.
            Consider pros, cons, trends, and current market position.
            """
            
            recommendation = await self.agent.query(recommendation_query)
            comparison_results['recommendation'] = recommendation
            
            # Update working memory with final recommendation
            self.update_working_memory('final_recommendation', {
                'technologies': technologies,
                'recommendation': recommendation,
                'comparison_summary': comparison_results
            })
            
        except Exception as e:
            logger.error(f"Error generating recommendation: {str(e)}")
            comparison_results['recommendation'] = "Error generating recommendation"
        
        return comparison_results
    
    async def market_analysis_task(self, industry: str, company: str = None) -> Dict[str, Any]:
        """
        Perform market analysis using web search and integrate findings.
        """
        print(f"\n📊 Market Analysis Task: {industry}")
        if company:
            print(f"Focus company: {company}")
        print("=" * 60)
        
        analysis_results = {
            'industry': industry,
            'company': company,
            'market_size': None,
            'key_players': [],
            'trends': [],
            'opportunities': [],
            'risks': []
        }
        
        # Update working memory
        self.working_memory['current_context'] = {
            'task_type': 'market_analysis',
            'industry': industry,
            'company': company,
            'start_time': datetime.now().isoformat()
        }
        
        # Research market size
        print(f"🔍 Researching market size for {industry}...")
        try:
            market_size_query = f"Search for current market size and growth of {industry} industry"
            market_size_result = await self.agent.query(market_size_query)
            analysis_results['market_size'] = market_size_result
            
            self.update_working_memory('market_research', {
                'aspect': 'market_size',
                'industry': industry,
                'data': market_size_result
            })
            
        except Exception as e:
            logger.error(f"Error researching market size: {str(e)}")
        
        # Research key players
        print(f"🔍 Researching key players in {industry}...")
        try:
            players_query = f"Search for top companies and key players in {industry} industry"
            players_result = await self.agent.query(players_query)
            analysis_results['key_players'] = players_result
            
            self.update_working_memory('market_research', {
                'aspect': 'key_players',
                'industry': industry,
                'data': players_result
            })
            
        except Exception as e:
            logger.error(f"Error researching key players: {str(e)}")
        
        # Research trends
        print(f"🔍 Researching current trends in {industry}...")
        try:
            trends_query = f"Search for current trends and innovations in {industry} industry 2024"
            trends_result = await self.agent.query(trends_query)
            analysis_results['trends'] = trends_result
            
            self.update_working_memory('market_research', {
                'aspect': 'trends',
                'industry': industry,
                'data': trends_result
            })
            
        except Exception as e:
            logger.error(f"Error researching trends: {str(e)}")
        
        # Generate strategic insights
        print(f"\n🤖 Generating strategic insights...")
        try:
            insights_query = f"""
            Based on the market analysis of {industry}, provide:
            1. Key opportunities for new entrants or existing players
            2. Potential risks and challenges
            3. Strategic recommendations
            """
            
            insights_result = await self.agent.query(insights_query)
            analysis_results['opportunities'] = insights_result
            analysis_results['risks'] = insights_result
            
            # Update working memory with final analysis
            self.update_working_memory('market_analysis', {
                'industry': industry,
                'company': company,
                'insights': insights_result,
                'analysis_summary': analysis_results
            })
            
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
        
        return analysis_results
    
    def get_working_memory_summary(self) -> Dict[str, Any]:
        """Get a summary of the current working memory."""
        summary = {
            'total_entries': sum(len(entries) for entries in self.working_memory.values() if isinstance(entries, list)),
            'memory_keys': list(self.working_memory.keys()),
            'current_context': self.working_memory.get('current_context', {}),
            'recent_activities': []
        }
        
        # Get recent activities from all memory entries
        for key, entries in self.working_memory.items():
            if isinstance(entries, list) and entries:
                latest_entry = entries[-1]
                summary['recent_activities'].append({
                    'key': key,
                    'source': latest_entry.get('source', 'unknown'),
                    'timestamp': latest_entry.get('timestamp', 'unknown'),
                    'data_preview': str(latest_entry.get('data', ''))[:100] + "..." if len(str(latest_entry.get('data', ''))) > 100 else str(latest_entry.get('data', ''))
                })
        
        return summary
    
    async def shutdown(self):
        """Shutdown the agent."""
        if self.agent:
            await self.agent.shutdown()


async def main():
    """Main demo function."""
    print("🌐 Web Search Integration Demo")
    print("=" * 60)
    print("This demo shows how web search integrates with intelligent task planning")
    print("and how results are stored in the model's working memory.")
    print("=" * 60)
    
    executor = WebSearchTaskExecutor()
    
    try:
        await executor.initialize()
        
        # Demo 1: Research Task
        print("\n🎯 Demo 1: Research Task")
        research_questions = [
            "What are the latest developments?",
            "What are the main challenges?",
            "What are the future prospects?"
        ]
        
        research_results = await executor.research_task(
            "artificial intelligence in healthcare",
            research_questions
        )
        
        print(f"\n📋 Research Summary:")
        print(f"Topic: {research_results['topic']}")
        print(f"Questions researched: {len(research_results['questions'])}")
        print(f"Findings collected: {len(research_results['findings'])}")
        print(f"Sources consulted: {len(research_results['sources'])}")
        
        # Demo 2: Technology Comparison
        print("\n🎯 Demo 2: Technology Comparison")
        technologies = ["React", "Vue.js", "Angular"]
        
        comparison_results = await executor.technology_comparison_task(technologies)
        
        print(f"\n📋 Comparison Summary:")
        print(f"Technologies compared: {len(comparison_results['technologies'])}")
        print(f"Comparisons completed: {len(comparison_results['comparisons'])}")
        print(f"Recommendation generated: {'Yes' if comparison_results['recommendation'] else 'No'}")
        
        # Demo 3: Market Analysis
        print("\n🎯 Demo 3: Market Analysis")
        market_results = await executor.market_analysis_task("electric vehicles")
        
        print(f"\n📋 Market Analysis Summary:")
        print(f"Industry analyzed: {market_results['industry']}")
        print(f"Market size researched: {'Yes' if market_results['market_size'] else 'No'}")
        print(f"Key players identified: {'Yes' if market_results['key_players'] else 'No'}")
        print(f"Trends analyzed: {'Yes' if market_results['trends'] else 'No'}")
        
        # Show working memory summary
        print(f"\n🧠 Working Memory Summary:")
        memory_summary = executor.get_working_memory_summary()
        print(f"Total memory entries: {memory_summary['total_entries']}")
        print(f"Memory keys: {', '.join(memory_summary['memory_keys'])}")
        print(f"Current context: {memory_summary['current_context'].get('task_type', 'None')}")
        
        print(f"\n📝 Recent Activities:")
        for activity in memory_summary['recent_activities'][-5:]:  # Show last 5 activities
            print(f"  • {activity['key']} ({activity['source']}) - {activity['timestamp']}")
            print(f"    {activity['data_preview']}")
        
        print(f"\n🎉 Demo completed successfully!")
        print(f"✅ Web search integration working")
        print(f"✅ Working memory updated with research results")
        print(f"✅ Intelligent task planning with web search data")
        
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")
        print(f"❌ Demo failed: {str(e)}")
    
    finally:
        await executor.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
