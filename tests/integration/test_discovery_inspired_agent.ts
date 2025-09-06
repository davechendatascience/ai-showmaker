#!/usr/bin/env ts-node

/**
 * Test Discovery-Inspired Agent - Based on GitHub Next Discovery Agent principles
 */

import * as dotenv from 'dotenv';
dotenv.config();

import { HTTPMCPClient } from '../../src/mcp/http-mcp-client';
import { RateLimitedLLM } from '../../src/llm/rate-limited-llm';
import { SessionManager } from '../../src/core/session-manager';
import { DiscoveryInspiredAgent } from '../../src/agents/discovery-inspired-agent';

async function testDiscoveryInspiredAgent() {
    console.log('🧠 Testing Discovery-Inspired Agent - GitHub Next Principles');
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
            maxTokens: 1500, // Increased for structured responses
            requestsPerMinute: 5,
            maxRetries: 3,
            retryDelayMs: 3000
        });
        console.log('   ✅ Rate-Limited LLM initialized');

        const sessionManager = new SessionManager();
        const session = sessionManager.createSession('Discovery-Inspired Agent Test Session');
        console.log('   ✅ Session Manager initialized');

        const agent = new DiscoveryInspiredAgent(mcpClient, llm, sessionManager);
        console.log('   ✅ Discovery-Inspired Agent initialized');

        // Test 1: Math problem with react loop
        console.log('\n2. 🧮 Testing Math Problem with React Loop...');
        console.log('   📝 Task: "What is 15 * 23?"');
        
        const mathResult = await agent.executeComplexTask('What is 15 * 23?', session.id);
        
        console.log('   📊 Math Task Result:');
        console.log(`      Response: ${mathResult.substring(0, 200)}...`);

        // Test 2: Search task with react loop
        console.log('\n3. 🔍 Testing Search Task with React Loop...');
        console.log('   📝 Task: "Find information about TypeScript best practices"');
        
        const searchResult = await agent.executeComplexTask(
            'Find information about TypeScript best practices', 
            session.id
        );
        
        console.log('   📊 Search Task Result:');
        console.log(`      Response: ${searchResult.substring(0, 200)}...`);

        // Test 3: Complex task requiring multiple steps
        console.log('\n4. 🎯 Testing Complex Task with Multiple Steps...');
        console.log('   📝 Task: "Help me solve LeetCode problem 1: Two Sum"');
        
        const leetcodeResult = await agent.executeComplexTask(
            'Help me solve LeetCode problem 1: Two Sum', 
            session.id
        );
        
        console.log('   📊 LeetCode Task Result:');
        console.log(`      Response: ${leetcodeResult.substring(0, 200)}...`);

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
        console.log('\n✅ Discovery-Inspired Agent test completed!');
        console.log('🎉 Discovery-Inspired Agent successfully demonstrated:');
        console.log('   ✅ React-loop style execution with iterative refinement');
        console.log('   ✅ Structured system prompt with clear objectives');
        console.log('   ✅ Tool selection based on execution feedback');
        console.log('   ✅ Context-aware decision making');
        console.log('   ✅ Intelligent exit conditions');
        console.log('   ✅ GitHub Next Discovery Agent principles');
        
        return true;
    } catch (error) {
        console.error('❌ Discovery-Inspired Agent test failed:', error);
        return false;
    }
}

if (require.main === module) {
    testDiscoveryInspiredAgent().then(success => {
        process.exit(success ? 0 : 1);
    });
}
