"""
Capability-Based Tool Discovery for MCP-Zero

This module enhances the existing MCP-Zero system with capability-based
tool discovery, allowing agents to find tools by what they can do rather
than just by name.
"""

import re
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class ToolCategory(Enum):
    """Standard tool categories for classification."""
    MATHEMATICS = "mathematics"
    STATISTICS = "statistics"
    LINEAR_ALGEBRA = "linear_algebra"
    CALCULUS = "calculus"
    NUMBER_THEORY = "number_theory"
    DATA_PROCESSING = "data_processing"
    FILE_OPERATIONS = "file_operations"
    NETWORK = "network"
    DATABASE = "database"
    AI_ML = "ai_ml"
    UTILITIES = "utilities"
    UNKNOWN = "unknown"


@dataclass
class ToolCapability:
    """Represents a tool's capabilities and metadata."""
    name: str
    description: str
    category: ToolCategory
    tags: Set[str]
    parameters: Dict[str, Any]
    examples: List[str]
    complexity: str  # "simple", "moderate", "advanced"
    input_types: List[str]
    output_types: List[str]
    
    def to_searchable_text(self) -> str:
        """Convert capability to searchable text for semantic search."""
        text_parts = [
            self.name,
            self.description,
            self.category.value,
            " ".join(self.tags),
            " ".join(self.input_types),
            " ".join(self.output_types),
            self.complexity
        ]
        return " ".join(text_parts).lower()


