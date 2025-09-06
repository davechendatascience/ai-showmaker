import { HTTPMCPClient } from '../mcp/http-mcp-client';
import { RateLimitedLLM } from '../llm/rate-limited-llm';
import { SessionManager } from '../core/session-manager';
import { HumanMessage } from '@langchain/core/messages';

/**
 * Simple Smart Agent - Demonstrates LangGraph best practices with practical tool selection
 */
export class SimpleSmartAgent {
    private mcpClient: HTTPMCPClient;
    private llm: RateLimitedLLM;
    private sessionManager: SessionManager;

    constructor(mcpClient: HTTPMCPClient, llm: RateLimitedLLM, sessionManager: SessionManager) {
        this.mcpClient = mcpClient;
        this.llm = llm;
        this.sessionManager = sessionManager;
    }

    /**
     * Execute task with smart tool selection
     */
    async executeComplexTask(taskQuery: string, sessionId: string): Promise<string> {
        console.log(`🎯 Simple Smart Agent executing: ${taskQuery}`);
        
        try {
            // Add user message to session
            this.sessionManager.addMessage(sessionId, {
                role: 'user',
                content: taskQuery
            });

            // Step 1: Smart Tool Selection
            const selectedTools = this.selectToolsSmartly(taskQuery);
            console.log(`   🎯 Smart selection: ${selectedTools.length} tools`);
            selectedTools.forEach(tool => {
                console.log(`      - ${tool.name} (${tool.category}) - ${tool.reasoning}`);
            });

            if (selectedTools.length === 0) {
                return "I couldn't determine which tools would be most helpful for your request. Could you please provide more details?";
            }

            // Step 2: Execute Selected Tools
            const toolResults = await this.executeSelectedTools(selectedTools, taskQuery);

            // Step 3: Process Results
            const finalResponse = await this.processToolResults(taskQuery, toolResults);

            // Add assistant response to session
            this.sessionManager.addMessage(sessionId, {
                role: 'assistant',
                content: finalResponse
            });

            console.log(`✅ Simple Smart Agent task completed`);
            return finalResponse;

        } catch (error) {
            console.error('❌ Simple Smart Agent task failed:', error);
            const errorMessage = `Task execution failed: ${error}`;
            
            this.sessionManager.addMessage(sessionId, {
                role: 'assistant',
                content: errorMessage
            });
            
            return errorMessage;
        }
    }

    /**
     * Smart tool selection using intent analysis
     */
    private selectToolsSmartly(taskQuery: string): Array<{
        name: string;
        category: string;
        reasoning: string;
        parameters: any;
    }> {
        const query = taskQuery.toLowerCase();
        const allTools = this.mcpClient.getTools();
        const selectedTools: Array<{
            name: string;
            category: string;
            reasoning: string;
            parameters: any;
        }> = [];

        // Intent-based tool selection
        for (const tool of allTools) {
            let shouldSelect = false;
            let reasoning = '';
            let category = 'Other';
            let parameters: any = {};

            // Math/Calculation tools
            if (tool.name.includes('calculate') || tool.name.includes('math')) {
                if (this.isMathQuery(query)) {
                    shouldSelect = true;
                    reasoning = 'Math query detected';
                    category = 'Math';
                    parameters = this.extractMathParameters(query);
                }
            }

            // Search tools
            else if (tool.name.includes('search') || tool.name.includes('web')) {
                if (this.isSearchQuery(query)) {
                    shouldSelect = true;
                    reasoning = 'Search query detected';
                    category = 'Search';
                    parameters = this.extractSearchParameters(query);
                }
            }

            // Todo/Task tools
            else if (tool.name.includes('todo') || tool.name.includes('task')) {
                if (this.isTodoQuery(query)) {
                    shouldSelect = true;
                    reasoning = 'Todo/task query detected';
                    category = 'Task Management';
                    parameters = this.extractTodoParameters(query);
                }
            }

            // File tools
            else if (tool.name.includes('file') || tool.name.includes('read') || tool.name.includes('write')) {
                if (this.isFileQuery(query)) {
                    shouldSelect = true;
                    reasoning = 'File operation query detected';
                    category = 'File Operations';
                    parameters = this.extractFileParameters(query);
                }
            }

            // Variable tools
            else if (tool.name.includes('variable') || tool.name.includes('set') || tool.name.includes('get')) {
                if (this.isVariableQuery(query)) {
                    shouldSelect = true;
                    reasoning = 'Variable operation query detected';
                    category = 'Variables';
                    parameters = this.extractVariableParameters(query);
                }
            }

            if (shouldSelect) {
                selectedTools.push({
                    name: tool.name,
                    category,
                    reasoning,
                    parameters
                });
            }
        }

        // Limit to top 3 tools to prevent over-execution
        return selectedTools.slice(0, 3);
    }

    /**
     * Intent detection methods
     */
    private isMathQuery(query: string): boolean {
        const mathKeywords = ['calculate', 'compute', 'solve', 'math', 'arithmetic', 'number', 'equation', 'what is', 'times', 'plus', 'minus', 'divide'];
        return mathKeywords.some(keyword => query.includes(keyword)) || /\d+\s*[\+\-\*\/]\s*\d+/.test(query);
    }

