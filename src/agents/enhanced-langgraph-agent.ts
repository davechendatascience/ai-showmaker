import { HTTPMCPClient } from '../mcp/http-mcp-client';
import { RateLimitedLLM } from '../llm/rate-limited-llm';
import { SessionManager } from '../core/session-manager';
import { SmartToolSelector, ToolSelectionContext, ToolSelectionResult } from './smart-tool-selector';
import { HumanMessage } from '@langchain/core/messages';

/**
 * Enhanced LangGraph MCP Agent with Smart Tool Selection
 * Implements LangGraph best practices for intelligent tool discovery and selection
 */
export class EnhancedLangGraphAgent {
    private mcpClient: HTTPMCPClient;
    private llm: RateLimitedLLM;
    private sessionManager: SessionManager;
    private toolSelector: SmartToolSelector;

    constructor(mcpClient: HTTPMCPClient, llm: RateLimitedLLM, sessionManager: SessionManager) {
        this.mcpClient = mcpClient;
        this.llm = llm;
        this.sessionManager = sessionManager;
        this.toolSelector = new SmartToolSelector(mcpClient);
    }

    /**
     * Execute a complex task using enhanced LangGraph workflow with smart tool selection
     */
    async executeComplexTask(taskQuery: string, sessionId: string): Promise<string> {
        console.log(`🎯 Enhanced LangGraph Agent executing: ${taskQuery}`);
        
        try {
            // Add user message to session
            this.sessionManager.addMessage(sessionId, {
                role: 'user',
                content: taskQuery
            });

            // Step 1: Smart Tool Selection
            const toolSelectionResult = await this.selectToolsIntelligently(taskQuery, sessionId);
            
            if (toolSelectionResult.shouldRetry) {
                return "I need more information to help you. Could you please provide more details about what you'd like me to do?";
            }

            // Step 2: Execute Selected Tools
            const toolResults = await this.executeSelectedTools(toolSelectionResult.selectedTools);

            // Step 3: Process Results with LLM
            const finalResponse = await this.processToolResults(taskQuery, toolResults);

            // Add assistant response to session
            this.sessionManager.addMessage(sessionId, {
                role: 'assistant',
                content: finalResponse
            });

            console.log(`✅ Enhanced LangGraph task completed`);
            return finalResponse;

        } catch (error) {
            console.error('❌ Enhanced LangGraph task failed:', error);
            const errorMessage = `Task execution failed: ${error}`;
            
            this.sessionManager.addMessage(sessionId, {
                role: 'assistant',
                content: errorMessage
            });
            
            return errorMessage;
        }
    }

    /**
     * Smart tool selection using multiple strategies
     */
    private async selectToolsIntelligently(taskQuery: string, sessionId: string): Promise<ToolSelectionResult> {
        console.log('🧠 Smart tool selection starting...');
        
        // Get session context
        const session = this.sessionManager.getSession(sessionId);
        const conversationHistory = session?.messages.slice(-5).map(msg => msg.content) || [];
        
        // Create tool selection context
        const context: ToolSelectionContext = {
            userQuery: taskQuery,
            conversationHistory,
            availableTools: this.toolSelector.getAllToolMetadata(),
            previousToolResults: [], // Could be enhanced to track previous results
            currentStep: 1,
            maxTools: 3 // Limit to prevent over-execution
        };

        // Use smart tool selector
        const result = await this.toolSelector.selectTools(context);
        
        console.log(`   🎯 Selected ${result.selectedTools.length} tools:`);
        result.selectedTools.forEach(tool => {
            console.log(`      - ${tool.tool} (confidence: ${tool.confidence.toFixed(2)})`);
            console.log(`        Reasoning: ${tool.reasoning}`);
        });

        return result;
    }

    /**
     * Execute selected tools with proper parameter extraction
     */
    private async executeSelectedTools(selectedTools: Array<{
        tool: string;
        parameters: any;
        confidence: number;
        reasoning: string;
    }>): Promise<any[]> {
        console.log('⚡ Executing selected tools...');
        
        const results: any[] = [];
        
        for (const toolSelection of selectedTools) {
            try {
                console.log(`   🛠️ Executing ${toolSelection.tool} (confidence: ${toolSelection.confidence.toFixed(2)})`);
                
                // Extract parameters from the original query context
                const parameters = await this.extractToolParameters(toolSelection.tool, toolSelection.parameters);
                
                const result = await this.mcpClient.executeTool(toolSelection.tool, parameters);
                results.push({
                    tool: toolSelection.tool,
                    result: result,
                    success: true,
                    confidence: toolSelection.confidence,
                    reasoning: toolSelection.reasoning
                });
                
                console.log(`   ✅ ${toolSelection.tool} executed successfully`);
                
            } catch (error) {
                console.log(`   ❌ ${toolSelection.tool} failed: ${error}`);
                results.push({
                    tool: toolSelection.tool,
                    error: String(error),
                    success: false,
                    confidence: toolSelection.confidence,
                    reasoning: toolSelection.reasoning
                });
            }
        }

        return results;
    }

    /**
     * Enhanced parameter extraction with context awareness
     */
    private async extractToolParameters(_toolName: string, baseParameters: any): Promise<any> {
        // This could be enhanced with LLM-based parameter extraction
        // For now, use the base parameters from smart selection
        return baseParameters;
    }

    /**
     * Process tool results with LLM for final response
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
            `Tool: ${tr.tool}\nResult: ${JSON.stringify(tr.result, null, 2)}\nConfidence: ${tr.confidence.toFixed(2)}\nReasoning: ${tr.reasoning}`
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
     * Continue conversation in the same session
     */
    async continueConversation(message: string, sessionId: string): Promise<string> {
        return this.executeComplexTask(message, sessionId);
    }

    /**
     * Get tool selection statistics
     */
    getToolSelectionStats(): any {
        return {
            totalTools: this.toolSelector.getAllToolMetadata().length,
            categories: [...new Set(this.toolSelector.getAllToolMetadata().map(t => t.category))],
            toolSelector: this.toolSelector
        };
    }
}
