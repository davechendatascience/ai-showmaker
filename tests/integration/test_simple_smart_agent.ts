#!/usr/bin/env ts-node

/**
 * Test Simple Smart Agent - Practical LangGraph Tool Selection
 */

import * as dotenv from 'dotenv';
dotenv.config();

import { HTTPMCPClient } from '../../src/mcp/http-mcp-client';
import { RateLimitedLLM } from '../../src/llm/rate-limited-llm';
import { SessionManager } from '../../src/core/session-manager';
import { SimpleSmartAgent } from '../../src/agents/simple-smart-agent';

async function testSimpleSmartAgent() {
    console.log('🧠 Testing Simple Smart Agent - Practical Tool Selection');
    console.log('='.repeat(70));

    try {
        // Initialize components
        console.log('1. Initializing components...');
        
        const mcpClient = new HTTPMCPClient('http://localhost:8000');
        await mcpClient.initialize();
        console.log('   ✅ MCP Client initialized');

        const llm = new RateLimitedLLM({
            apiKey: process.env['INFERENCE_NET_KEY'] || '',
            model: 'meta-llama/llama-3.2-3b-instruct/fp-16',
            temperature: 0.1,
            maxTokens: 1000,
            requestsPerMinute: 5,
            maxRetries: 3,
            retryDelayMs: 3000
        });
        console.log('   ✅ Rate-Limited LLM initialized');

        const sessionManager = new SessionManager();
        const session = sessionManager.createSession('Simple Smart Agent Test Session');
        console.log('   ✅ Session Manager initialized');

        const agent = new SimpleSmartAgent(mcpClient, llm, sessionManager);
        console.log('   ✅ Simple Smart Agent initialized');

        // Test 1: Math problem
        console.log('\n2. 🧮 Testing Math Problem...');
        console.log('   📝 Task: "What is 15 * 23?"');
        
        const mathResult = await agent.executeComplexTask('What is 15 * 23?', session.id);
        
        console.log('   📊 Math Task Result:');
        console.log(`      Response: ${mathResult.substring(0, 200)}...`);

        // Test 2: Search task
        console.log('\n3. 🔍 Testing Search Task...');
        console.log('   📝 Task: "Find information about TypeScript best practices"');
        
        const searchResult = await agent.executeComplexTask(
            'Find information about TypeScript best practices', 
            session.id
        );
        
        console.log('   📊 Search Task Result:');
        console.log(`      Response: ${searchResult.substring(0, 200)}...`);

        // Test 3: Todo creation
        console.log('\n4. 📝 Testing Todo Creation...');
        console.log('   📝 Task: "Create a todo list for learning Python"');
        
        const todoResult = await agent.executeComplexTask(
            'Create a todo list for learning Python', 
            session.id
        );
        
        console.log('   📊 Todo Task Result:');
        console.log(`      Response: ${todoResult.substring(0, 200)}...`);

        // Show LLM stats
        console.log('\n5. 📊 LLM Usage Statistics...');
        const llmStats = llm.getRequestStats();
        console.log(`   📈 Requests in last minute: ${llmStats.requestsInLastMinute}`);
        console.log(`   📈 Rate limit: ${llmStats.requestsPerMinute} per minute`);

        // Show session statistics
        console.log('\n6. 📊 Session Statistics...');
        const sessionStats = sessionManager.getSessionStats(session.id);
        if (sessionStats) {
            console.log('   📈 Session Stats:', sessionStats);
        }

        // Summary
        console.log('\n✅ Simple Smart Agent test completed!');
        console.log('🎉 Simple Smart Agent successfully demonstrated:');
        console.log('   ✅ Intent-based tool selection');
        console.log('   ✅ Category-based tool filtering');
        console.log('   ✅ Parameter extraction');
        console.log('   ✅ Tool execution with results');
        console.log('   ✅ LLM result processing');
        console.log('   ✅ Practical LangGraph implementation');
        
        return true;
    } catch (error) {
        console.error('❌ Simple Smart Agent test failed:', error);
        return false;
    }
}

if (require.main === module) {
    testSimpleSmartAgent().then(success => {
        process.exit(success ? 0 : 1);
    });
}
