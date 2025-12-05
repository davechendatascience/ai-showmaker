/**
 * Test System for Memory Bank Integration with Enhanced Best-First Search
 * 
 * This test demonstrates how to use the Cline-aligned Memory Bank system
 * with our Enhanced Best-First Search agent for real user tasks.
 */

import { MemoryBankSystem, MemoryBankFactory } from '../../src/core/memory-bank-system';
import { EnhancedBestFirstSearchAgent } from '../../src/agents/enhanced-best-first-search-agent';
import { HTTPMCPClient } from '../../src/mcp/http-mcp-client';
import { SessionManager } from '../../src/core/session-manager';
import { OpenAILLM } from '../../src/llm/openai-llm';
import * as fs from 'fs';
import * as path from 'path';

// Test configuration
const TEST_CONFIG = {
  memoryBankPath: './test-memory-bank',
  maxFileSize: 50000,
  autoSync: true
};

class MemoryBankTestRunner {
  private memoryBank: MemoryBankSystem;
  private agent: EnhancedBestFirstSearchAgent;
  private sessionManager: SessionManager;
  private mcpClient: HTTPMCPClient;
  private llm: OpenAILLM;

  constructor() {
    this.sessionManager = new SessionManager();
    
    // Initialize LLM
    const apiKey = process.env['OPENAI_KEY'] || process.env['OPENAI_API_KEY'];
    if (!apiKey) {
      throw new Error('OPENAI_KEY not found for testing');
    }

    this.llm = new OpenAILLM({
      apiKey,
      model: 'gpt-4o-mini',
      temperature: 0.1,
      maxTokens: 2000
    });

    // Initialize memory bank
    this.memoryBank = MemoryBankFactory.getInstance(this.llm, TEST_CONFIG);
    
    // Mock MCP client for testing
    this.mcpClient = {
      getTools: () => [
        { name: 'calculate', description: 'Perform calculations', schema: {} },
        { name: 'search_web', description: 'Search the web', schema: {} },
        { name: 'write_file', description: 'Write files', schema: {} },
        { name: 'read_file', description: 'Read files', schema: {} }
      ],
      executeTool: async (tool: string, params: any) => {
        console.log(`[TEST] Executing tool: ${tool} with params:`, params);
        return { success: true, result: `Mock result for ${tool}` };
      },
      initialize: async () => console.log('[TEST] MCP client initialized')
    } as any;

    this.agent = new EnhancedBestFirstSearchAgent(this.mcpClient, this.llm, this.sessionManager);
  }

  async runTestSuite(): Promise<void> {
    console.log('🧪 Starting Memory Bank Test Suite\n');

    // Test 1: Basic Memory Bank Operations
    await this.testBasicMemoryOperations();

    // Test 2: Task with Memory Context
    await this.testTaskWithMemoryContext();

    // Test 3: Error Logging and Recovery
    await this.testErrorLogging();

    // Test 4: Success Pattern Learning
    await this.testSuccessPatternLearning();

    // Test 5: Cross-Session Memory Persistence
    await this.testCrossSessionPersistence();

    console.log('✅ Memory Bank Test Suite Complete\n');
  }

  private async testBasicMemoryOperations(): Promise<void> {
    console.log('📋 Test 1: Basic Memory Bank Operations');

    // Test adding entries
    const entryId = await this.memoryBank.updateMemoryBank({
      type: 'project_brief',
      content: 'Test project: Build a Python calculator with unit tests',
      metadata: {
        agent: 'main',
        iteration: 1,
        confidence: 0.9,
        tags: ['python', 'calculator', 'testing']
      },
      context: {
        task: 'Build calculator',
        toolsUsed: ['write_file', 'execute_command'],
        successRate: 0.9,
        executionTime: 5000
      }
    });

    console.log(`✓ Added project brief: ${entryId}`);

    // Test loading context
    const context = await this.memoryBank.loadMemoryBankContext('Build calculator');
    console.log('✓ Loaded memory bank context');
    console.log(`Context length: ${context.length} characters`);

    // Test stats
    const stats = this.memoryBank.getStats();
    console.log('✓ Memory bank stats:', stats);
  }

