import { HTTPMCPClient } from '../mcp/http-mcp-client';

export interface ToolMetadata {
    name: string;
    description: string;
    category: string;
    tags: string[];
    parameters: Record<string, any>;
    examples: string[];
    useCases: string[];
}

export interface ToolSelectionContext {
    userQuery: string;
    conversationHistory: string[];
    availableTools: ToolMetadata[];
    previousToolResults: any[];
    currentStep: number;
    maxTools: number;
}

export interface ToolSelectionResult {
    selectedTools: Array<{
        tool: string;
        parameters: any;
        confidence: number;
        reasoning: string;
    }>;
    shouldRetry: boolean;
    nextStep: string;
}

export class SmartToolSelector {
    private mcpClient: HTTPMCPClient;
    private toolMetadata: Map<string, ToolMetadata> = new Map();

    constructor(mcpClient: HTTPMCPClient) {
        this.mcpClient = mcpClient;
        this.initializeToolMetadata();
    }

    /**
     * Initialize tool metadata with rich descriptions and use cases
     */
    private initializeToolMetadata(): void {
        const tools = this.mcpClient.getTools();
        
        tools.forEach(tool => {
            const metadata = this.createToolMetadata(tool);
            this.toolMetadata.set(tool.name, metadata);
        });
    }

    /**
     * Create rich metadata for each tool
     */
    private createToolMetadata(tool: any): ToolMetadata {
        const baseMetadata = {
            name: tool.name,
            description: tool.description || '',
            category: this.categorizeTool(tool.name),
            tags: this.generateTags(tool.name, tool.description),
            parameters: tool.schema || {},
            examples: this.generateExamples(tool.name),
            useCases: this.generateUseCases(tool.name)
        };

        return baseMetadata;
    }

    /**
     * Categorize tools by functionality
     */
    private categorizeTool(toolName: string): string {
        if (toolName.includes('calculate') || toolName.includes('math')) {
            return 'Math';
        } else if (toolName.includes('search') || toolName.includes('web')) {
            return 'Web Search';
        } else if (toolName.includes('todo') || toolName.includes('task')) {
            return 'Task Management';
        } else if (toolName.includes('file') || toolName.includes('create') || toolName.includes('read')) {
            return 'File Operations';
        } else if (toolName.includes('variable') || toolName.includes('set') || toolName.includes('get')) {
            return 'Variables';
        } else if (toolName.includes('execute') || toolName.includes('command')) {
            return 'Execution';
        } else if (toolName.includes('monitor') || toolName.includes('log')) {
            return 'Monitoring';
        } else {
            return 'Other';
        }
    }

    /**
     * Generate relevant tags for tool discovery
     */
    private generateTags(toolName: string, _description: string): string[] {
        const tags = [toolName];
        
        // Add semantic tags based on tool name and description
        if (toolName.includes('calculate')) {
            tags.push('math', 'arithmetic', 'computation', 'numbers');
        }
        if (toolName.includes('search')) {
            tags.push('search', 'web', 'information', 'research');
        }
        if (toolName.includes('todo')) {
            tags.push('tasks', 'planning', 'organization', 'productivity');
        }
        if (toolName.includes('file')) {
            tags.push('files', 'storage', 'document', 'content');
        }
        if (toolName.includes('variable')) {
            tags.push('data', 'storage', 'memory', 'state');
        }
        if (toolName.includes('execute')) {
            tags.push('execution', 'commands', 'system', 'automation');
        }
        if (toolName.includes('monitor')) {
            tags.push('monitoring', 'logging', 'tracking', 'observability');
        }

        return [...new Set(tags)]; // Remove duplicates
    }