class CapabilityDiscoveryEngine:
    """
    Enhanced discovery engine that finds tools by capabilities.
    
    This extends the existing MCP-Zero system with semantic search
    and capability-based filtering.
    """
    
    def __init__(self):
        self.tool_capabilities: Dict[str, ToolCapability] = {}
        self.category_index: Dict[ToolCategory, Set[str]] = {}
        self.tag_index: Dict[str, Set[str]] = {}
        
    def register_tool_capability(self, tool_name: str, capability: ToolCapability) -> None:
        """Register a tool's capabilities for discovery."""
        self.tool_capabilities[tool_name] = capability
        
        # Update category index
        if capability.category not in self.category_index:
            self.category_index[capability.category] = set()
        self.category_index[capability.category].add(tool_name)
        
        # Update tag index
        for tag in capability.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(tool_name)
    
    def discover_by_category(self, category: ToolCategory) -> List[str]:
        """Find tools by category."""
        return list(self.category_index.get(category, set()))
    
    def discover_by_tags(self, tags: List[str]) -> List[str]:
        """Find tools that have any of the specified tags."""
        matching_tools = set()
        for tag in tags:
            if tag in self.tag_index:
                matching_tools.update(self.tag_index[tag])
        return list(matching_tools)
    
    def discover_by_capability(self, query: str) -> List[Tuple[str, float]]:
        """
        Find tools by capability using semantic search.
        
        Args:
            query: Natural language description of what the agent needs
            
        Returns:
            List of (tool_name, relevance_score) tuples
        """
        query_lower = query.lower()
        results = []
        
        for tool_name, capability in self.tool_capabilities.items():
            score = self._calculate_relevance(query_lower, capability)
            if score > 0:
                results.append((tool_name, score))
        
        # Sort by relevance score (highest first)
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def discover_by_input_output(self, input_types: List[str], output_types: List[str]) -> List[str]:
        """Find tools that can handle specific input/output types."""
        matching_tools = []
        
        for tool_name, capability in self.tool_capabilities.items():
            if (any(input_type in capability.input_types for input_type in input_types) and
                any(output_type in capability.output_types for output_type in output_types)):
                matching_tools.append(tool_name)
        
        return matching_tools
    
    def get_tool_suggestions(self, context: str) -> List[str]:
        """
        Get intelligent tool suggestions based on context.
        
        Args:
            context: Description of what the agent is trying to accomplish
            
        Returns:
            List of suggested tool names
        """
        # Extract key concepts from context
        context_lower = context.lower()
        
        # Look for mathematical operations
        math_keywords = ["calculate", "solve", "compute", "math", "equation", "formula"]
        if any(keyword in context_lower for keyword in math_keywords):
            return self.discover_by_category(ToolCategory.MATHEMATICS)
        
        # Look for statistical analysis
        stats_keywords = ["analyze", "statistics", "data", "mean", "median", "distribution"]
        if any(keyword in context_lower for keyword in stats_keywords):
            return self.discover_by_category(ToolCategory.STATISTICS)
        
        # Look for matrix operations
        matrix_keywords = ["matrix", "determinant", "eigenvalue", "linear algebra"]
        if any(keyword in context_lower for keyword in matrix_keywords):
            return self.discover_by_category(ToolCategory.LINEAR_ALGEBRA)
        
        # Look for integration/differentiation
        calc_keywords = ["integrate", "differentiate", "derivative", "calculus"]
        if any(keyword in context_lower for keyword in calc_keywords):
            return self.discover_by_category(ToolCategory.CALCULUS)
        
        # Default to general search
        results = self.discover_by_capability(context)
        return [tool_name for tool_name, _ in results[:5]]
    
    def _calculate_relevance(self, query: str, capability: ToolCapability) -> float:
        """
        Calculate relevance score between query and tool capability.
        
        This is a simple but effective scoring algorithm. In production,
        you might use embeddings or more sophisticated NLP.
        """
        score = 0.0
        searchable_text = capability.to_searchable_text()
        
        # Exact matches get high scores
        if query in capability.name.lower():
            score += 10.0
        if query in capability.description.lower():
            score += 8.0
        
        # Category matches
        if query in capability.category.value:
            score += 5.0
        
        # Tag matches
        for tag in capability.tags:
            if query in tag.lower():
                score += 3.0
        
        # Word overlap
        query_words = set(query.split())
        text_words = set(searchable_text.split())
        overlap = len(query_words.intersection(text_words))
        score += overlap * 1.0
        
        # Complexity matching
        if "simple" in query and capability.complexity == "simple":
            score += 2.0
        elif "advanced" in query and capability.complexity == "advanced":
            score += 2.0
        
        return score
    
    def get_capability_summary(self) -> Dict[str, Any]:
        """Get a summary of all available capabilities."""
        summary = {
            "total_tools": len(self.tool_capabilities),
            "categories": {},
            "tags": {},
            "complexity_distribution": {"simple": 0, "moderate": 0, "advanced": 0}
        }
        
        # Category distribution
        for category in ToolCategory:
            tools = self.category_index.get(category, set())
            summary["categories"][category.value] = len(tools)
        
        # Tag distribution
        for tag, tools in self.tag_index.items():
            summary["tags"][tag] = len(tools)
        
        # Complexity distribution
        for capability in self.tool_capabilities.values():
            summary["complexity_distribution"][capability.complexity] += 1
        
        return summary


