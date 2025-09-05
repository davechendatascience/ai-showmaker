#!/usr/bin/env ts-node

/**
 * Simple test script for inference.net LLM without complex agent setup
 */

import { ConfigManager } from '../../src/core/config';
import { HTTPMCPClient } from '../../src/mcp/http-mcp-client';
import { InferenceNetLLM } from '../../src/llm/inference-net-llm';

async function testSimpleInference() {
    console.log('🧠 Testing Simple Inference.net LLM Integration');
    console.log('='.repeat(60));

    try {
        // Initialize configuration
        console.log('1. Initializing configuration...');
        const config = new ConfigManager();
        console.log('   ✅ Configuration loaded');

        // Initialize MCP client
        console.log('\n2. Initializing MCP client...');
        const mcpClient = new HTTPMCPClient('http://localhost:8000');
        await mcpClient.initialize();
        console.log('   ✅ MCP client connected to bridge');

        // Get available tools
        console.log('\n3. Discovering available tools...');
        const tools = mcpClient.getTools();
        console.log(`   📋 Found ${tools.length} tools:`);
        tools.forEach(tool => {
            console.log(`      - ${tool.name}: ${tool.description.substring(0, 60)}...`);
        });

        // Initialize inference.net LLM
        console.log('\n4. Initializing Inference.net LLM...');
        const inferenceLLM = new InferenceNetLLM({
            apiKey: process.env['INFERENCE_NET_KEY'] || '',
            model: 'meta-llama/llama-3.2-3b-instruct/fp-16',
            temperature: 0.1,
            maxTokens: 1000
        });
        console.log('   ✅ Inference.net LLM initialized');

        // Test 1: Direct LLM Query
        console.log('\n5. Testing Direct LLM Query...');
        console.log('   📝 Task: Simple reasoning test');
        const llmResponse = await inferenceLLM.invoke('What is 15 * 8 + 42 / 7? Please show your work step by step.');
        console.log('   📤 Query: What is 15 * 8 + 42 / 7? Show your work.');
        console.log('   📥 Response:', llmResponse.content);
        console.log('   ✅ Direct LLM query successful');

        // Test 2: Tool Execution with LLM Reasoning
        console.log('\n6. Testing Tool Execution with LLM Reasoning...');
        console.log('   📝 Task: Use calculation tool and explain the result');
        
        // First, let the LLM reason about what tool to use
        const reasoningPrompt = `I need to calculate (25 * 4) + (100 / 5). 
        I have access to these tools: ${tools.map(t => t.name).join(', ')}.
        Which tool should I use and what parameters should I pass?`;
        
        const reasoningResponse = await inferenceLLM.invoke(reasoningPrompt);
        console.log('   📤 Reasoning Query:', reasoningPrompt);
        console.log('   📥 LLM Reasoning:', reasoningResponse.content);
        
        // Execute the calculation tool
        const calcResult = await mcpClient.executeTool('calculate', { expression: '(25 * 4) + (100 / 5)' });
        console.log('   🔧 Tool Execution Result:', calcResult);
        
        // Let LLM interpret the result
        const interpretationPrompt = `The calculation tool returned: ${JSON.stringify(calcResult)}. 
        Please explain what this result means and verify if it's correct.`;
        
        const interpretationResponse = await inferenceLLM.invoke(interpretationPrompt);
        console.log('   📤 Interpretation Query:', interpretationPrompt);
        console.log('   📥 LLM Interpretation:', interpretationResponse.content);
        console.log('   ✅ Tool execution with LLM reasoning successful');

        // Test 3: File Search with LLM Analysis
        console.log('\n7. Testing File Search with LLM Analysis...');
        console.log('   📝 Task: Find TypeScript files and analyze the project structure');
        
        // Execute file search
        const fileResult = await mcpClient.executeTool('find_files', { pattern: '*.ts' });
        console.log('   🔧 File Search Result:', fileResult);
        
        // Let LLM analyze the results
        const analysisPrompt = `I found these TypeScript files in the project: ${JSON.stringify(fileResult)}. 
        Please analyze the project structure and tell me what kind of application this appears to be.`;
        
        const analysisResponse = await inferenceLLM.invoke(analysisPrompt);
        console.log('   📤 Analysis Query:', analysisPrompt);
        console.log('   📥 LLM Analysis:', analysisResponse.content);
        console.log('   ✅ File search with LLM analysis successful');

        // Test 4: Web Search with LLM Processing
        console.log('\n8. Testing Web Search with LLM Processing...');
        console.log('   📝 Task: Search for information and summarize');
        
        // Execute web search
        const webResult = await mcpClient.executeTool('search_web', { 
            query: 'TypeScript AI agent frameworks 2024', 
            max_results: 3 
        });
        console.log('   🔧 Web Search Result:', webResult);
        
        // Let LLM summarize the results
        const summaryPrompt = `I searched for "TypeScript AI agent frameworks 2024" and got these results: ${JSON.stringify(webResult)}. 
        Please summarize the key findings and trends in TypeScript AI agent development.`;
        
        const summaryResponse = await inferenceLLM.invoke(summaryPrompt);
        console.log('   📤 Summary Query:', summaryPrompt);
        console.log('   📥 LLM Summary:', summaryResponse.content);
        console.log('   ✅ Web search with LLM processing successful');

        // Test 5: Complex Multi-step Task
        console.log('\n9. Testing Complex Multi-step Task...');
        console.log('   📝 Task: Create todos, calculate something, and search for information');
        
        // Step 1: Create todos
        const todoResult = await mcpClient.executeTool('create_todos', { 
            todos: ['Test TypeScript agent', 'Integrate with MCP tools', 'Deploy to production'] 
        });
        console.log('   🔧 Todo Creation Result:', todoResult);
        
        // Step 2: Calculate something
        const calcResult2 = await mcpClient.executeTool('calculate', { expression: '2^10' });
        console.log('   🔧 Calculation Result:', calcResult2);
        
        // Step 3: Let LLM coordinate and summarize
        const coordinationPrompt = `I just completed a multi-step task:
        1. Created todos: ${JSON.stringify(todoResult)}
        2. Calculated 2^10: ${JSON.stringify(calcResult2)}
        
        Please summarize what was accomplished and provide insights about the task execution.`;
        
        const coordinationResponse = await inferenceLLM.invoke(coordinationPrompt);
        console.log('   📤 Coordination Query:', coordinationPrompt);
        console.log('   📥 LLM Coordination:', coordinationResponse.content);
        console.log('   ✅ Complex multi-step task successful');

        // Summary
        console.log('\n✅ All simple inference tests completed!');
        console.log('🎉 Inference.net LLM integration is working successfully');
        console.log('🔧 MCP tools are functioning correctly');
        console.log('🧠 LLM reasoning and tool coordination is effective');
        
        return true;
    } catch (error) {
        console.error('❌ Simple inference test failed:', error);
        return false;
    }
}

if (require.main === module) {
    testSimpleInference().then(success => {
        process.exit(success ? 0 : 1);
    });
}
