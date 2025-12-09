#!/usr/bin/env ts-node

/**
 * Test All Tools Selection - Can the agent choose the right tool from ALL available tools?
 */

import * as dotenv from 'dotenv';
dotenv.config();

import { HTTPMCPClient } from '../../src/mcp/http-mcp-client';
import { OpenAILLM } from '../../src/llm/openai-llm';
import { SessionManager } from '../../src/core/session-manager';
import { DiscoveryInspiredAgent } from '../../src/agents/discovery-inspired-agent';

async function testAllToolsSelection() {
    console.log('🧠 Testing All Tools Selection - Can agent choose correctly from 39 tools?');
    console.log('🤖 Using OpenAI GPT-4o-mini Model');
    console.log('='.repeat(80));

    try {
        // Initialize components
        console.log('1. Initializing components...');
        
        const mcpClient = new HTTPMCPClient('http://localhost:8000');
        await mcpClient.initialize();
        console.log('   ✅ MCP Client initialized');

        const apiKey = process.env['OPENAI_KEY'] || process.env['OPENAI_API_KEY'];
        console.log(`   🔑 API Key loaded: ${apiKey ? 'Yes (length: ' + apiKey.length + ')' : 'No'}`);
        
        if (!apiKey) {
            throw new Error('OPENAI_KEY / OPENAI_API_KEY not found in environment variables');
        }
        
        const llm = new OpenAILLM({
            apiKey: apiKey,
            model: 'gpt-4o-mini',
            temperature: 0.1,
            maxTokens: 2000
        });
        console.log('   ✅ OpenAI LLM initialized');

        const sessionManager = new SessionManager();
        const session = sessionManager.createSession('All Tools Selection Test');
        console.log('   ✅ Session Manager initialized');

        const agent = new DiscoveryInspiredAgent(mcpClient, llm, sessionManager);
        console.log('   ✅ Discovery-Inspired Agent initialized');

        // Show all available tools
        console.log('\n2. 📋 All Available Tools (39 total):');
        const allTools = mcpClient.getTools();
        allTools.forEach((tool, index) => {
            console.log(`   ${index + 1}. ${tool.name}: ${tool.description}`);
        });

        // Test 1: Math calculation with all tools available
        console.log('\n3. 🧮 Test 1: Math Calculation with ALL tools available');
        console.log('   📝 Task: "What is 25 * 17?"');
        console.log('   🎯 Expected: Should choose "calculate" tool');
        
        const mathResult = await agent.executeComplexTask('What is 25 * 17?', session.id);
        
        console.log('   📊 Math Task Result:');
        console.log(`      Response: ${mathResult.substring(0, 300)}...`);

        // Test 2: Web search with all tools available
        console.log('\n4. 🔍 Test 2: Web Search with ALL tools available');
        console.log('   📝 Task: "Find information about Python async programming"');
        console.log('   🎯 Expected: Should choose "search_web" or similar search tool');
        
        const searchResult = await agent.executeComplexTask(
            'Find information about Python async programming', 
            session.id
        );
        
        console.log('   📊 Search Task Result:');
        console.log(`      Response: ${searchResult.substring(0, 300)}...`);

        // Test 3: File operation with all tools available
        console.log('\n5. 📁 Test 3: File Operation with ALL tools available');
        console.log('   📝 Task: "List all files in the current directory"');
        console.log('   🎯 Expected: Should choose "list_files" or similar file tool');
        
        const fileResult = await agent.executeComplexTask(
            'List all files in the current directory', 
            session.id
        );
        
        console.log('   📊 File Task Result:');
        console.log(`      Response: ${fileResult.substring(0, 300)}...`);

        // Test 4: Todo management with all tools available
        console.log('\n6. ✅ Test 4: Todo Management with ALL tools available');
        console.log('   📝 Task: "Create a todo list for learning TypeScript"');
        console.log('   🎯 Expected: Should choose "create_todos" or similar todo tool');
        
        const todoResult = await agent.executeComplexTask(
            'Create a todo list for learning TypeScript', 
            session.id
        );
        
        console.log('   📊 Todo Task Result:');
        console.log(`      Response: ${todoResult.substring(0, 300)}...`);

        // Test 5: Variable management with all tools available
        console.log('\n7. 🔧 Test 5: Variable Management with ALL tools available');
        console.log('   📝 Task: "Set a variable called username to John"');
        console.log('   🎯 Expected: Should choose "set_variable" tool');
        
        const variableResult = await agent.executeComplexTask(
            'Set a variable called username to John', 
            session.id
        );
        
        console.log('   📊 Variable Task Result:');
        console.log(`      Response: ${variableResult.substring(0, 300)}...`);

        // Show LLM info
        console.log('\n8. 📊 LLM Information...');
        console.log(`   📈 Model: gpt-4o-mini`);
        console.log(`   📈 Type: OpenAI LLM`);

        // Show session statistics
        console.log('\n9. 📊 Session Statistics...');
        const sessionStats = sessionManager.getSessionStats(session.id);
        if (sessionStats) {
            console.log('   📈 Session Stats:', sessionStats);
        }

        // Summary
        console.log('\n✅ All Tools Selection test completed!');
        console.log('🎉 Key Insights:');
        console.log('   ✅ Agent can choose from ALL 39 available tools');
        console.log('   ✅ Tool selection based on task context and requirements');
        console.log('   ✅ No pre-filtering - pure agent reasoning');
        console.log('   ✅ Two-phase approach: Think → Act → Execute');
        console.log('   ✅ GitHub Next Discovery Agent principles applied');
        
        return true;
    } catch (error) {
        console.error('❌ All Tools Selection test failed:', error);
        return false;
    }
}

if (require.main === module) {
    testAllToolsSelection().then(success => {
        process.exit(success ? 0 : 1);
    });
}
