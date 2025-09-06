import { HTTPMCPClient } from '../mcp/http-mcp-client';
import { SessionManager } from '../core/session-manager';
import { HumanMessage, SystemMessage } from '@langchain/core/messages';
import { BaseLanguageModel } from '@langchain/core/language_models/base';

/**
 * Discovery-Inspired Agent - Based on GitHub Next Discovery Agent principles
 * Uses react-loop style execution with iterative refinement based on feedback
 */
export class DiscoveryInspiredAgent {
    private mcpClient: HTTPMCPClient;
    private llm: BaseLanguageModel;
    private sessionManager: SessionManager;
    private maxIterations: number = 10; // Increased to allow more flexibility, but still has safety limit

    constructor(mcpClient: HTTPMCPClient, llm: BaseLanguageModel, sessionManager: SessionManager) {
        this.mcpClient = mcpClient;
        this.llm = llm;
        this.sessionManager = sessionManager;
    }

    /**
     * Execute task using Discovery Agent principles
     */
    async executeComplexTask(taskQuery: string, sessionId: string): Promise<string> {
        console.log(`🎯 Discovery-Inspired Agent executing: ${taskQuery}`);
        
        try {
            // Add user message to session
            this.sessionManager.addMessage(sessionId, {
                role: 'user',
                content: taskQuery
            });

            // Step 1: Initialize react loop
            const result = await this.executeReactLoop(taskQuery, sessionId);

            // Add assistant response to session
            this.sessionManager.addMessage(sessionId, {
                role: 'assistant',
                content: result
            });

            console.log(`✅ Discovery-Inspired Agent task completed`);
            return result;

        } catch (error) {
            console.error('❌ Discovery-Inspired Agent task failed:', error);
            const errorMessage = `Task execution failed: ${error}`;
            
            this.sessionManager.addMessage(sessionId, {
                role: 'assistant',
                content: errorMessage
            });
            
            return errorMessage;
        }
    }

    /**
     * React loop execution with iterative refinement
     */
    private async executeReactLoop(taskQuery: string, _sessionId: string): Promise<string> {
        console.log('🔄 Starting react loop execution...');
        
        let iteration = 0;
        let context = {
            task: taskQuery,
            availableTools: this.mcpClient.getTools().map(t => ({
                name: t.name,
                description: t.description,
                schema: t.schema
            })),
            executionHistory: [] as any[],
            currentStep: 'analyze',
            reasoning: '',
            nextAction: '',
            // Add memory tracking
            completedActions: new Set<string>(),
            gatheredInformation: new Map<string, any>(),
            lastResults: [] as any[]
        };

        while (iteration < this.maxIterations) {
            iteration++;
            console.log(`\n   🔄 Iteration ${iteration}/${this.maxIterations}`);

            // Phase 1: Think - Analyze current state and plan next action
            console.log(`   🧠 Phase 1: THINKING...`);
            console.log(`      📊 Memory Debug - Completed Actions: [${Array.from(context.completedActions).join(', ')}]`);
            console.log(`      📊 Memory Debug - Gathered Info: [${Array.from(context.gatheredInformation.keys()).join(', ')}]`);
            console.log(`      📊 Memory Debug - Last Results: [${context.lastResults.length} items]`);
            const thinking = await this.thinkAndAnalyze(context);
            console.log(`      💭 Reasoning: ${thinking.reasoning}`);
            console.log(`      🎯 Next Action: ${thinking.nextAction}`);
            console.log(`      🔄 Should Continue: ${thinking.shouldContinue ? 'YES' : 'NO'}`);
            
            // Check if LLM thinks we have enough information
            if (!thinking.shouldContinue) {
                console.log(`   🏁 LLM decided to stop: Has enough information to complete task`);
                break;
            }
            
            // Phase 2: Act - Select and execute specific tool
            console.log(`   ⚡ Phase 2: ACTING...`);
            const action = await this.actAndExecute(thinking, context);
            console.log(`      🛠️ Selected Tool: ${action.selectedTool || 'None'}`);
            console.log(`      📋 Parameters: ${JSON.stringify(action.parameters)}`);
            
            // Step 3: Execute the selected tool
            const executionResult = await this.executeAction(action, context);
            console.log(`      ✅ Execution: ${executionResult.success ? 'SUCCESS' : 'FAILED'}`);
            
            // Step 4: Update context with results
            context = this.updateContext(context, { ...thinking, ...action }, executionResult);
            
            // Step 5: Check if we should exit
            if (this.shouldExit(context, executionResult)) {
                console.log(`   🏁 Exit condition met: ${context.currentStep}`);
                break;
            }
        }

        // Generate final response based on execution history
        return this.generateFinalResponse(context);
    }

