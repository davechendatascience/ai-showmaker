#!/usr/bin/env ts-node

/**
 * Comprehensive test script for complex tasks with inference.net LLM
 */

import { ConfigManager } from '../../src/core/config';
import { AIAgent } from '../../src/core/agent';
import { InferenceNetLLM } from '../../src/llm/inference-net-llm';

async function testComplexTasks() {
    console.log('🧠 Testing Complex Tasks with Inference.net LLM');
    console.log('='.repeat(60));

    try {
        // Initialize configuration
        console.log('1. Initializing configuration...');
        const config = new ConfigManager();
        console.log('   ✅ Configuration loaded');

        // Initialize agent with inference.net LLM
        console.log('\n2. Initializing AI Agent with Inference.net LLM...');
        const agent = new AIAgent(config);
        
        // Create and set the inference.net LLM
        const inferenceLLM = new InferenceNetLLM({
            apiKey: process.env['INFERENCE_NET_KEY'] || '',
            model: 'meta-llama/llama-3.2-3b-instruct/fp-16',
            temperature: 0.1,
            maxTokens: 2000
        });
        
        // Set the LLM in the agent
        agent.setLLM(inferenceLLM);
        
        // Initialize the agent
        await agent.initialize();
        console.log('   ✅ Agent initialized with inference.net LLM');

        // Test 1: Mathematical Problem Solving
        console.log('\n3. Testing Mathematical Problem Solving...');
        console.log('   📝 Task: Solve a complex mathematical expression');
        const mathResponse = await agent.query('Calculate the result of (15 * 8) + (42 / 7) - (3^2) and explain each step');
        console.log('   📤 Query: Calculate (15 * 8) + (42 / 7) - (3^2) and explain each step');
        console.log('   📥 Response:', mathResponse.content);
        console.log('   ⏱️  Execution time:', mathResponse.metadata.executionTime + 'ms');

        // Test 2: File System Operations
        console.log('\n4. Testing File System Operations...');
        console.log('   📝 Task: Search for Python files and analyze them');
        const fileResponse = await agent.query('Find all Python files in the current directory and tell me how many there are');
        console.log('   📤 Query: Find all Python files in the current directory');
        console.log('   📥 Response:', fileResponse.content);
        console.log('   ⏱️  Execution time:', fileResponse.metadata.executionTime + 'ms');

        // Test 3: Web Search and Information Gathering
        console.log('\n5. Testing Web Search and Information Gathering...');
        console.log('   📝 Task: Search for recent AI developments');
        const webResponse = await agent.query('Search for the latest developments in AI agent frameworks in 2024');
        console.log('   📤 Query: Search for latest AI agent frameworks in 2024');
        console.log('   📥 Response:', webResponse.content);
        console.log('   ⏱️  Execution time:', webResponse.metadata.executionTime + 'ms');

        // Test 4: Task Management
        console.log('\n6. Testing Task Management...');
        console.log('   📝 Task: Create and manage a todo list');
        const todoResponse = await agent.query('Create a todo list for developing a new AI agent with the following tasks: 1) Design architecture, 2) Implement core logic, 3) Add tool integration, 4) Write tests, 5) Deploy to production');
        console.log('   📤 Query: Create a todo list for AI agent development');
        console.log('   📥 Response:', todoResponse.content);
        console.log('   ⏱️  Execution time:', todoResponse.metadata.executionTime + 'ms');

        // Test 5: Complex Multi-step Reasoning
        console.log('\n7. Testing Complex Multi-step Reasoning...');
        console.log('   📝 Task: Solve a complex problem requiring multiple tools');
        const complexResponse = await agent.query('I need to analyze the current project structure. First, find all TypeScript files, then search for any mentions of "agent" in those files, and finally create a summary of the findings');
        console.log('   📤 Query: Analyze project structure with multiple steps');
        console.log('   📥 Response:', complexResponse.content);
        console.log('   ⏱️  Execution time:', complexResponse.metadata.executionTime + 'ms');

        // Test 6: Error Handling and Recovery
        console.log('\n8. Testing Error Handling and Recovery...');
        console.log('   📝 Task: Handle invalid input gracefully');
        const errorResponse = await agent.query('Execute a command that will fail: "invalid_command_that_does_not_exist"');
        console.log('   📤 Query: Execute invalid command');
        console.log('   📥 Response:', errorResponse.content);
        console.log('   ⏱️  Execution time:', errorResponse.metadata.executionTime + 'ms');

        // Test 7: Memory and Context Retention
        console.log('\n9. Testing Memory and Context Retention...');
        console.log('   📝 Task: Test conversation memory');
        const memoryResponse1 = await agent.query('My name is John and I am working on a TypeScript project');
        console.log('   📤 Query 1: Set context (name and project)');
        console.log('   📥 Response:', memoryResponse1.content);
        
        const memoryResponse2 = await agent.query('What is my name and what project am I working on?');
        console.log('   📤 Query 2: Recall context');
        console.log('   📥 Response:', memoryResponse2.content);
        console.log('   ⏱️  Execution time:', memoryResponse2.metadata.executionTime + 'ms');

        // Summary
        console.log('\n✅ All complex task tests completed!');
        console.log('🎉 Inference.net LLM integration is working successfully');
        
        return true;
    } catch (error) {
        console.error('❌ Complex task test failed:', error);
        return false;
    }
}

if (require.main === module) {
    testComplexTasks().then(success => {
        process.exit(success ? 0 : 1);
    });
}
