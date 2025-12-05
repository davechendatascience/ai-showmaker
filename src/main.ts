/**
 * AI-Showmaker Interactive App
 * Main application for interactive querying with the LangGraph MCP Agent
 */

import * as dotenv from 'dotenv';
import * as readline from 'readline';
import { HTTPMCPClient } from './mcp/http-mcp-client';
import { SessionManager } from './core/session-manager';
import { EnhancedBestFirstSearchAgentWithMemoryBank } from './agents/enhanced-best-first-search-agent-with-memory-bank';
import { OpenAILLM } from './llm/openai-llm';

// Load environment variables
dotenv.config();

class InteractiveApp {
    private mcpClient!: HTTPMCPClient;
    private llm!: OpenAILLM;
    private sessionManager!: SessionManager;
    private agent!: EnhancedBestFirstSearchAgentWithMemoryBank;
    private rl: readline.Interface;
    private sessionId!: string;
    private isInitialized: boolean = false;

    constructor() {
        this.rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout,
            prompt: '?? AI-Showmaker> '
        });
    }

    async initialize(): Promise<void> {
        console.log('?? Initializing AI-Showmaker Interactive App...');
        console.log('='.repeat(60));

        try {
            // Initialize MCP Client
            console.log('?? Connecting to MCP servers...');
            const mcpBase = (process.env['MCP_HTTP_BASE'] || 'http://localhost:8000').replace(/\/+$/, '');
            this.mcpClient = new HTTPMCPClient(mcpBase);
            console.log(`   Using MCP HTTP base: ${mcpBase}`);
            await this.mcpClient.initialize();
            console.log(`   ??Connected to MCP servers (${this.mcpClient.getTools().length} tools available)`);

            // Initialize LLM
            console.log('?? Initializing OpenAI LLM...');
            const apiKey = process.env['OPENAI_KEY'];
            if (!apiKey) {
                throw new Error('OPENAI_KEY not found in environment variables');
            }
            
            this.llm = new OpenAILLM({
                apiKey: apiKey,
                model: 'gpt-4o-mini',
                temperature: 0.1,
                maxTokens: 2000
            });
            console.log('   ??OpenAI LLM initialized');

            // Initialize Session Manager
            console.log('?? Initializing session management...');
            this.sessionManager = new SessionManager();
            this.sessionId = this.sessionManager.createSession('Interactive Session').id;
            console.log(`   ??Session created: ${this.sessionId}`);

            // Initialize Enhanced Best-First Search Agent
            console.log('?? Initializing Enhanced Best-First Search Agent...');
            this.agent = new EnhancedBestFirstSearchAgentWithMemoryBank(this.mcpClient, this.llm, this.sessionManager);
            console.log('   ??Enhanced Best-First Search Agent initialized');
            console.log('   Features: Shared Memory System, Memory Bank, Enhanced Validation, Persistent Learning');
            
            // Print agent/validator tunables for visibility
            const bw = Number(process.env['BFS_BEAM_WIDTH'] || 4);
            const mi = Number(process.env['BFS_MAX_ITER'] || 40);
            const ms = Number(process.env['BFS_MIN_SCORE'] || 0.4);
            const ve = Number(process.env['BFS_VALIDATOR_EVERY'] || 1);
            const vc = Number(process.env['BFS_VALIDATOR_CONF'] || 0.7);
            console.log(`   Config: BEAM_WIDTH=${bw}, MAX_ITER=${mi}, MIN_SCORE=${ms}`);
            console.log(`   Validator: every ${ve} step(s), min_conf=${vc}`);
            
            const sp = String(process.env['BFS_SCENARIO_PREDICTION'] || 'true');
            const lfo = String(process.env['BFS_LEARN_FROM_OUTCOMES'] || 'true');
            console.log(`   Enhanced: SCENARIO_PREDICTION=${sp}, LEARN_FROM_OUTCOMES=${lfo}`);

            this.isInitialized = true;
            console.log(`\n?? AI-Showmaker is ready with Enhanced Best-First Search Agent!`);
            console.log('?? Best-First Search with Policy+Value (ReAct memory)');
            console.log('?? Enhanced with Scenario Prediction & State Management');
            console.log('? Type your queries below. Use "help" for commands, "exit" to quit.');
            console.log('='.repeat(60));

        } catch (error) {
            console.error('??Failed to initialize AI-Showmaker:', error);
            console.log('\n? Troubleshooting:');
            console.log('   1. Make sure the MCP bridge is running: python full_mcp_bridge.py');
            console.log('   2. Check your .env file has INFERENCE_NET_KEY');
            console.log('   3. Ensure all dependencies are installed: npm install');
            process.exit(1);
        }
    }

    async start(): Promise<void> {
        if (!this.isInitialized) {
            await this.initialize();
        }

        // Set up event handlers
        this.rl.on('line', async (input) => {
            const query = input.trim();
            
            if (query === '') {
                this.rl.prompt();
                return;
            }

            await this.handleInput(query);
        });

        this.rl.on('close', () => {
            console.log('\n?? Goodbye! Thanks for using AI-Showmaker!');
            process.exit(0);
        });

        // Show initial prompt
        this.rl.prompt();
    }

    private async handleInput(query: string): Promise<void> {
        try {
            // Handle special commands
            if (query.toLowerCase() === 'exit' || query.toLowerCase() === 'quit') {
                this.rl.close();
                return;
            }

            if (query.toLowerCase() === 'help') {
                this.showHelp();
                this.rl.prompt();
                return;
            }

            if (query.toLowerCase() === 'status') {
                this.showStatus();
                this.rl.prompt();
                return;
            }

            if (query.toLowerCase() === 'clear') {
                this.clearSession();
                this.rl.prompt();
                return;
            }

            if (query.toLowerCase() === 'tools') {
                this.showTools();
                this.rl.prompt();
                return;
            }

            if (query.toLowerCase() === 'state') {
                this.showEnhancedState();
                this.rl.prompt();
                return;
            }

            if (query.toLowerCase() === 'scenarios') {
                this.showScenarioCache();
                this.rl.prompt();
                return;
            }

            // Process the query with the agent
            console.log(`\n?? Processing: "${query}"`);
            console.log('??Thinking...\n');

            const startTime = Date.now();
            const response = await this.agent.executeTask(query, this.sessionId);
            const endTime = Date.now();

            console.log('?? Response:');
            console.log('?'.repeat(50));
            console.log(response);
            console.log('?'.repeat(50));
            console.log(`?梧?  Response time: ${endTime - startTime}ms`);

            // Show session stats
            const stats = this.sessionManager.getSessionStats(this.sessionId);
            if (stats) {
                console.log(`?? Session: ${stats.messageCount} messages, ${stats.duration.toFixed(1)}s`);
            }

        } catch (error) {
            console.error('??Error processing query:', error);
            console.log('? Try rephrasing your question or check the MCP bridge connection.');
        }

        console.log(''); // Empty line for readability
        this.rl.prompt();
    }

    private showHelp(): void {
        console.log('\n?? AI-Showmaker Commands:');
        console.log('?'.repeat(40));
        console.log('  help     - Show this help message');
        console.log('  status   - Show system status');
        console.log('  tools    - List available tools');
        console.log('  clear    - Clear conversation history');
        console.log('  exit     - Exit the application');
        console.log('');
        console.log('? Example queries (with LATS Search Agent):');
        console.log('  "What is 15 * 23?" ??Think: Need to calculate ??Act: Use calculate tool');
        console.log('  "Find information about TypeScript best practices" ??Think: Need to search ??Act: Use search_web tool');
        console.log('  "Create a todo list for learning Python" ??Think: Need to create todos ??Act: Use create_todos tool');
        console.log('  "Set a variable called username to John" ??Think: Need to set variable ??Act: Use set_variable tool');
        console.log('  "List all files in the current directory" ??Think: Need to list files ??Act: Use list_directory tool');
        console.log('');
    }

    private showStatus(): void {
        console.log('\n?? System Status:');
        console.log('?'.repeat(40));
        console.log(`  MCP Tools: ${this.mcpClient.getTools().length} available`);
        console.log(`  Session: ${this.sessionId}`);
        
        const stats = this.sessionManager.getSessionStats(this.sessionId);
        if (stats) {
            console.log(`  Messages: ${stats.messageCount} (${stats.userMessages} user, ${stats.assistantMessages} assistant)`);
            console.log(`  Duration: ${stats.duration.toFixed(1)}s`);
            console.log(`  Status: ${stats.status}`);
        }
        
        console.log(`  LLM Model: gpt-4o-mini (OpenAI)`);
        console.log('');
    }

    private showTools(): void {
        console.log('\n??儭? Available Tools:');
        console.log('?'.repeat(40));
        
        const tools = this.mcpClient.getTools();
        const toolsByCategory = new Map<string, string[]>();
        
        tools.forEach(tool => {
            // Categorize tools by name patterns
            let category = 'Other';
            if (tool.name.includes('calculate') || tool.name.includes('math')) {
                category = 'Math';
            } else if (tool.name.includes('search') || tool.name.includes('web')) {
                category = 'Web Search';
            } else if (tool.name.includes('todo') || tool.name.includes('task')) {
                category = 'Task Management';
            } else if (tool.name.includes('file') || tool.name.includes('create') || tool.name.includes('read')) {
                category = 'File Operations';
            } else if (tool.name.includes('variable') || tool.name.includes('set') || tool.name.includes('get')) {
                category = 'Variables';
            }
            
            if (!toolsByCategory.has(category)) {
                toolsByCategory.set(category, []);
            }
            toolsByCategory.get(category)!.push(tool.name);
        });
        
        toolsByCategory.forEach((toolNames, category) => {
            console.log(`  ${category}:`);
            toolNames.forEach(name => {
                console.log(`    - ${name}`);
            });
        });
        console.log('');
    }

    private clearSession(): void {
        this.sessionId = this.sessionManager.createSession('Interactive Session').id;
        console.log('?完 Session cleared. New session started.');
    }

    private showEnhancedState(): void {
        console.log('\n?? Enhanced Agent State:');
        console.log('?'.repeat(40));
        
        const state = this.agent.getState();
        console.log(`  Current Iteration: ${state.iteration}`);
        console.log(`  Frontier Size: ${state.frontier.length}`);
        console.log(`  Scratchpad Size: ${state.scratchpad.length}`);
        console.log(`  Validator Interactions: ${state.metrics.validatorInteractions}`);
        console.log(`  Success Rate: ${(state.metrics.successRate * 100).toFixed(1)}%`);
        console.log(`  Average Execution Time: ${state.metrics.averageExecutionTime.toFixed(0)}ms`);
        console.log(`  Prediction Accuracy: ${(state.metrics.predictionAccuracy * 100).toFixed(1)}%`);
        
        if (state.validatorState.lastValidation) {
            const lastVal = state.validatorState.lastValidation;
            console.log(`  Last Validation: completed=${lastVal.completed}, confidence=${lastVal.confidence.toFixed(2)}`);
        }
        
        if (state.validatorState.hints.length > 0) {
            console.log(`  Validator Hints: ${state.validatorState.hints.join(', ')}`);
        }
        
        console.log('');
    }

    private showScenarioCache(): void {
        console.log('\n?? Scenario Prediction Cache:');
        console.log('?'.repeat(40));
        
        const cache = this.agent.getScenarioCache();
        if (cache.size === 0) {
            console.log('  No scenario predictions cached yet.');
            return;
        }

        cache.forEach((prediction, _key) => {
            console.log(`  Tool: ${prediction.tool}`);
            console.log(`  Confidence: ${(prediction.confidence * 100).toFixed(1)}%`);
            console.log(`  Scenarios: ${prediction.scenarios.map(s => `${s.type}(${(s.probability * 100).toFixed(0)}%)`).join(', ')}`);
            console.log(`  Cached: ${new Date(prediction.timestamp).toLocaleTimeString()}`);
            console.log('');
        });
    }
}

// Main execution
async function main() {
    const app = new InteractiveApp();
    await app.start();
}

// Handle graceful shutdown
process.on('SIGINT', () => {
    console.log('\n?? Goodbye! Thanks for using AI-Showmaker!');
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('\n?? Goodbye! Thanks for using AI-Showmaker!');
    process.exit(0);
});

// Start the app
if (require.main === module) {
    main().catch(error => {
        console.error('??Fatal error:', error);
        process.exit(1);
    });
}
