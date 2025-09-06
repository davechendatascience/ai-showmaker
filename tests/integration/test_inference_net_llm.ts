#!/usr/bin/env ts-node

/**
 * Test script to verify TypeScript agent with inference.net LLM
 */

import { ConfigManager } from '../../src/core/config';
import { AIAgent } from '../../src/core/agent';
import { HTTPMCPClient } from '../../src/mcp/http-mcp-client';
import { InferenceNetLLM } from '../../src/llm/inference-net-llm';

async function testInferenceNetLLM() {
    console.log('🔧 Testing TypeScript Agent with Inference.net LLM');
    console.log('='.repeat(50));

    try {
        // Initialize configuration
        console.log('1. Initializing configuration...');
        const config = new ConfigManager();
        console.log('   ✅ Configuration loaded');

        // Check for required environment variables
        const inferenceNetKey = process.env['INFERENCE_NET_KEY'];
        if (!inferenceNetKey) {
            console.error('❌ INFERENCE_NET_KEY environment variable is required');
            console.log('   Please set INFERENCE_NET_KEY in your .env file');
            return false;
        }

        // Initialize MCP client
        console.log('\n2. Initializing MCP client...');
        const mcpClient = new HTTPMCPClient('http://localhost:8000');
        await mcpClient.initialize();
        console.log('   ✅ MCP client connected to bridge');

        // Get available tools
        console.log('\n3. Discovering available tools...');
        const toolsByServer = await mcpClient.getAllToolsByServer();
        const totalTools = Object.values(toolsByServer).reduce((sum, tools) => sum + tools.length, 0);
        console.log(`   📋 Found ${totalTools} tools across all servers:`);
        
        for (const [serverName, serverTools] of Object.entries(toolsByServer)) {
            console.log(`   📦 ${serverName}: ${serverTools.length} tools`);
        }

        // Initialize agent with inference.net LLM
        console.log('\n4. Initializing AI Agent with Inference.net LLM...');
        const agent = new AIAgent(config);
        
        // Create and set the inference.net LLM
        const inferenceNetLLM = new InferenceNetLLM({
            apiKey: inferenceNetKey,
            model: 'meta-llama/llama-3.2-3b-instruct/fp-16',
            temperature: 0.1,
            maxTokens: 1000
        });
        
        // Set the inference.net LLM in the agent
        agent.setLLM(inferenceNetLLM);
        
        // Now initialize the agent (this will use our inference.net LLM)
        await agent.initialize();
        console.log('   ✅ Agent initialized with inference.net LLM');

        // Test simple calculation
        console.log('\n5. Testing simple calculation...');
        const calcResult = await agent.query('What is 15 * 8?');
        console.log('   📤 Query: What is 15 * 8?');
        console.log(`   📥 Response: ${calcResult}`);

        // Test file search
        console.log('\n6. Testing file search...');
        const searchResult = await agent.query('Find all Python files in the current directory');
        console.log('   📤 Query: Find all Python files in the current directory');
        console.log(`   📥 Response: ${searchResult}`);

        // Test web search
        console.log('\n7. Testing web search...');
        const webResult = await agent.query('Search for information about TypeScript best practices');
        console.log('   📤 Query: Search for information about TypeScript best practices');
        console.log(`   📥 Response: ${webResult}`);

        // Test todo management
        console.log('\n8. Testing todo management...');
        const todoResult = await agent.query('Create a todo list with: 1. Review code, 2. Write tests, 3. Deploy');
        console.log('   📤 Query: Create a todo list with: 1. Review code, 2. Write tests, 3. Deploy');
        console.log(`   📥 Response: ${todoResult}`);

        console.log('\n🎉 All inference.net LLM tests completed successfully!');
        return true;

    } catch (error) {
        console.error('❌ Test failed:', error);
        return false;
    }
}

// Run the test
if (require.main === module) {
    testInferenceNetLLM()
        .then(success => {
            process.exit(success ? 0 : 1);
        })
        .catch(error => {
            console.error('❌ Test runner failed:', error);
            process.exit(1);
        });
}

export { testInferenceNetLLM };