    /**
     * Phase 1: Think - Analyze current state and plan next action (Discovery Agent style)
     */
    private async thinkAndAnalyze(context: any): Promise<{
        reasoning: string;
        nextAction: string;
        confidence: number;
        shouldContinue: boolean;
    }> {
        const systemPrompt = `# Objective:
You are an autonomous AI assistant in the THINKING phase. Your job is to analyze the current state and determine what needs to be done next.

# Available Tools:
${this.formatToolsByServer(context.availableTools)}

# Current Context:
- Task: ${context.task}
- Current Step: ${context.currentStep}
- Execution History: ${context.executionHistory.length} actions taken
- Completed Actions: ${Array.from(context.completedActions).join(', ') || 'None'}
- Gathered Information: ${Array.from(context.gatheredInformation.keys()).join(', ') || 'None'}
- Last Results: ${context.lastResults.slice(-2).map((r: any) => typeof r === 'string' ? r.substring(0, 100) + '...' : JSON.stringify(r).substring(0, 100) + '...').join(', ') || 'None'}

# Your Job (THINKING PHASE):
1. Analyze the current state and what has been accomplished
2. Determine what needs to be done next to progress toward the goal
3. Think about what type of action would be most helpful
4. Do NOT select a specific tool yet - just think about the approach
5. IMPORTANT: Do NOT repeat actions that have already been completed

# Task Completion Logic:
- For DEVELOPMENT tasks (build, create, develop): Continue until the actual product is created
- For INFORMATION tasks (search, find, explain): Continue until you have comprehensive information
- For CALCULATION tasks: Continue until the calculation is complete
- For LEETCODE tasks: Continue until code is written and tested
- Only stop when you have actually COMPLETED the user's request, not just gathered partial information

# Constraints:
1. Focus on understanding what needs to be done
2. Consider the context and execution history
3. Think strategically about the next step
4. Do not make tool selections in this phase
5. AVOID repeating actions that are already in "Completed Actions"
6. Remember: The user wants the TASK completed, not just information about it

# Output Format:
Provide your thinking in this format:
REASONING: [Your analysis of the current state and what needs to be done next]
NEXT_ACTION: [The type of action you think should be taken - be specific about what needs to happen]
CONTINUE: [YES if you need to perform more actions to complete the actual task, NO only if you have completed all necessary steps to fulfill the user's request]
CONFIDENCE: [0-1 confidence score in your analysis]`;

        const messages = [
            new SystemMessage(systemPrompt),
            new HumanMessage(`Analyze the current state and plan the next action for: ${context.task}`)
        ];

        try {
            const response = await this.llm.invoke(messages);
            const responseText = String(response.content);
            
            // Parse the structured response for thinking phase
            const reasoning = this.extractSection(responseText, 'REASONING') || 'No reasoning provided';
            const nextAction = this.extractSection(responseText, 'NEXT_ACTION') || 'No action specified';
            const continueText = this.extractSection(responseText, 'CONTINUE') || 'YES';
            const confidence = parseFloat(this.extractSection(responseText, 'CONFIDENCE') || '0.5');
            
            const shouldContinue = continueText.toUpperCase().includes('YES');

            return {
                reasoning: reasoning,
                nextAction: nextAction,
                confidence: confidence,
                shouldContinue: shouldContinue
            };

        } catch (error) {
            console.error('❌ Analysis failed:', error);
            return {
                reasoning: 'Analysis failed due to error',
                nextAction: 'retry_analysis',
                confidence: 0.1,
                shouldContinue: true
            };
        }
    }

