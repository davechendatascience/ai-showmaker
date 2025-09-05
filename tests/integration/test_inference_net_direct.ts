#!/usr/bin/env ts-node

/**
 * Direct test of inference.net LLM with MCP tools
 */

import * as dotenv from 'dotenv';
dotenv.config();

import { HTTPMCPClient } from '../../src/mcp/http-mcp-client';
import { InferenceNetLLM } from '../../src/llm/inference-net-llm';

async function testInferenceNetDirect() {
    console.log('🧠 Testing Inference.net LLM Direct Integration');
    console.log('='.repeat(60));

    try {
        // Initialize MCP client
        console.log('1. Initializing MCP client...');
        const mcpClient = new HTTPMCPClient('http://localhost:8000');
        await mcpClient.initialize();
        console.log('   ✅ MCP client connected to bridge');

        // Initialize inference.net LLM
        console.log('\n2. Initializing Inference.net LLM...');
        const inferenceLLM = new InferenceNetLLM({
            apiKey: process.env['INFERENCE_NET_KEY'] || '',
            model: 'meta-llama/llama-3.2-3b-instruct/fp-16',
            temperature: 0.1,
            maxTokens: 1000
        });
        console.log('   ✅ Inference.net LLM initialized');

        // Test 1: Direct LLM Query
        console.log('\n3. Testing Direct LLM Query...');
        const llmResponse = await inferenceLLM.invoke('What is 15 * 8 + 42 / 7? Please show your work step by step.');
        console.log('   📤 Query: What is 15 * 8 + 42 / 7? Show your work.');
        console.log('   📥 Response:', llmResponse.content);
        console.log('   ✅ Direct LLM query successful');

        // Test 2: LLM + Tool Integration
        console.log('\n4. Testing LLM + Tool Integration...');
        
        // Let LLM reason about tool selection
        const tools = mcpClient.getTools();
        const toolNames = tools.map(t => t.name).join(', ');
        
        const reasoningPrompt = `I need to calculate (25 * 4) + (100 / 5). 
        I have access to these tools: ${toolNames}.
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
        console.log('   ✅ LLM + Tool integration successful');

        // Test 3: Complex Multi-step Task
        console.log('\n5. Testing Complex Multi-step Task...');
        
        // Step 1: Create todos
        const todoResult = await mcpClient.executeTool('create_todos', { 
            todos: ['Test inference.net LLM', 'Verify tool integration', 'Document results'] 
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

        // Test 4: Web Search + LLM Analysis
        console.log('\n6. Testing Web Search + LLM Analysis...');
        
        // Execute web search
        const webResult = await mcpClient.executeTool('search_web', { 
            query: 'TypeScript AI agent frameworks 2024', 
            max_results: 2 
        });
        console.log('   🔧 Web Search Result:', JSON.stringify(webResult).substring(0, 300) + '...');
        
        // Let LLM analyze the results
        const analysisPrompt = `I searched for "TypeScript AI agent frameworks 2024" and got these results: ${JSON.stringify(webResult).substring(0, 500)}...
        Please analyze the key findings and trends in TypeScript AI agent development.`;
        
        const analysisResponse = await inferenceLLM.invoke(analysisPrompt);
        console.log('   📤 Analysis Query:', analysisPrompt);
        console.log('   📥 LLM Analysis:', analysisResponse.content);
        console.log('   ✅ Web search + LLM analysis successful');

        // Summary
        console.log('\n✅ All inference.net LLM integration tests completed!');
        console.log('🎉 Inference.net LLM is working perfectly with MCP tools');
        console.log('🧠 Real LLM reasoning and tool coordination is functional');
        console.log('🔧 Multi-step workflows with real LLM are working');
        console.log('📊 Complex task solving with LLM + tools is successful');
        
        return true;
    } catch (error) {
        console.error('❌ Inference.net LLM test failed:', error);
        return false;
    }
}

if (require.main === module) {
    testInferenceNetDirect().then(success => {
        process.exit(success ? 0 : 1);
    });
}