    /**
     * Generate example use cases for each tool
     */
    private generateExamples(toolName: string): string[] {
        const examples: Record<string, string[]> = {
            'calculate': [
                'What is 15 * 23?',
                'Calculate the area of a circle with radius 5',
                'Solve this equation: 2x + 5 = 15'
            ],
            'search_web': [
                'Find information about TypeScript best practices',
                'Search for the latest news about AI',
                'Look up documentation for React hooks'
            ],
            'create_todos': [
                'Create a todo list for learning Python',
                'Make a shopping list for groceries',
                'Plan tasks for the weekend'
            ],
            'read_file': [
                'Read the contents of config.json',
                'Check the main.py file',
                'Read the README.md file'
            ],
            'write_file': [
                'Create a new Python script',
                'Write a configuration file',
                'Save the results to a file'
            ],
            'set_variable': [
                'Store the result of a calculation',
                'Save user preferences',
                'Remember a configuration value'
            ],
            'get_variable': [
                'Retrieve a stored value',
                'Get user settings',
                'Access saved data'
            ]
        };

        return examples[toolName] || [];
    }

    /**
     * Generate use cases for each tool
     */
    private generateUseCases(toolName: string): string[] {
        const useCases: Record<string, string[]> = {
            'calculate': [
                'mathematical computations',
                'arithmetic operations',
                'formula evaluation',
                'numerical analysis'
            ],
            'search_web': [
                'information gathering',
                'research tasks',
                'fact checking',
                'current events lookup'
            ],
            'create_todos': [
                'task planning',
                'project organization',
                'goal setting',
                'workflow management'
            ],
            'read_file': [
                'file content access',
                'configuration reading',
                'document analysis',
                'data retrieval'
            ],
            'write_file': [
                'file creation',
                'data persistence',
                'report generation',
                'code writing'
            ],
            'set_variable': [
                'data storage',
                'state management',
                'configuration saving',
                'memory persistence'
            ],
            'get_variable': [
                'data retrieval',
                'state access',
                'configuration reading',
                'memory recall'
            ]
        };

        return useCases[toolName] || [];
    }

    /**
     * Smart tool selection using multiple strategies
     */
    async selectTools(context: ToolSelectionContext): Promise<ToolSelectionResult> {
        console.log('🧠 Smart tool selection starting...');
        
        // Strategy 1: Intent-based filtering
        const intentTools = this.filterByIntent(context.userQuery, context.availableTools);
        console.log(`   📊 Intent filtering: ${intentTools.length} tools`);

        // Strategy 2: Category-based filtering
        const categoryTools = this.filterByCategory(context.userQuery, intentTools);
        console.log(`   📊 Category filtering: ${categoryTools.length} tools`);

        // Strategy 3: Semantic similarity (simplified)
        const semanticTools = this.filterBySemanticSimilarity(context.userQuery, categoryTools);
        console.log(`   📊 Semantic filtering: ${semanticTools.length} tools`);

        // Strategy 4: Parameter validation
        const validTools = this.validateToolParameters(context.userQuery, semanticTools);
        console.log(`   📊 Parameter validation: ${validTools.length} tools`);

        // Strategy 5: Select top tools with confidence scoring
        const selectedTools = this.selectTopTools(validTools, context.maxTools);
        console.log(`   📊 Final selection: ${selectedTools.length} tools`);

        return {
            selectedTools,
            shouldRetry: selectedTools.length === 0,
            nextStep: selectedTools.length > 0 ? 'execute_tools' : 'request_clarification'
        };
    }

    /**
     * Filter tools based on user intent
     */
    private filterByIntent(userQuery: string, tools: ToolMetadata[]): ToolMetadata[] {
        const query = userQuery.toLowerCase();
        const intentKeywords: Record<string, string[]> = {
            'math': ['calculate', 'compute', 'solve', 'math', 'arithmetic', 'number', 'equation'],
            'search': ['find', 'search', 'look', 'information', 'about', 'what is', 'how to'],
            'todo': ['todo', 'task', 'list', 'plan', 'organize', 'schedule'],
            'file': ['read', 'write', 'file', 'document', 'save', 'create'],
            'variable': ['store', 'save', 'remember', 'variable', 'value', 'data']
        };

        return tools.filter(tool => {
            // Check if query contains intent keywords for this tool category
            const categoryKeywords = intentKeywords[tool.category.toLowerCase()] || [];
            return categoryKeywords.some((keyword: string) => query.includes(keyword));
        });
    }