    /**
     * Phase 2: Act - Select and execute specific tool based on thinking phase
     */
    private async actAndExecute(thinking: any, context: any): Promise<{
        selectedTool?: string;
        parameters?: any;
        reasoning: string;
    }> {
        const systemPrompt = `# Objective:
You are an autonomous AI assistant in the ACTING phase. Based on the thinking analysis, you must now select and execute a specific tool.

# Available Tools:
${this.formatToolsByServer(context.availableTools)}

# Current Context:
- Completed Actions: ${Array.from(context.completedActions).join(', ') || 'None'}
- Gathered Information: ${Array.from(context.gatheredInformation.keys()).join(', ') || 'None'}
- Last Results: ${context.lastResults.slice(-2).map((r: any) => typeof r === 'string' ? r.substring(0, 100) + '...' : JSON.stringify(r).substring(0, 100) + '...').join(', ') || 'None'}

# Thinking Analysis:
- Reasoning: ${thinking.reasoning}
- Next Action: ${thinking.nextAction}
- Confidence: ${thinking.confidence}

# Your Job (ACTING PHASE):
1. Based on the thinking analysis, select the most appropriate tool
2. Determine the exact parameters needed for that tool
3. Be specific and precise in your tool selection
4. Consider the context and what the tool needs to accomplish
5. CRITICAL: Do NOT select tools that are already in "Completed Actions" - choose a different tool or approach

# Constraints:
1. Select only one tool per action
2. Provide ALL required parameters using the EXACT schema keys (do NOT invent synonyms)
3. Be precise with parameter values
4. Consider the user's original request
5. File tools: the key is "filename" (NOT "path" or "file_path")
6. Multiple commands: use "execute_commands_session" with "commands": ["..."] (NOT "execute_command")

# Output Format:
You MUST provide your action in this EXACT format:
TOOL: [Exact tool name from the available tools list - must be one of the tools listed above]
PARAMETERS: [JSON object with all required parameters - must be valid JSON]
REASONING: [Why you selected this tool and these parameters]

# Examples:
TOOL: search_web
PARAMETERS: {"query": "TypeScript best practices"}
REASONING: I need to search for information about TypeScript best practices.

TOOL: calculate
PARAMETERS: {"expression": "15 * 23"}
REASONING: I need to calculate the mathematical expression 15 * 23.

TOOL: create_todos
PARAMETERS: {"todos": [{"id": "task1", "content": "Complete project setup", "status": "pending"}]}
REASONING: I need to create a todo list for task management.

TOOL: write_file
PARAMETERS: {"filename":"index.html","content":"<html>...</html>"}
REASONING: I need to create an HTML entry file. The schema requires "filename" and "content".

TOOL: execute_commands_session
PARAMETERS: {"commands":["cd /home/ec2-user/workspace","git status"]}
REASONING: I need to run multiple commands while preserving state.

# CRITICAL: You must select a valid tool from the list above. Do not select "None" or make up tool names.`;

        const messages = [
            new SystemMessage(systemPrompt),
            new HumanMessage(`Based on the thinking analysis, select and execute a tool for: ${context.task}`)
        ];

        try {
            const response = await this.llm.invoke(messages);
            const responseText = String(response.content);
            
            // Parse the structured response
            const rawTool = this.extractSection(responseText, 'TOOL');
            const tool = this.cleanToolName(rawTool);
            const parameters = this.extractParameters(responseText, tool || undefined);
            const reasoning = this.extractSection(responseText, 'REASONING') || 'No reasoning provided';
            
            // Debug logging
            console.log(`      🔍 Debug - Raw Tool: "${rawTool}"`);
            console.log(`      🔍 Debug - Cleaned Tool: "${tool}"`);
            console.log(`      🔍 Debug - Parameters: ${JSON.stringify(parameters)}`);
            console.log(`      🔍 Debug - Full Response: ${responseText.substring(0, 500)}...`);

            const result: {
                selectedTool?: string;
                parameters?: any;
                reasoning: string;
            } = {
                reasoning: reasoning
            };
            
            if (tool) {
                result.selectedTool = tool;
            }
            
            if (parameters && Object.keys(parameters).length > 0) {
                result.parameters = parameters;
            }
            
            return result;

        } catch (error) {
            console.error('❌ Action failed:', error);
            return {
                reasoning: 'Action failed due to error'
            };
        }
    }

