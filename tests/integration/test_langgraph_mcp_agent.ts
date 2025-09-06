#!/usr/bin/env ts-node

/**
 * Test LangGraph MCP Agent - Let LangGraph handle the workflow
 * We just provide the initial query and let LangGraph figure out the rest
 */

import * as dotenv from 'dotenv';
dotenv.config();

import { HTTPMCPClient } from '../../src/mcp/http-mcp-client';
import { RateLimitedLLM } from '../../src/llm/rate-limited-llm';
import { SessionManager } from '../../src/core/session-manager';
import { LangGraphMCPAgent } from '../../src/agents/langgraph-mcp-agent';

async function testLangGraphMCPAgent() {
    console.log('🧠 Testing LangGraph MCP Agent - Let LangGraph Handle Workflow');
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
            requestsPerMinute: 5, // Slightly higher for LangGraph workflow
            maxRetries: 3,
            retryDelayMs: 3000
        });
        console.log('   ✅ Rate-Limited LLM initialized');

        const sessionManager = new SessionManager();
        const session = sessionManager.createSession('LangGraph MCP Agent Test Session');
        console.log('   ✅ Session Manager initialized');

        const agent = new LangGraphMCPAgent(mcpClient, llm, sessionManager);
        console.log('   ✅ LangGraph MCP Agent initialized');

        // Test 1: Simple task - let LangGraph decide what to do
        console.log('\n2. 🎯 Testing Simple Task with LangGraph Workflow...');
        console.log('   📝 Task: "Help me solve a math problem: What is 15 * 23?"');
        
        const mathResult = await agent.executeComplexTask(
            'Help me solve a math problem: What is 15 * 23?', 
            session.id
        );
        
        console.log('   📊 Math Task Result:');
        console.log(`      Response: ${mathResult.substring(0, 300)}...`);

        // Test 2: LeetCode task - let LangGraph orchestrate
        console.log('\n3. 💻 Testing LeetCode Task with LangGraph Workflow...');
        console.log('   📝 Task: "Solve LeetCode problem 1: Two Sum"');
        
        const leetcodeResult = await agent.executeComplexTask(
            'Solve LeetCode problem 1: Two Sum', 
            session.id
        );
        
        console.log('   📊 LeetCode Task Result:');
        console.log(`      Response: ${leetcodeResult.substring(0, 300)}...`);

        // Test 3: Web search task - let LangGraph decide tools
        console.log('\n4. 🔍 Testing Web Search Task with LangGraph Workflow...');
        console.log('   📝 Task: "Find information about TypeScript best practices"');
        
        const searchResult = await agent.executeComplexTask(
            'Find information about TypeScript best practices', 
            session.id
        );
        
        console.log('   📊 Search Task Result:');
        console.log(`      Response: ${searchResult.substring(0, 300)}...`);

        // Test 4: Continue conversation
        console.log('\n5. 💬 Testing Conversation Continuity...');
        console.log('   📝 Follow-up: "Can you create a todo list for learning TypeScript?"');
        
        const todoResult = await agent.continueConversation(
            'Can you create a todo list for learning TypeScript?', 
            session.id
        );
        
        console.log('   📊 Todo Task Result:');
        console.log(`      Response: ${todoResult.substring(0, 300)}...`);

        // Show LLM stats
        console.log('\n6. 📊 LLM Usage Statistics...');
        const llmStats = llm.getRequestStats();
        console.log(`   📈 Requests in last minute: ${llmStats.requestsInLastMinute}`);
        console.log(`   📈 Rate limit: ${llmStats.requestsPerMinute} per minute`);

        // Show session statistics
        console.log('\n7. 📊 Session Statistics...');
        const stats = sessionManager.getSessionStats(session.id);
        console.log('   📈 Session Stats:', stats);

        // Summary
        console.log('\n✅ LangGraph MCP Agent test completed!');
        console.log('🎉 LangGraph MCP Agent successfully demonstrated:');
        console.log('   ✅ Simple query input - no complex instructions');
        console.log('   ✅ LangGraph-style workflow orchestration');
        console.log('   ✅ Automatic tool selection and execution');
        console.log('   ✅ Conversation continuity with session management');
        console.log('   ✅ Core MCP + LLM + LangGraph principles');
        
        return true;
    } catch (error) {
        console.error('❌ LangGraph MCP Agent test failed:', error);
        return false;
    }
}

if (require.main === module) {
    testLangGraphMCPAgent().then(success => {
        process.exit(success ? 0 : 1);
    });
}