    private isSearchQuery(query: string): boolean {
        const searchKeywords = ['find', 'search', 'look', 'information', 'about', 'what is', 'how to', 'best practices', 'documentation'];
        return searchKeywords.some(keyword => query.includes(keyword));
    }

    private isTodoQuery(query: string): boolean {
        const todoKeywords = ['todo', 'task', 'list', 'plan', 'organize', 'schedule', 'create', 'make'];
        return todoKeywords.some(keyword => query.includes(keyword));
    }

    private isFileQuery(query: string): boolean {
        const fileKeywords = ['read', 'write', 'file', 'document', 'save', 'create', 'open'];
        return fileKeywords.some(keyword => query.includes(keyword)) || /\.\w+/.test(query);
    }

    private isVariableQuery(query: string): boolean {
        const variableKeywords = ['store', 'save', 'remember', 'variable', 'value', 'data', 'set', 'get'];
        return variableKeywords.some(keyword => query.includes(keyword));
    }

    /**
     * Parameter extraction methods
     */
    private extractMathParameters(query: string): any {
        const mathMatch = query.match(/(\d+(?:\.\d+)?)\s*[\+\-\*\/]\s*(\d+(?:\.\d+)?)/);
        if (mathMatch) {
            return { expression: mathMatch[0] };
        }
        return { expression: '15 * 23' }; // Default
    }

    private extractSearchParameters(query: string): any {
        // Extract search terms
        const searchTerms = query.replace(/find|search|look|information|about|what is|how to/gi, '').trim();
        return { query: searchTerms || 'TypeScript best practices' };
    }

    private extractTodoParameters(query: string): any {
        // Extract todo subject
        const todoMatch = query.match(/todo|list|plan|organize|schedule|create|make.*for\s+(.+)/i);
        if (todoMatch && todoMatch[1]) {
            return { todos: [`Learn ${todoMatch[1].trim()}`] };
        }
        return { todos: ['Create todo list'] };
    }

    private extractFileParameters(query: string): any {
        const fileMatch = query.match(/(\w+\.\w+)/);
        if (fileMatch) {
            return { filename: fileMatch[1] };
        }
        return { filename: 'example.txt' };
    }

    private extractVariableParameters(_query: string): any {
        return { name: 'variable', value: 'value' };
    }

    /**
     * Execute selected tools
     */
    private async executeSelectedTools(selectedTools: Array<{
        name: string;
        category: string;
        reasoning: string;
        parameters: any;
    }>, _taskQuery: string): Promise<any[]> {
        console.log('⚡ Executing selected tools...');
        
        const results: any[] = [];
        
        for (const toolSelection of selectedTools) {
            try {
                console.log(`   🛠️ Executing ${toolSelection.name} (${toolSelection.category})`);
                
                const result = await this.mcpClient.executeTool(toolSelection.name, toolSelection.parameters);
                results.push({
                    tool: toolSelection.name,
                    result: result,
                    success: true,
                    category: toolSelection.category,
                    reasoning: toolSelection.reasoning
                });
                
                console.log(`   ✅ ${toolSelection.name} executed successfully`);
                
            } catch (error) {
                console.log(`   ❌ ${toolSelection.name} failed: ${error}`);
                results.push({
                    tool: toolSelection.name,
                    error: String(error),
                    success: false,
                    category: toolSelection.category,
                    reasoning: toolSelection.reasoning
                });
            }
        }

        return results;
    }

    /**
     * Process tool results with LLM
     */
    private async processToolResults(originalTask: string, toolResults: any[]): Promise<string> {
        console.log('📊 Processing tool results with LLM...');
        
        const successfulResults = toolResults.filter(tr => tr.success);
        const failedResults = toolResults.filter(tr => !tr.success);
        
        if (successfulResults.length === 0) {
            return "I encountered some issues while trying to help you. The tools I attempted to use didn't work as expected. Could you please rephrase your request?";
        }

        // Create a summary of tool results
        const toolResultsSummary = successfulResults.map(tr => 
            `Tool: ${tr.tool} (${tr.category})\nResult: ${JSON.stringify(tr.result, null, 2)}\nReasoning: ${tr.reasoning}`
        ).join('\n\n');

        const failedResultsSummary = failedResults.length > 0 ? 
            `\n\nFailed tools:\n${failedResults.map(tr => `- ${tr.tool}: ${tr.error}`).join('\n')}` : '';

        const prompt = `Based on the tool results below, provide a comprehensive and helpful response to the user's original task.

Original task: ${originalTask}

Tool Results:
${toolResultsSummary}${failedResultsSummary}

Please provide a clear, helpful response that addresses the user's original question using the information from the tool results.`;

        try {
            const response = await this.llm.invoke([new HumanMessage(prompt)]);
            return String(response.content);
        } catch (error) {
            return `I used tools to help with your request, but encountered an error in the final response: ${error}`;
        }
    }

    /**
     * Continue conversation
     */
    async continueConversation(message: string, sessionId: string): Promise<string> {
        return this.executeComplexTask(message, sessionId);
    }
}