    /**
     * Execute the planned action
     */
    private async executeAction(analysis: any, _context: any): Promise<{
        success: boolean;
        result: any;
        error?: string;
        tool?: string;
    }> {
        if (!analysis.selectedTool || analysis.selectedTool === 'None') {
            // LLM decided not to use tools - this is a valid decision
            return {
                success: true,
                result: 'LLM decided to respond directly without using tools',
                tool: 'none'
            };
        }

        try {
            console.log(`      🛠️ Executing ${analysis.selectedTool} with params:`, analysis.parameters);
            
            const result = await this.mcpClient.executeTool(analysis.selectedTool, analysis.parameters);
            const ok = typeof (result?.success) === 'boolean' ? Boolean(result.success) : true;
            const errorMsg = (result && typeof result.error === 'string') ? result.error : undefined;
            return {
                success: ok,
                result: result,
                tool: analysis.selectedTool,
                error: ok ? undefined : (errorMsg || 'Tool reported failure')
            };

        } catch (error) {
            console.log(`      ❌ Tool execution failed: ${error}`);
            return {
                success: false,
                result: null,
                error: String(error),
                tool: analysis.selectedTool
            };
        }
    }

    /**
     * Update context with execution results
     */
    private updateContext(context: any, analysis: any, executionResult: any): any {
        const newContext = { ...context };
        
        // Add to execution history
        newContext.executionHistory.push({
            iteration: newContext.executionHistory.length + 1,
            analysis: analysis,
            execution: executionResult,
            timestamp: new Date()
        });

        // Track completed actions and gathered information
        if (executionResult.success && analysis.selectedTool && analysis.selectedTool !== 'None') {
            // Mark action as completed
            console.log(`      🧠 Memory Update - Adding completed action: ${analysis.selectedTool}`);
            newContext.completedActions.add(analysis.selectedTool);
            
            // Store gathered information based on tool type
            if (analysis.selectedTool === 'search_web' && executionResult.result) {
                const searchQuery = analysis.parameters?.query || 'unknown';
                newContext.gatheredInformation.set(`search_${searchQuery}`, executionResult.result);
            } else if (analysis.selectedTool === 'calculate' && executionResult.result) {
                newContext.gatheredInformation.set('calculation_result', executionResult.result);
            } else if (analysis.selectedTool === 'create_todos' && executionResult.result) {
                newContext.gatheredInformation.set('todo_list', executionResult.result);
            } else if (analysis.selectedTool === 'set_variable' && executionResult.result) {
                newContext.gatheredInformation.set('variable_set', executionResult.result);
            }
            
            // Update last results
            newContext.lastResults.push(executionResult.result);
            if (newContext.lastResults.length > 5) {
                newContext.lastResults = newContext.lastResults.slice(-5); // Keep only last 5 results
            }
        }

        // Update current step based on results
        if (executionResult.success) {
            if (analysis.selectedTool === 'calculate') {
                newContext.currentStep = 'math_completed';
            } else if (analysis.selectedTool?.includes('search')) {
                newContext.currentStep = 'search_completed';
            } else if (analysis.selectedTool?.includes('todo')) {
                newContext.currentStep = 'todo_completed';
            } else if (analysis.selectedTool === 'None' || executionResult.tool === 'none') {
                newContext.currentStep = 'direct_response_ready';
            } else {
                newContext.currentStep = 'action_completed';
            }
        } else {
            newContext.currentStep = 'error_recovery';
        }

        return newContext;
    }