class CapabilityExtractor:
    """Extracts capabilities from MCP tools automatically."""
    
    @staticmethod
    def extract_from_tool(tool_name: str, tool_data: Dict[str, Any]) -> ToolCapability:
        """Extract capabilities from an MCP tool definition."""
        description = tool_data.get("description", "")
        parameters = tool_data.get("parameters", {})
        category = tool_data.get("category", "utilities")
        
        # Extract tags from description and parameters
        tags = CapabilityExtractor._extract_tags(description, parameters)
        
        # Determine complexity based on description and parameters
        complexity = CapabilityExtractor._determine_complexity(description, parameters)
        
        # Extract input/output types from parameters
        input_types, output_types = CapabilityExtractor._extract_types(parameters)
        
        # Generate examples based on tool type
        examples = CapabilityExtractor._generate_examples(tool_name, description, parameters)
        
        return ToolCapability(
            name=tool_name,
            description=description,
            category=CapabilityExtractor._map_category(category),
            tags=tags,
            parameters=parameters,
            examples=examples,
            complexity=complexity,
            input_types=input_types,
            output_types=output_types
        )
    
    @staticmethod
    def _extract_tags(description: str, parameters: Dict[str, Any]) -> Set[str]:
        """Extract relevant tags from tool description and parameters."""
        tags = set()
        
        # Common mathematical tags
        math_tags = ["math", "mathematics", "calculate", "compute", "solve"]
        for tag in math_tags:
            if tag in description.lower():
                tags.add(tag)
        
        # Statistical tags
        stats_tags = ["statistics", "analysis", "data", "mean", "median", "variance"]
        for tag in stats_tags:
            if tag in description.lower():
                tags.add(tag)
        
        # Matrix tags
        matrix_tags = ["matrix", "linear algebra", "determinant", "eigenvalue"]
        for tag in matrix_tags:
            if tag in description.lower():
                tags.add(tag)
        
        # Integration tags
        calc_tags = ["integration", "differentiation", "calculus", "derivative"]
        for tag in calc_tags:
            if tag in description.lower():
                tags.add(tag)
        
        # Parameter-based tags
        if "array" in str(parameters).lower():
            tags.add("array_processing")
        if "file" in str(parameters).lower():
            tags.add("file_operations")
        if "network" in str(parameters).lower():
            tags.add("network")
        
        return tags
    
    @staticmethod
    def _determine_complexity(description: str, parameters: Dict[str, Any]) -> str:
        """Determine tool complexity based on description and parameters."""
        description_lower = description.lower()
        
        # Simple tools
        simple_indicators = ["simple", "basic", "hello", "status"]
        if any(indicator in description_lower for indicator in simple_indicators):
            return "simple"
        
        # Advanced tools
        advanced_indicators = ["advanced", "complex", "integration", "eigenvalue", "statistics"]
        if any(indicator in description_lower for indicator in advanced_indicators):
            return "advanced"
        
        # Default to moderate
        return "moderate"
    
    @staticmethod
    def _extract_types(parameters: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Extract input and output types from parameters."""
        input_types = []
        output_types = []
        
        # Analyze parameter types
        if "properties" in parameters:
            for prop_name, prop_info in parameters["properties"].items():
                prop_type = prop_info.get("type", "unknown")
                if prop_type == "array":
                    input_types.append("array")
                elif prop_type == "string":
                    input_types.append("string")
                elif prop_type == "number":
                    input_types.append("number")
                elif prop_type == "integer":
                    input_types.append("integer")
                elif prop_type == "boolean":
                    input_types.append("boolean")
        
        # Default output types based on common patterns
        output_types = ["string", "result"]
        
        return input_types, output_types
    
    @staticmethod
    def _generate_examples(tool_name: str, description: str, parameters: Dict[str, Any]) -> List[str]:
        """Generate example usage for the tool."""
        examples = []
        
        # Generate examples based on tool name and description
        if "calculator" in tool_name.lower() or "calc" in tool_name.lower():
            examples.append("Calculate: 2^3 + sqrt(16)")
            examples.append("Evaluate: sin(pi/2)")
        
        if "statistics" in tool_name.lower() or "stats" in tool_name.lower():
            examples.append("Analyze data: [1, 2, 3, 4, 5]")
            examples.append("Calculate mean and standard deviation")
        
        if "matrix" in tool_name.lower():
            examples.append("Find determinant of [[1,2],[3,4]]")
            examples.append("Calculate eigenvalues")
        
        if "integration" in tool_name.lower():
            examples.append("Integrate x^2 from 0 to 1")
            examples.append("Numerical integration of sin(x)")
        
        return examples
    
    @staticmethod
    def _map_category(category: str) -> ToolCategory:
        """Map string category to ToolCategory enum."""
        category_mapping = {
            "mathematics": ToolCategory.MATHEMATICS,
            "statistics": ToolCategory.STATISTICS,
            "linear_algebra": ToolCategory.LINEAR_ALGEBRA,
            "calculus": ToolCategory.CALCULUS,
            "number_theory": ToolCategory.NUMBER_THEORY,
            "data_processing": ToolCategory.DATA_PROCESSING,
            "file_operations": ToolCategory.FILE_OPERATIONS,
            "network": ToolCategory.NETWORK,
            "database": ToolCategory.DATABASE,
            "ai_ml": ToolCategory.AI_ML,
            "utilities": ToolCategory.UTILITIES
        }
        
        return category_mapping.get(category.lower(), ToolCategory.UNKNOWN)
