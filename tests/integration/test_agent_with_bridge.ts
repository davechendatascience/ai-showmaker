#!/usr/bin/env ts-node

/**
 * Test script to verify TypeScript agent integration with MCP bridge
 */

import { ConfigManager } from '../../src/core/config';
import { AIAgent } from '../../src/core/agent';
import { HTTPMCPClient } from '../../src/mcp/http-mcp-client';

async function testAgentWithBridge() {
    console.log('🔧 Testing TypeScript Agent with MCP Bridge');
    console.log('='.repeat(50));

    try {
        // Initialize configuration
        console.log('1. Initializing configuration...');
        const config = new ConfigManager();
        // Config is already loaded in constructor
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
            serverTools.forEach((tool: any) => {
                console.log(`      - ${tool.name}: ${tool.description.substring(0, 60)}...`);
            });
        }

        // Initialize agent
        console.log('\n4. Initializing AI Agent...');
        const agent = new AIAgent(config);
        await agent.initialize();
        console.log('   ✅ Agent initialized');

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

        // Test complex multi-step task
        console.log('\n9. Testing complex multi-step task...');
        const complexResult = await agent.query('Calculate 25 * 4, then search for Python tutorials, and create a todo to learn more');
        console.log('   📤 Query: Calculate 25 * 4, then search for Python tutorials, and create a todo to learn more');
        console.log(`   📥 Response: ${complexResult}`);

        console.log('\n🎉 All agent tests completed successfully!');
        return true;

    } catch (error) {
        console.error('❌ Test failed:', error);
        return false;
    }
}

// Run the test
if (require.main === module) {
    testAgentWithBridge()
        .then(success => {
            process.exit(success ? 0 : 1);
        })
        .catch(error => {
            console.error('❌ Test runner failed:', error);
            process.exit(1);
        });
}

export { testAgentWithBridge };