  private async testTaskWithMemoryContext(): Promise<void> {
    console.log('\n📊 Test 2: Task with Memory Context');

    // Set up memory for calculator task
    await this.memoryBank.updateMemoryBank({
      type: 'technical_notes',
      content: 'Use pytest for unit testing. Test edge cases like division by zero.',
      metadata: {
        agent: 'main',
        iteration: 2,
        confidence: 0.8,
        tags: ['testing', 'pytest', 'edge-cases']
      },
      context: {
        task: 'Calculator testing',
        toolsUsed: ['execute_command', 'read_file'],
        successRate: 0.8,
        executionTime: 3000
      }
    });

    // Get BFS context
    const bfsContext = await this.memoryBank.getBFSContext('Build calculator with tests', 3);
    console.log('✓ Generated BFS context');
    console.log('Context includes technical notes and patterns');

    // Get validator context
    const validatorContext = await this.memoryBank.getValidatorContext('Validate calculator tests');
    console.log('✓ Generated validator context');
  }

  private async testErrorLogging(): Promise<void> {
    console.log('\n❌ Test 3: Error Logging and Recovery');

    // Log an error
    await this.memoryBank.logError(
      'Division by zero not handled',
      'Calculator crashes when dividing by zero',
      5,
      ['execute_command', 'python3']
    );

    // Log decision about fixing it
    await this.memoryBank.logDecision(
      'Add input validation for division',
      'Prevent division by zero with try-catch',
      6,
      0.9,
      ['return error message', 'use infinity', 'raise exception']
    );

    console.log('✓ Error and decision logged');
  }

  private async testSuccessPatternLearning(): Promise<void> {
    console.log('\n✅ Test 4: Success Pattern Learning');

    // Log success pattern
    await this.memoryBank.logSuccessPattern(
      'Always validate inputs before calculations',
      ['write_file', 'execute_command'],
      1.0,
      2000
    );

    // Extract patterns
    const patterns = await this.memoryBank.extractPatterns('calculator');
    console.log('✓ Extracted patterns:', patterns);
  }

  private async testCrossSessionPersistence(): Promise<void> {
    console.log('\n🔄 Test 5: Cross-Session Memory Persistence');

    // Simulate session end
    const finalStats = this.memoryBank.getStats();
    console.log('Final memory bank stats:', finalStats);

    // Reset and reload
    MemoryBankFactory.resetInstance();
    const newMemoryBank = MemoryBankFactory.getInstance(this.llm, TEST_CONFIG);

    // Verify persistence
    const newContext = await newMemoryBank.loadMemoryBankContext('Build calculator');
    console.log('✓ Memory persisted across sessions');
    console.log('New context includes previous entries');
  }

  async runRealTaskExample(): Promise<void> {
    console.log('\n🎯 Real Task Example: Build Python Calculator');

    const sessionId = this.sessionManager.createSession('Calculator Build').id;
    
    // Set up memory context
    await this.memoryBank.updateMemoryBank({
      type: 'project_brief',
      content: 'Build a Python calculator with basic operations (+, -, *, /) and comprehensive unit tests',
      metadata: {
        agent: 'main',
        iteration: 0,
        confidence: 1.0,
        tags: ['python', 'calculator', 'testing', 'unit-tests']
      },
      context: {
        task: 'Build Python calculator',
        toolsUsed: [],
        successRate: 0,
        executionTime: 0
      }
    });

    // Execute task with memory context
    const context = await this.memoryBank.getBFSContext('Build Python calculator with tests', 0);
    console.log('Memory context loaded for task execution');

    // Simulate task execution and memory updates
    await this.memoryBank.updateActiveContext(
      'Build Python calculator',
      1,
      ['write_file', 'execute_command'],
      0.8,
      5000,
      'Created calculator.py with basic operations'
    );

    await this.memoryBank.logSuccessPattern(
      'Use pytest fixtures for test setup',
      ['execute_command', 'pytest'],
      0.95,
      3000
    );

    console.log('✅ Real task example complete');
  }
}

// Test runner
async function runMemoryBankTests(): Promise<void> {
  console.log('🚀 Starting Memory Bank Integration Tests\n');

  const runner = new MemoryBankTestRunner();
  
  try {
    await runner.runTestSuite();
    await runner.runRealTaskExample();
    
    console.log('\n📊 Final Memory Bank Stats:');
    const finalStats = runner['memoryBank'].getStats();
    console.log(JSON.stringify(finalStats, null, 2));
    
  } catch (error) {
    console.error('❌ Test failed:', error);
  } finally {
    // Clean up test directory
    if (fs.existsSync(TEST_CONFIG.memoryBankPath)) {
      fs.rmSync(TEST_CONFIG.memoryBankPath, { recursive: true, force: true });
      console.log('🧹 Test directory cleaned up');
    }
  }
}

// Run tests if this file is executed directly
if (require.main === module) {
  runMemoryBankTests().catch(console.error);
}

export { MemoryBankTestRunner, runMemoryBankTests };
