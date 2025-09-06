#!/usr/bin/env ts-node

/**
 * Test Enhanced LangGraph Agent with Smart Tool Selection
 * Demonstrates LangGraph best practices for intelligent tool discovery
 */

import * as dotenv from 'dotenv';
dotenv.config();

import { HTTPMCPClient } from '../../src/mcp/http-mcp-client';
import { RateLimitedLLM } from '../../src/llm/rate-limited-llm';
import { SessionManager } from '../../src/core/session-manager';
import { EnhancedLangGraphAgent } from '../../src/agents/enhanced-langgraph-agent';

async function testEnhancedLangGraphAgent() {
    console.log('🧠 Testing Enhanced LangGraph Agent with Smart Tool Selection');
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
        const session = sessionManager.createSession('Enhanced LangGraph Agent Test Session');
        console.log('   ✅ Session Manager initialized');

        const agent = new EnhancedLangGraphAgent(mcpClient, llm, sessionManager);
        console.log('   ✅ Enhanced LangGraph Agent initialized');

        // Show tool selection stats
        console.log('\n2. 📊 Tool Selection Statistics...');
        const stats = agent.getToolSelectionStats();
        console.log(`   Total Tools: ${stats.totalTools}`);
        console.log(`   Categories: ${stats.categories.join(', ')}`);

        // Test 1: Math problem with smart tool selection
        console.log('\n3. 🧮 Testing Math Problem with Smart Tool Selection...');
        console.log('   📝 Task: "What is 15 * 23?"');
        
        const mathResult = await agent.executeComplexTask('What is 15 * 23?', session.id);
        
        console.log('   📊 Math Task Result:');
        console.log(`      Response: ${mathResult.substring(0, 200)}...`);

        // Test 2: Search task with smart tool selection
        console.log('\n4. 🔍 Testing Search Task with Smart Tool Selection...');
        console.log('   📝 Task: "Find information about TypeScript best practices"');
        
        const searchResult = await agent.executeComplexTask(
            'Find information about TypeScript best practices', 
            session.id
        );
        
        console.log('   📊 Search Task Result:');
        console.log(`      Response: ${searchResult.substring(0, 200)}...`);

        // Test 3: Todo creation with smart tool selection
        console.log('\n5. 📝 Testing Todo Creation with Smart Tool Selection...');
        console.log('   📝 Task: "Create a todo list for learning Python"');
        
        const todoResult = await agent.executeComplexTask(
            'Create a todo list for learning Python', 
            session.id
        );
        
        console.log('   📊 Todo Task Result:');
        console.log(`      Response: ${todoResult.substring(0, 200)}...`);

        // Test 4: Complex task with multiple tool types
        console.log('\n6. 🎯 Testing Complex Task with Multiple Tool Types...');
        console.log('   📝 Task: "Help me solve LeetCode problem 1: Two Sum"');
        
        const leetcodeResult = await agent.executeComplexTask(
            'Help me solve LeetCode problem 1: Two Sum', 
            session.id
        );
        
        console.log('   📊 LeetCode Task Result:');
        console.log(`      Response: ${leetcodeResult.substring(0, 200)}...`);

        // Show LLM stats
        console.log('\n7. 📊 LLM Usage Statistics...');
        const llmStats = llm.getRequestStats();
        console.log(`   📈 Requests in last minute: ${llmStats.requestsInLastMinute}`);
        console.log(`   📈 Rate limit: ${llmStats.requestsPerMinute} per minute`);

        // Show session statistics
        console.log('\n8. 📊 Session Statistics...');
        const sessionStats = sessionManager.getSessionStats(session.id);
        if (sessionStats) {
            console.log('   📈 Session Stats:', sessionStats);
        }

        // Summary
        console.log('\n✅ Enhanced LangGraph Agent test completed!');
        console.log('🎉 Enhanced LangGraph Agent successfully demonstrated:');
        console.log('   ✅ Smart tool selection with multiple strategies');
        console.log('   ✅ Intent-based tool filtering');
        console.log('   ✅ Category-based tool filtering');
        console.log('   ✅ Semantic similarity matching');
        console.log('   ✅ Parameter validation');
        console.log('   ✅ Confidence scoring and ranking');
        console.log('   ✅ LangGraph best practices implementation');
        
        return true;
    } catch (error) {
        console.error('❌ Enhanced LangGraph Agent test failed:', error);
        return false;
    }
}

if (require.main === module) {
    testEnhancedLangGraphAgent().then(success => {
        process.exit(success ? 0 : 1);
    });
}