    /**
     * Check if we should exit the react loop
     */
    private shouldExit(context: any, executionResult: any): boolean {
        // Exit conditions based on Discovery Agent principles
        
        // If LLM decided to respond directly without tools, exit
        if (executionResult.success && executionResult.tool === 'none') {
            console.log('   🏁 Exit: LLM decided to respond directly, task complete');
            return true;
        }

        // If we have the information we need, exit
        if (context.gatheredInformation.size > 0 && executionResult.success) {
            const taskLower = context.task.toLowerCase();
            
            // For search tasks, if we have search results, we can exit
            if (taskLower.includes('search') || taskLower.includes('find') || taskLower.includes('information')) {
                const hasSearchResults = Array.from(context.gatheredInformation.keys()).some((key: any) => String(key).startsWith('search_'));
                if (hasSearchResults) {
                    console.log('   🏁 Exit: Found search results, task likely complete');
                    return true;
                }
            }
            
            // For calculation tasks, if we have calculation results, we can exit
            if (taskLower.includes('calculate') || taskLower.includes('math') || taskLower.includes('*') || taskLower.includes('+')) {
                if (context.gatheredInformation.has('calculation_result')) {
                    console.log('   🏁 Exit: Found calculation result, task complete');
                    return true;
                }
            }
            
            // For todo tasks, if we have todo list, we can exit
            if (taskLower.includes('todo') || taskLower.includes('list')) {
                if (context.gatheredInformation.has('todo_list')) {
                    console.log('   🏁 Exit: Created todo list, task complete');
                    return true;
                }
            }
        }
        
        // Exit if we've made significant progress
        if (context.executionHistory.length >= 3 && executionResult.success) {
            console.log('   🏁 Exit: Made significant progress, task likely complete');
            return true;
        }

        // Exit if we're stuck in error recovery
        if (context.currentStep === 'error_recovery' && context.executionHistory.length >= 2) {
            console.log('   🏁 Exit: Stuck in error recovery, stopping');
            return true;
        }

        return false;
    }

    /**
     * Generate final response based on execution history
     */
    private async generateFinalResponse(context: any): Promise<string> {
        const successfulExecutions = context.executionHistory.filter((h: any) => h.execution.success);
        const failedExecutions = context.executionHistory.filter((h: any) => !h.execution.success);

        // Check if the LLM decided not to use tools (intentional decision)
        const hasDirectResponse = context.executionHistory.some((h: any) => 
            h.execution.tool === 'none' || h.analysis?.selectedTool === 'None'
        );

        if (successfulExecutions.length === 0 && !hasDirectResponse) {
            return "I encountered difficulties while trying to help you. The tools I attempted to use didn't work as expected. Could you please rephrase your request or provide more details?";
        }

        // If LLM decided to respond directly without tools, generate a direct response
        if (hasDirectResponse && successfulExecutions.length === 0) {
            const prompt = `The user asked: "${context.task}"

I analyzed the request and determined that I can provide a helpful response without needing to use any specific tools. Please provide a comprehensive, helpful response that directly addresses the user's request.

Be informative, accurate, and provide practical guidance or information as appropriate.`;

            try {
                const response = await this.llm.invoke([new HumanMessage(prompt)]);
                return String(response.content);
            } catch (error) {
                return `I can help you with that request. Let me provide some guidance based on your question: "${context.task}". However, I encountered an error in generating the response: ${error}`;
            }
        }

        // Determine if this is an information task or a completion task
        const taskLower = context.task.toLowerCase();
        const isInformationTask = taskLower.includes('search') || taskLower.includes('find') || 
                                 taskLower.includes('explain') || taskLower.includes('information') ||
                                 taskLower.includes('what') || taskLower.includes('how') || taskLower.includes('why');
        
        const isDevelopmentTask = taskLower.includes('develop') || taskLower.includes('build') || 
                                 taskLower.includes('create') || taskLower.includes('make') ||
                                 taskLower.includes('webapp') || taskLower.includes('application');

        const prompt = `Based on the execution history below, provide a comprehensive response to the user's original request.

Original Request: ${context.task}

Successful Executions:
${successfulExecutions.map((h: any) => 
    `- ${h.execution.tool}: ${JSON.stringify(h.execution.result, null, 2)}`
).join('\n')}

${failedExecutions.length > 0 ? `Failed Executions:
${failedExecutions.map((h: any) => 
    `- ${h.execution.tool}: ${h.execution.error}`
).join('\n')}` : ''}

${isInformationTask ? 
    'Please provide comprehensive information that addresses the user\'s question using the gathered data.' :
    isDevelopmentTask ?
    'Please provide a summary of what was accomplished and any next steps needed to complete the development task.' :
    'Please provide a clear, helpful response that addresses the user\'s original request using the information from the successful tool executions.'}`;

        try {
            const response = await this.llm.invoke([new HumanMessage(prompt)]);
            return String(response.content);
        } catch (error) {
            return `I used tools to help with your request, but encountered an error in the final response: ${error}`;
        }
    }

