#!/usr/bin/env ts-node

/**
 * Test script to verify TypeScript agent with mock LLM
 */

import { ConfigManager } from '../../src/core/config';
import { AIAgent } from '../../src/core/agent';
import { HTTPMCPClient } from '../../src/mcp/http-mcp-client';
import { MockLLM } from '../../src/llm/mock-llm';

async function testMockLLM() {
    console.log('🔧 Testing TypeScript Agent with Mock LLM');
    console.log('='.repeat(50));

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
        const toolsByServer = await mcpClient.getAllToolsByServer();
        const totalTools = Object.values(toolsByServer).reduce((sum, tools) => sum + tools.length, 0);
        console.log(`   📋 Found ${totalTools} tools across all servers:`);
        
        for (const [serverName, serverTools] of Object.entries(toolsByServer)) {
            console.log(`   📦 ${serverName}: ${serverTools.length} tools`);
        }

        // Initialize agent with mock LLM
        console.log('\n4. Initializing AI Agent with Mock LLM...');
        const agent = new AIAgent(config);
        
        // Create and set the mock LLM BEFORE initialization
        const mockLLM = new MockLLM({
            name: 'mock-llm',
            temperature: 0.1,
            maxTokens: 1000
        });
        
        // Set the mock LLM in the agent
        agent.setLLM(mockLLM);
        
        // Now initialize the agent (this will use our mock LLM)
        await agent.initialize();
        console.log('   ✅ Agent initialized with mock LLM');

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

        console.log('\n🎉 All mock LLM tests completed successfully!');
        return true;

    } catch (error) {
        console.error('❌ Test failed:', error);
        return false;
    }
}

// Run the test
if (require.main === module) {
    testMockLLM()
        .then(success => {
            process.exit(success ? 0 : 1);
        })
        .catch(error => {
            console.error('❌ Test runner failed:', error);
            process.exit(1);
        });
}

export { testMockLLM };