    /**
     * Filter tools by category relevance
     */
    private filterByCategory(userQuery: string, tools: ToolMetadata[]): ToolMetadata[] {
        const query = userQuery.toLowerCase();
        
        return tools.filter(tool => {
            // Check if tool tags match query
            return tool.tags.some(tag => query.includes(tag.toLowerCase()));
        });
    }

    /**
     * Filter tools by semantic similarity (simplified)
     */
    private filterBySemanticSimilarity(userQuery: string, tools: ToolMetadata[]): ToolMetadata[] {
        const query = userQuery.toLowerCase();
        
        return tools.filter(tool => {
            // Check if tool description or examples match query
            const descriptionMatch = tool.description.toLowerCase().includes(query) ||
                                   query.includes(tool.description.toLowerCase());
            
            const exampleMatch = tool.examples.some(example => 
                example.toLowerCase().includes(query) || query.includes(example.toLowerCase())
            );
            
            const useCaseMatch = tool.useCases.some(useCase => 
                useCase.toLowerCase().includes(query) || query.includes(useCase.toLowerCase())
            );
            
            return descriptionMatch || exampleMatch || useCaseMatch;
        });
    }

    /**
     * Validate tool parameters can be extracted from query
     */
    private validateToolParameters(userQuery: string, tools: ToolMetadata[]): ToolMetadata[] {
        return tools.filter(tool => {
            // Check if we can extract required parameters
            const requiredParams = Object.keys(tool.parameters['required'] || {});
            
            if (requiredParams.length === 0) {
                return true; // No required parameters
            }
            
            // Simple parameter extraction validation
            return requiredParams.some(param => {
                switch (param) {
                    case 'expression':
                        return /\d+\s*[\+\-\*\/]\s*\d+/.test(userQuery);
                    case 'query':
                        return userQuery.length > 10; // Assume query is extractable
                    case 'filename':
                        return /\.\w+/.test(userQuery); // Has file extension
                    case 'todos':
                        return /todo|list|task/.test(userQuery.toLowerCase());
                    default:
                        return true; // Assume other parameters are extractable
                }
            });
        });
    }

    /**
     * Select top tools with confidence scoring
     */
    private selectTopTools(tools: ToolMetadata[], maxTools: number): Array<{
        tool: string;
        parameters: any;
        confidence: number;
        reasoning: string;
    }> {
        // Score tools based on relevance
        const scoredTools = tools.map(tool => {
            let score = 0;
            let reasoning = '';
            
            // Base score
            score += 0.3;
            reasoning += 'Base relevance. ';
            
            // Category relevance
            if (tool.category !== 'Other') {
                score += 0.2;
                reasoning += 'Category match. ';
            }
            
            // Tag relevance
            if (tool.tags.length > 1) {
                score += 0.2;
                reasoning += 'Multiple relevant tags. ';
            }
            
            // Example relevance
            if (tool.examples.length > 0) {
                score += 0.2;
                reasoning += 'Has relevant examples. ';
            }
            
            // Use case relevance
            if (tool.useCases.length > 0) {
                score += 0.1;
                reasoning += 'Has relevant use cases. ';
            }
            
            return {
                tool: tool.name,
                parameters: this.extractParameters(tool.name),
                confidence: Math.min(score, 1.0),
                reasoning: reasoning.trim()
            };
        });
        
        // Sort by confidence and take top tools
        return scoredTools
            .sort((a, b) => b.confidence - a.confidence)
            .slice(0, maxTools);
    }

    /**
     * Extract parameters for selected tools
     */
    private extractParameters(toolName: string): any {
        // This would be enhanced with the existing parameter extraction logic
        switch (toolName) {
            case 'calculate':
                return { expression: '15 * 23' }; // Placeholder
            case 'search_web':
                return { query: 'TypeScript best practices' }; // Placeholder
            case 'create_todos':
                return { todos: ['Learn TypeScript'] }; // Placeholder
            default:
                return {};
        }
    }

    /**
     * Get tool metadata
     */
    getToolMetadata(toolName: string): ToolMetadata | undefined {
        return this.toolMetadata.get(toolName);
    }

    /**
     * Get all tool metadata
     */
    getAllToolMetadata(): ToolMetadata[] {
        return Array.from(this.toolMetadata.values());
    }
}