    /**
     * Extract section from structured response
     */
    private extractSection(text: string, section: string): string | null {
        const regex = new RegExp(`${section}:\\s*(.+?)(?=\\n[A-Z_]+:|$)`, 's');
        const match = text.match(regex);
        return match && match[1] ? match[1].trim() : null;
    }

    /**
     * Clean tool name from long descriptions
     */
    private cleanToolName(rawTool: string | null): string | null {
        if (!rawTool) return null;

        // All available MCP tool names (from the bridge output)
        const toolNames = [
            // Calculation Server
            'calculate', 'set_variable', 'get_variables', 'clear_variables',
            // Development Server
            'git_status', 'git_add', 'git_commit', 'git_log', 'git_diff', 'find_files', 'search_in_files', 'install_package',
            // Monitoring Server
            'create_session', 'create_todos', 'update_todo_status', 'get_current_todos', 'clear_todos', 'get_progress_summary',
            // Remote Server
            'init_workspace', 'clone_repository', 'list_repositories', 'switch_repository', 'get_current_repository',
            'git_push', 'git_pull', 'install_ollama', 'pull_model', 'list_ollama_models', 'test_local_model',
            'execute_command', 'write_file', 'read_file', 'list_directory', 'execute_commands_session', 'development_workflow',
            // Web Search Server
            'search_web', 'extract_content', 'search_and_extract', 'get_search_suggestions'
        ];

        const lower = rawTool.toLowerCase().trim();
        // Prefer exact match
        for (const name of toolNames) {
            if (lower === name) return name;
        }
        // Prefer word-boundary match
        for (const name of toolNames) {
            const re = new RegExp(`(^|[^a-zA-Z0-9_])${name}([^a-zA-Z0-9_]|$)`);
            if (re.test(lower)) return name;
        }
        // Fallback: longest-first substring match (prevents mapping session->command)
        for (const name of [...toolNames].sort((a,b)=>b.length-a.length)) {
            if (lower.includes(name)) return name;
        }

        // Extract from patterns like "use the calculate tool"
        const usePattern = /use (?:the )?(\w+) tool/i;
        const useMatch = rawTool.match(usePattern);
        if (useMatch && useMatch[1] && toolNames.includes(useMatch[1])) {
            return useMatch[1];
        }

        // Extract from patterns like "call calculate"
        const callPattern = /call (\w+)/i;
        const callMatch = rawTool.match(callPattern);
        if (callMatch && callMatch[1] && toolNames.includes(callMatch[1])) {
            return callMatch[1];
        }

        // If no pattern matches, return the first word that looks like a tool name
        const words = rawTool.split(/\s+/);
        for (const word of words) {
            if (toolNames.includes(word.toLowerCase())) {
                return word.toLowerCase();
            }
        }

        return null;
    }

