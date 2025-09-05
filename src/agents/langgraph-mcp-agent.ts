import { HTTPMCPClient } from '../mcp/http-mcp-client';
import { RateLimitedLLM } from '../llm/rate-limited-llm';
import { SessionManager } from '../core/session-manager';
import { HumanMessage } from '@langchain/core/messages';

/**
 * LangGraph MCP Agent - Let LangGraph handle the workflow orchestration
 * We just provide the initial query and let LangGraph figure out the rest
 */
export class LangGraphMCPAgent {
    private mcpClient: HTTPMCPClient;
    private llm: RateLimitedLLM;
    private sessionManager: SessionManager;

    constructor(mcpClient: HTTPMCPClient, llm: RateLimitedLLM, sessionManager: SessionManager) {
        this.mcpClient = mcpClient;
        this.llm = llm;
        this.sessionManager = sessionManager;
    }

    /**
     * Execute a complex task using LangGraph workflow
     * Just provide the initial query - LangGraph handles the rest
     */
    async executeComplexTask(taskQuery: string, sessionId: string): Promise<string> {
        console.log(`🎯 LangGraph MCP Agent executing: ${taskQuery}`);
        
        try {
            // Add user message to session
            this.sessionManager.addMessage(sessionId, {
                role: 'user',
                content: taskQuery
            });

            // Get available tools for LangGraph
            const tools = this.mcpClient.getTools();
            console.log(`   🛠️ Available tools: ${tools.length}`);

            // Simple LangGraph-style workflow execution
            // Let the LLM decide what to do with the tools
            const result = await this.executeLangGraphWorkflow(taskQuery, tools, sessionId);

            // Add assistant response to session
            this.sessionManager.addMessage(sessionId, {
                role: 'assistant',
                content: result
            });

            console.log(`✅ LangGraph task completed`);
            return result;

        } catch (error) {
            console.error('❌ LangGraph task failed:', error);
            const errorMessage = `Task execution failed: ${error}`;
            
            this.sessionManager.addMessage(sessionId, {
                role: 'assistant',
                content: errorMessage
            });
            
            return errorMessage;
        }
    }

    /**
     * Execute LangGraph-style workflow
     * The LLM decides which tools to use and when
     */
    private async executeLangGraphWorkflow(
        taskQuery: string, 
        tools: any[], 
        sessionId: string
    ): Promise<string> {
        console.log('🔄 Starting LangGraph workflow execution...');

        // Get session history for context
        const session = this.sessionManager.getSession(sessionId);
        const history = session?.messages || [];

        // Build context from session history
        const contextMessages = history.slice(-6); // Last 6 messages for context
        const context = contextMessages.map(msg => 
            `${msg.role}: ${msg.content}`
        ).join('\n');

        // Simple system prompt - let LangGraph handle tool orchestration
        const systemPrompt = `You are an AI assistant with access to tools. 
You can use these tools to help complete tasks. 
Think step by step and use tools when needed.

Available tools: ${tools.map(t => t.name).join(', ')}

${context ? `Previous context:\n${context}\n` : ''}

Task: ${taskQuery}

Respond naturally and use tools when helpful.`;

        const messages = [new HumanMessage(systemPrompt)];

        try {
            // Let the LLM decide what to do
            const response = await this.llm.invoke(messages);
            const responseText = String(response.content);

            console.log(`   🧠 LLM Response: ${responseText.substring(0, 200)}...`);

            // Check if the LLM wants to use tools
            const toolCalls = this.extractToolCalls(responseText);
            
            if (toolCalls.length > 0) {
                console.log(`   🛠️ LLM wants to use tools: ${toolCalls.map(tc => tc.tool).join(', ')}`);
                
                // Execute tool calls
                const toolResults = await this.executeToolCalls(toolCalls);
                
                // Let LLM process tool results
                const finalResponse = await this.processToolResults(
                    taskQuery, 
                    responseText, 
                    toolResults, 
                    tools
                );
                
                return finalResponse;
            } else {
                // No tools needed, return direct response
                return responseText;
            }

        } catch (error) {
            console.error('❌ LangGraph workflow failed:', error);
            return `I encountered an error while processing your request: ${error}`;
        }
    }

    /**
     * Extract tool calls from LLM response
     * Simple pattern matching for tool usage
     */
    private extractToolCalls(responseText: string): Array<{tool: string, parameters: any}> {
        const toolCalls: Array<{tool: string, parameters: any}> = [];
        
        // Look for tool usage patterns
        const toolPatterns = [
            /use tool (\w+)/gi,
            /call (\w+)/gi,
            /execute (\w+)/gi,
            /run (\w+)/gi
        ];

        for (const pattern of toolPatterns) {
            const matches = responseText.matchAll(pattern);
            for (const match of matches) {
                if (match[1]) {
                    toolCalls.push({
                        tool: match[1],
                        parameters: {} // Simple parameters for now
                    });
                }
            }
        }

        return toolCalls;
    }

    /**
     * Execute tool calls
     */
    private async executeToolCalls(toolCalls: Array<{tool: string, parameters: any}>): Promise<any[]> {
        const results: any[] = [];
        
        for (const toolCall of toolCalls) {
            try {
                console.log(`      🛠️ Executing tool: ${toolCall.tool}`);
                
                const result = await this.mcpClient.executeTool(toolCall.tool, toolCall.parameters);
                results.push({
                    tool: toolCall.tool,
                    result: result,
                    success: true
                });
                
            } catch (error) {
                console.log(`      ❌ Tool ${toolCall.tool} failed: ${error}`);
                results.push({
                    tool: toolCall.tool,
                    error: String(error),
                    success: false
                });
            }
        }

        return results;
    }

    /**
     * Process tool results and generate final response
     */
    private async processToolResults(
        originalTask: string,
        initialResponse: string,
        toolResults: any[],
        _tools: any[]
    ): Promise<string> {
        const toolResultsText = toolResults.map(tr => 
            `Tool ${tr.tool}: ${tr.success ? JSON.stringify(tr.result) : tr.error}`
        ).join('\n');

        const followUpPrompt = `Based on the tool results, provide a complete answer to the original task.

Original task: ${originalTask}
Initial response: ${initialResponse}

Tool results:
${toolResultsText}

Provide a comprehensive final answer.`;

        try {
            const finalResponse = await this.llm.invoke([new HumanMessage(followUpPrompt)]);
            return String(finalResponse.content);
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
}
