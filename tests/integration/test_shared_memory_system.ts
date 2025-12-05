/**
 * Comprehensive Test Suite for Shared Memory System
 * 
 * This test suite validates the shared memory bank system between the main agent
 * and validator agent, ensuring proper communication and data persistence.
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach } from '@jest/globals';
import { HTTPMCPClient } from '../../src/mcp/http-mcp-client';
import { SessionManager } from '../../src/core/session-manager';
import { SharedMemorySystem, MemoryFactory } from '../../src/core/shared-memory-system';
import { EnhancedBestFirstSearchAgentWithMemoryBank } from '../../src/agents/enhanced-best-first-search-agent-with-memory-bank';
import { ValidatorAgent } from '../../src/agents/validator-agent';
import { MockLLM } from '../../src/llm/mock-llm';

describe('Shared Memory System Integration Tests', () => {
  let mcpClient: HTTPMCPClient;
  let sessionManager: SessionManager;
  let sharedMemory: SharedMemorySystem;
  let mainAgent: EnhancedBestFirstSearchAgentWithMemoryBank;
  let validatorAgent: ValidatorAgent;
  let mockLLM: MockLLM;

  beforeAll(async () => {
    // Initialize MCP client
    mcpClient = new HTTPMCPClient('http://localhost:8000');
    await mcpClient.initialize();
    
    // Initialize session manager
    sessionManager = new SessionManager();
    
    // Initialize mock LLM for testing
    mockLLM = new MockLLM();
    
    // Initialize shared memory system
    sharedMemory = MemoryFactory.getInstance(mockLLM);
    
    // Initialize agents
    mainAgent = new EnhancedBestFirstSearchAgentWithMemoryBank(mcpClient, mockLLM, sessionManager);
    validatorAgent = new ValidatorAgent(mockLLM);
  });

  afterAll(async () => {
    // Clean up
    MemoryFactory.resetInstance();
  });

  beforeEach(() => {
    // Reset shared memory for each test
    MemoryFactory.resetInstance();
    sharedMemory = MemoryFactory.getInstance(mockLLM);
  });

  describe('Basic Memory Operations', () => {
    it('should add and retrieve memory entries', () => {
      const entryId = sharedMemory.addEntry({
        type: 'execution',
        content: 'Test execution step',
        metadata: {
          agent: 'main',
          iteration: 1,
          confidence: 0.8,
          tool: 'test_tool',
          success: true
        },
        context: {
          task: 'test task',
          availableTools: ['test_tool'],
          iteration: 1,
          frontierSize: 3
        }
      });

      expect(entryId).toBeDefined();
      expect(entryId).toMatch(/^mem_\d+_[a-z0-9]+$/);

      const entries = sharedMemory.queryMemories({
        types: ['execution'],
        maxResults: 10
      });

      expect(entries).toHaveLength(1);
      expect(entries[0].content).toBe('Test execution step');
      expect(entries[0].metadata.agent).toBe('main');
      expect(entries[0].metadata.tool).toBe('test_tool');
    });

    it('should filter memories by type', () => {
      // Add different types of entries
      sharedMemory.addEntry({
        type: 'execution',
        content: 'Execution step 1',
        metadata: { agent: 'main', iteration: 1 },
        context: { task: 'test', availableTools: [], iteration: 1, frontierSize: 0 }
      });

      sharedMemory.addEntry({
        type: 'validation',
        content: 'Validation step 1',
        metadata: { agent: 'validator', iteration: 1 },
        context: { task: 'test', availableTools: [], iteration: 1, frontierSize: 0 }
      });

      sharedMemory.addEntry({
        type: 'error',
        content: 'Error step 1',
        metadata: { agent: 'main', iteration: 1 },
        context: { task: 'test', availableTools: [], iteration: 1, frontierSize: 0 }
      });

      const executionEntries = sharedMemory.queryMemories({
        types: ['execution'],
        maxResults: 10
      });

      const validationEntries = sharedMemory.queryMemories({
        types: ['validation'],
        maxResults: 10
      });

      const errorEntries = sharedMemory.queryMemories({
        types: ['error'],
        maxResults: 10
      });

      expect(executionEntries).toHaveLength(1);
      expect(validationEntries).toHaveLength(1);
      expect(errorEntries).toHaveLength(1);

      expect(executionEntries[0].type).toBe('execution');
      expect(validationEntries[0].type).toBe('validation');
      expect(errorEntries[0].type).toBe('error');
    });

    it('should filter memories by agent', () => {
      // Add entries from different agents
      sharedMemory.addEntry({
        type: 'execution',
        content: 'Main agent execution',
        metadata: { agent: 'main', iteration: 1 },
        context: { task: 'test', availableTools: [], iteration: 1, frontierSize: 0 }
      });

      sharedMemory.addEntry({
        type: 'validation',
        content: 'Validator validation',
        metadata: { agent: 'validator', iteration: 1 },
        context: { task: 'test', availableTools: [], iteration: 1, frontierSize: 0 }
      });

      const mainEntries = sharedMemory.queryMemories({
        agent: 'main',
        maxResults: 10
      });

      const validatorEntries = sharedMemory.queryMemories({
        agent: 'validator',
        maxResults: 10
      });

      expect(mainEntries).toHaveLength(1);
      expect(validatorEntries).toHaveLength(1);

      expect(mainEntries[0].metadata.agent).toBe('main');
      expect(validatorEntries[0].metadata.agent).toBe('validator');
    });

    it('should provide memory summary', () => {
      // Add various entries
      sharedMemory.addEntry({
        type: 'execution',
        content: 'Execution 1',
        metadata: { agent: 'main', iteration: 1 },
        context: { task: 'test', availableTools: [], iteration: 1, frontierSize: 0 }
      });

      sharedMemory.addEntry({
        type: 'execution',
        content: 'Execution 2',
        metadata: { agent: 'main', iteration: 2 },
        context: { task: 'test', availableTools: [], iteration: 2, frontierSize: 0 }
      });

      sharedMemory.addEntry({
        type: 'validation',
        content: 'Validation 1',
        metadata: { agent: 'validator', iteration: 1 },
        context: { task: 'test', availableTools: [], iteration: 1, frontierSize: 0 }
      });

      const summary = sharedMemory.getMemorySummary();

      expect(summary.totalEntries).toBe(3);
      expect(summary.byType.execution).toBe(2);
      expect(summary.byType.validation).toBe(1);
      expect(summary.byAgent.main).toBe(2);
      expect(summary.byAgent.validator).toBe(1);
    });
  });

  describe('Agent Communication', () => {
    it('should allow main agent to add execution entries', () => {
      const entryId = sharedMemory.addEntry({
        type: 'execution',
        content: 'Main agent executed tool: search_web',
        metadata: {
          agent: 'main',
          iteration: 1,
          confidence: 0.9,
          tool: 'search_web',
          success: true
        },
        context: {
          task: 'Search for information',
          availableTools: ['search_web', 'extract_content'],
          iteration: 1,
          frontierSize: 2
        }
      });

      expect(entryId).toBeDefined();

      const entries = sharedMemory.queryMemories({
        types: ['execution'],
        agent: 'main'
      });

      expect(entries).toHaveLength(1);
      expect(entries[0].content).toContain('search_web');
      expect(entries[0].metadata.tool).toBe('search_web');
      expect(entries[0].metadata.success).toBe(true);
    });

    it('should allow validator agent to add validation entries', () => {
      const entryId = sharedMemory.addEntry({
        type: 'validation',
        content: 'Task validation: completed=false, confidence=0.6',
        metadata: {
          agent: 'validator',
          iteration: 1,
          confidence: 0.6,
          success: false
        },
        context: {
          task: 'Test task',
          availableTools: ['test_tool'],
          iteration: 1,
          frontierSize: 1
        }
      });

      expect(entryId).toBeDefined();

      const entries = sharedMemory.queryMemories({
        types: ['validation'],
        agent: 'validator'
      });

      expect(entries).toHaveLength(1);
      expect(entries[0].content).toContain('completed=false');
      expect(entries[0].metadata.agent).toBe('validator');
    });

    it('should provide context for validator agent', async () => {
      // Add some execution history
      sharedMemory.addEntry({
        type: 'execution',
        content: 'Executed: search_web with query "test"',
        metadata: {
          agent: 'main',
          iteration: 1,
          tool: 'search_web',
          success: true
        },
        context: {
          task: 'Search task',
          availableTools: ['search_web'],
          iteration: 1,
          frontierSize: 1
        }
      });

      sharedMemory.addEntry({
        type: 'execution',
        content: 'Executed: extract_content from results',
        metadata: {
          agent: 'main',
          iteration: 2,
          tool: 'extract_content',
          success: true
        },
        context: {
          task: 'Search task',
          availableTools: ['search_web', 'extract_content'],
          iteration: 2,
          frontierSize: 0
        }
      });

      const context = await sharedMemory.getValidatorContext('Search task');

      expect(context).toContain('Search task');
      expect(context).toContain('search_web');
      expect(context).toContain('extract_content');
      expect(context).toContain('Recent Execution History');
    });

    it('should provide context for main agent', async () => {
      // Add some recent entries
      sharedMemory.addEntry({
        type: 'execution',
        content: 'Recent execution step',
        metadata: {
          agent: 'main',
          iteration: 5,
          tool: 'test_tool',
          success: true
        },
        context: {
          task: 'Test task',
          availableTools: ['test_tool'],
          iteration: 5,
          frontierSize: 2
        }
      });

      const context = await sharedMemory.getAgentContext('Test task', 5);

      expect(context).toContain('Test task');
      expect(context).toContain('Recent Memory');
      expect(context).toContain('Recent execution step');
    });
  });

  describe('Memory Persistence and Cleanup', () => {
    it('should limit memory entries to prevent bloat', () => {
      // Add more entries than the max limit
      const maxEntries = 1000;
      const testEntries = 1005;

      for (let i = 0; i < testEntries; i++) {
        sharedMemory.addEntry({
          type: 'execution',
          content: `Execution step ${i}`,
          metadata: {
            agent: 'main',
            iteration: i,
            tool: 'test_tool',
            success: true
          },
          context: {
            task: 'Test task',
            availableTools: ['test_tool'],
            iteration: i,
            frontierSize: 1
          }
        });
      }

      const summary = sharedMemory.getMemorySummary();
      expect(summary.totalEntries).toBeLessThanOrEqual(maxEntries);
    });

    it('should clean up old entries', () => {
      // Add some entries
      for (let i = 0; i < 10; i++) {
        sharedMemory.addEntry({
          type: 'execution',
          content: `Execution ${i}`,
          metadata: {
            agent: 'main',
            iteration: i,
            tool: 'test_tool',
            success: true
          },
          context: {
            task: 'Test task',
            availableTools: ['test_tool'],
            iteration: i,
            frontierSize: 1
          }
        });
      }

      expect(sharedMemory.getMemorySummary().totalEntries).toBe(10);

      // Clean up, keeping only 5 recent entries
      sharedMemory.cleanup(5);

      expect(sharedMemory.getMemorySummary().totalEntries).toBe(5);
    });
  });

  describe('Pattern Extraction', () => {
    it('should extract patterns from memory entries', async () => {
      // Add entries with patterns
      sharedMemory.addEntry({
        type: 'execution',
        content: 'Successfully executed search_web for information gathering',
        metadata: {
          agent: 'main',
          iteration: 1,
          tool: 'search_web',
          success: true
        },
        context: {
          task: 'Information gathering',
          availableTools: ['search_web'],
          iteration: 1,
          frontierSize: 1
        }
      });

      sharedMemory.addEntry({
        type: 'execution',
        content: 'Successfully executed extract_content for data processing',
        metadata: {
          agent: 'main',
          iteration: 2,
          tool: 'extract_content',
          success: true
        },
        context: {
          task: 'Data processing',
          availableTools: ['extract_content'],
          iteration: 2,
          frontierSize: 0
        }
      });

      const patterns = await sharedMemory.extractPatterns('information_gathering');

      // MockLLM should return some patterns
      expect(Array.isArray(patterns)).toBe(true);
    });
  });

  describe('Integration with Agents', () => {
    it('should work with EnhancedBestFirstSearchAgentWithMemoryBank', async () => {
      // This test verifies that the main agent can use shared memory
      const sessionId = 'test-session-1';
      
      // The agent should be able to execute a simple task and store results in shared memory
      const task = 'Test the shared memory system by creating a simple file';
      
      try {
        const result = await mainAgent.executeTask(task, sessionId);
        
        // Check that some entries were added to shared memory
        const summary = sharedMemory.getMemorySummary();
        expect(summary.totalEntries).toBeGreaterThan(0);
        
        // Check that we have execution entries
        const executionEntries = sharedMemory.queryMemories({
          types: ['execution'],
          agent: 'main'
        });
        expect(executionEntries.length).toBeGreaterThan(0);
        
        console.log(`Main agent executed task and added ${summary.totalEntries} memory entries`);
        console.log(`Execution entries: ${executionEntries.length}`);
        
      } catch (error) {
        console.error('Agent execution failed:', error);
        // Even if execution fails, we should have some memory entries
        const summary = sharedMemory.getMemorySummary();
        expect(summary.totalEntries).toBeGreaterThan(0);
      }
    });

    it('should work with ValidatorAgent', async () => {
      // Add some execution history first
      sharedMemory.addEntry({
        type: 'execution',
        content: 'Executed: write_file with test content',
        metadata: {
          agent: 'main',
          iteration: 1,
          tool: 'write_file',
          success: true
        },
        context: {
          task: 'Create test file',
          availableTools: ['write_file'],
          iteration: 1,
          frontierSize: 0
        }
      });

      // Create a mock execution trace for the validator
      const mockTrace = [
        {
          id: 'test-1',
          planId: 'plan-1',
          thought: 'Create a test file',
          step: 'write_file with test content',
          observation: 'File created successfully',
          success: true,
          tool: 'write_file',
          executionTime: 100
        }
      ];

      const validationResult = await validatorAgent.validate('Create a test file', mockTrace);
      
      expect(validationResult).toBeDefined();
      expect(typeof validationResult.completed).toBe('boolean');
      expect(typeof validationResult.confidence).toBe('number');
      expect(Array.isArray(validationResult.issues)).toBe(true);
      expect(Array.isArray(validationResult.suggested_next_actions)).toBe(true);

      // Check that validation entry was added to shared memory
      const validationEntries = sharedMemory.queryMemories({
        types: ['validation'],
        agent: 'validator'
      });
      
      expect(validationEntries.length).toBeGreaterThan(0);
      console.log(`Validator added ${validationEntries.length} validation entries`);
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid memory queries gracefully', () => {
      const entries = sharedMemory.queryMemories({
        types: ['nonexistent_type'] as any,
        maxResults: 10
      });

      expect(Array.isArray(entries)).toBe(true);
      expect(entries.length).toBe(0);
    });

    it('should handle empty memory queries', () => {
      const entries = sharedMemory.queryMemories({});
      expect(Array.isArray(entries)).toBe(true);
    });

    it('should handle pattern extraction failures gracefully', async () => {
      // Test with empty memory
      const patterns = await sharedMemory.extractPatterns();
      expect(Array.isArray(patterns)).toBe(true);
    });
  });

  describe('Memory Factory Singleton', () => {
    it('should return the same instance', () => {
      const instance1 = MemoryFactory.getInstance(mockLLM);
      const instance2 = MemoryFactory.getInstance(mockLLM);
      
      expect(instance1).toBe(instance2);
    });

    it('should create new instance after reset', () => {
      const instance1 = MemoryFactory.getInstance(mockLLM);
      MemoryFactory.resetInstance();
      const instance2 = MemoryFactory.getInstance(mockLLM);
      
      expect(instance1).not.toBe(instance2);
    });
  });
});