    /**
     * Extract parameters from structured response
     */
    private extractParameters(text: string, toolName?: string): any {
        const paramsSection = this.extractSection(text, 'PARAMETERS');
        if (!paramsSection) {
            // Generate default parameters based on tool name and context
            return this.generateDefaultParameters(text, toolName);
        }

        // Check if the parameters section contains code instead of JSON
        if (paramsSection.includes('def ') || paramsSection.includes('function ') || 
            paramsSection.includes('class ') || paramsSection.includes('import ')) {
            console.log('   ⚠️  Detected code in parameters, generating default parameters instead');
            return this.generateDefaultParameters(text, toolName);
        }

        try {
            // Try to parse as JSON
            const parsed = JSON.parse(paramsSection);
            return this.applyParameterAliases(parsed, toolName);
        } catch {
            // Fallback to simple key-value parsing
            const params: any = {};
            const lines = paramsSection.split('\n');
            for (const line of lines) {
                const [key, value] = line.split(':');
                if (key && value) {
                    params[key.trim()] = value.trim();
                }
            }
            return this.applyParameterAliases(params, toolName);
        }
    }

    // Normalize/alias common parameter names the LLM may use
    private applyParameterAliases(params: any, toolName?: string): any {
        const p = { ...(params || {}) };
        const t = (toolName || '').toLowerCase();
        if (t === 'write_file' || t === 'read_file') {
            if (p.file_path && !p.filename) {
                p.filename = p.file_path;
                delete p.file_path;
            }
        }
        if (t === 'execute_command' && Array.isArray(p.commands) && !p.command) {
            // Signal the caller to use the session variant by keeping commands array
            // Final routing happens in normalizeToolAndParams
        }
        return p;
    }

    /**
     * Get tool server category for better organization
     */
    private getToolServerCategory(toolName: string): string {
        const serverCategories: { [key: string]: string } = {
            // Calculation Server
            'calculate': 'Calculation',
            'set_variable': 'Calculation',
            'get_variables': 'Calculation',
            'clear_variables': 'Calculation',
            
            // Development Server
            'git_status': 'Development',
            'git_add': 'Development',
            'git_commit': 'Development',
            'git_log': 'Development',
            'git_diff': 'Development',
            'find_files': 'Development',
            'search_in_files': 'Development',
            'install_package': 'Development',
            
            // Monitoring Server
            'create_session': 'Monitoring',
            'create_todos': 'Monitoring',
            'update_todo_status': 'Monitoring',
            'get_current_todos': 'Monitoring',
            'clear_todos': 'Monitoring',
            'get_progress_summary': 'Monitoring',
            
            // Remote Server
            'init_workspace': 'Remote',
            'clone_repository': 'Remote',
            'list_repositories': 'Remote',
            'switch_repository': 'Remote',
            'get_current_repository': 'Remote',
            'git_push': 'Remote',
            'git_pull': 'Remote',
            'install_ollama': 'Remote',
            'pull_model': 'Remote',
            'list_ollama_models': 'Remote',
            'test_local_model': 'Remote',
            'execute_command': 'Remote',
            'write_file': 'Remote',
            'read_file': 'Remote',
            'list_directory': 'Remote',
            'execute_commands_session': 'Remote',
            'development_workflow': 'Remote',
            
            // Web Search Server
            'search_web': 'Web Search',
            'extract_content': 'Web Search',
            'search_and_extract': 'Web Search',
            'get_search_suggestions': 'Web Search'
        };
        
        return serverCategories[toolName] || 'Other';
    }

    /**
     * Get enhanced tool description for better LLM understanding
     */
    private getEnhancedToolDescription(toolName: string, originalDescription: string): string {
        const enhancedDescriptions: { [key: string]: string } = {
            'search_web': 'Search the web for information. Use for finding facts, documentation, tutorials, or any online content.',
            'calculate': 'Perform mathematical calculations. Use for arithmetic, algebra, or any mathematical operations.',
            'create_todos': 'Create a todo list for task management. Use for organizing tasks and tracking progress.',
            'set_variable': 'Store a value in memory for later use. Use for saving important information or results.',
            'get_variables': 'Retrieve stored values from memory. Use for accessing previously saved information.',
            'write_file': 'Create or write content to a file. Use for saving code, documentation, or any text content.',
            'read_file': 'Read content from a file. Use for accessing existing files or code.',
            'execute_command': 'Run shell commands. Use for executing system commands, scripts, or development tasks.',
            'git_status': 'Check git repository status. Use for seeing what files have changed.',
            'git_add': 'Stage files for git commit. Use for preparing files to be committed.',
            'git_commit': 'Commit staged changes to git. Use for saving changes to version control.',
            'find_files': 'Search for files by name or pattern. Use for locating specific files in the project.',
            'search_in_files': 'Search for text content within files. Use for finding specific code or text patterns.',
            'list_directory': 'List files and folders in a directory. Use for exploring project structure.',
            'extract_content': 'Extract content from web pages. Use for getting specific information from websites.',
            'search_and_extract': 'Search web and extract content in one step. Use for comprehensive web research.',
            'init_workspace': 'Initialize a new workspace for development. Use for setting up new projects.',
            'clone_repository': 'Clone a git repository. Use for downloading existing projects.',
            'install_package': 'Install software packages or dependencies. Use for adding libraries or tools.',
            'development_workflow': 'Execute a complete development workflow. Use for complex multi-step development tasks.'
        };
        
        return enhancedDescriptions[toolName] || originalDescription;
    }

    /**
     * Format tools grouped by server categories
     */
    private formatToolsByServer(tools: any[]): string {
        // Group tools by server category
        const toolsByServer: { [server: string]: any[] } = {};
        
        tools.forEach(tool => {
            const server = this.getToolServerCategory(tool.name);
            if (!toolsByServer[server]) {
                toolsByServer[server] = [];
            }
            toolsByServer[server].push(tool);
        });

        // Format each server category
        const serverDescriptions: { [key: string]: string } = {
            'Calculation': '🧮 CALCULATION SERVER - Math operations and variable management',
            'Development': '🛠️ DEVELOPMENT SERVER - Git operations and file management',
            'Monitoring': '📊 MONITORING SERVER - Task tracking and progress management',
            'Remote': '🌐 REMOTE SERVER - Remote workspace and command execution',
            'Web Search': '🔍 WEB SEARCH SERVER - Internet search and content extraction',
            'Other': '🔧 OTHER TOOLS - Miscellaneous utilities'
        };

        let result = '';
        Object.keys(toolsByServer).sort().forEach(server => {
            const serverTools = toolsByServer[server];
            if (serverTools) {
                const description = serverDescriptions[server] || `🔧 ${server.toUpperCase()} SERVER`;
                
                result += `\n## ${description}\n`;
                serverTools.forEach(tool => {
                    const enhancedDescription = this.getEnhancedToolDescription(tool.name, tool.description);
                    result += `- ${tool.name}: ${enhancedDescription}\n`;
                });
            }
        });

        return result;
    }

    /**
     * Generate default parameters based on tool name and context
     */
    private generateDefaultParameters(text: string, toolName?: string): any {
        if (!toolName) return {};

        switch (toolName.toLowerCase()) {
            case 'calculate':
                // Extract math expression from the original task
                const mathMatch = text.match(/(\d+\s*[\+\-\*\/]\s*\d+)/);
                if (mathMatch) {
                    return { expression: mathMatch[1] };
                }
                // Look for "What is X * Y?" patterns
                const whatIsMatch = text.match(/what is (\d+)\s*\*\s*(\d+)/i);
                if (whatIsMatch) {
                    return { expression: `${whatIsMatch[1]} * ${whatIsMatch[2]}` };
                }
                return { expression: '15 * 23' }; // Default fallback

            case 'search_web':
                // Extract search query from context
                const searchMatch = text.match(/find information about (.+?)(?:\.|$)/i);
                if (searchMatch && searchMatch[1]) {
                    return { query: searchMatch[1].trim() };
                }
                return { query: 'TypeScript best practices' };

            case 'create_todos':
                return { 
                    title: 'Task List',
                    items: ['Complete the requested task']
                };

            default:
                return {};
        }
    }

    /**
     * Continue conversation
     */
    async continueConversation(message: string, sessionId: string): Promise<string> {
        return this.executeComplexTask(message, sessionId);
    }
}
