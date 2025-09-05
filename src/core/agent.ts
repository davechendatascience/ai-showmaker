/**
 * Main AI Agent class for AI-Showmaker
 */

import { ConfigManager } from './config';
import { HTTPMCPClient, MCPToolWrapper } from '../mcp/http-mcp-client';
import { AgentResponse, ConversationMessage, AgentState, AgentCapabilities } from '../types';
import { ChatOpenAI } from '@langchain/openai';
import { AgentExecutor, createOpenAIFunctionsAgent } from 'langchain/agents';
import { ChatPromptTemplate, MessagesPlaceholder } from '@langchain/core/prompts';
import { DynamicTool } from 'langchain/tools';
import { ConversationChain } from 'langchain/chains';
import { BufferMemory } from 'langchain/memory';

export class AIAgent {
  // private config: ConfigManager; // Will be used for future LLM integration
  private mcpClient: HTTPMCPClient;
  private llm!: ChatOpenAI;
  private agent!: AgentExecutor | ConversationChain;
  private memory!: BufferMemory;
  private state!: AgentState;
  private capabilities!: AgentCapabilities;

  constructor(_config: ConfigManager) {
    // this.config = config; // Will be used for future LLM integration
    this.mcpClient = new HTTPMCPClient('http://localhost:8000');
    this.initializeCapabilities();
    this.initializeState();
  }

  /**
   * Initialize the agent
   */
  async initialize(): Promise<void> {
    console.log('🤖 Initializing AI Agent...');
    
    try {
      // Initialize MCP client
      await this.mcpClient.initialize();
      
      // Initialize LLM
      await this.initializeLLM();
      
      // Initialize memory
      this.initializeMemory();
      
      // Create agent with tools
      await this.createAgent();
      
      console.log('✅ AI Agent initialized successfully');
      console.log(`📊 Available tools: ${this.mcpClient.getToolCount()}`);
      console.log(`🔌 Connected servers: ${this.mcpClient.getServerCount()}`);
      
    } catch (error) {
      console.error('❌ Failed to initialize AI Agent:', error);
      throw error;
    }
  }

  /**
   * Initialize agent capabilities
   */
  private initializeCapabilities(): void {
    this.capabilities = {
      toolExecution: true,
      conversationMemory: true,
      taskPlanning: true,
      webSearch: true,
      fileOperations: true,
      gitOperations: true,
      remoteExecution: true,
    };
  }

  /**
   * Initialize agent state
   */
  private initializeState(): void {
    this.state = {
      sessionId: this.generateSessionId(),
      conversationHistory: [],
      availableTools: [],
      metadata: {
        initialized: false,
        startTime: new Date(),
        version: '2.0.0-ts',
      },
    };
  }

  /**
   * Initialize the LLM
   */
  private async initializeLLM(): Promise<void> {
    try {
      // If LLM is already set (e.g., by setLLM), skip initialization
      if (this.llm) {
        console.log('✅ LLM already set, skipping initialization');
        return;
      }
      
      // For now, we'll use a mock LLM since we need to handle inference.net differently
      // In a real implementation, you'd create a custom LLM class for inference.net
      this.llm = new ChatOpenAI({
        modelName: 'gpt-3.5-turbo', // Placeholder
        temperature: 0.1,
        openAIApiKey: 'mock-key', // Placeholder
      });
      
      console.log('✅ LLM initialized');
    } catch (error) {
      console.error('❌ Failed to initialize LLM:', error);
      throw error;
    }
  }

  /**
   * Set a custom LLM (for testing or different providers)
   */
  setLLM(llm: any): void {
    this.llm = llm;
    console.log('✅ Custom LLM set');
  }

  /**
   * Initialize memory
   */
  private initializeMemory(): void {
    this.memory = new BufferMemory({
      memoryKey: 'chat_history',
      returnMessages: true,
    });
    
    console.log('✅ Memory initialized');
  }

  /**
   * Create the agent with tools
   */
  private async createAgent(): Promise<void> {
    try {
      const tools = this.convertToLangChainTools();
      
      if (tools.length > 0) {
        // Create function-calling agent
        const prompt = ChatPromptTemplate.fromMessages([
          ['system', this.getSystemPrompt()],
          ['human', '{input}'],
          new MessagesPlaceholder('agent_scratchpad'),
        ]);

        const agent = await createOpenAIFunctionsAgent({
          llm: this.llm,
          tools,
          prompt,
        });

        this.agent = new AgentExecutor({
          agent,
          tools,
          verbose: true,
          handleParsingErrors: true,
        });
        
        console.log('✅ Function-calling agent created with tools');
      } else {
        // Create simple conversation chain
        this.agent = new ConversationChain({
          llm: this.llm,
          memory: this.memory,
        });
        
        console.log('✅ Simple conversation agent created (no tools)');
      }
      
    } catch (error) {
      console.error('❌ Failed to create agent:', error);
      throw error;
    }
  }

  /**
   * Convert MCP tools to LangChain tools
   */
  private convertToLangChainTools(): DynamicTool[] {
    const mcpTools = this.mcpClient.getTools();
    
    return mcpTools.map(mcpTool => new DynamicTool({
      name: mcpTool.name,
      description: mcpTool.description,
      func: async (input: string) => {
        try {
          // Parse input as JSON or use as-is
          let params: Record<string, any> = {};
          try {
            params = JSON.parse(input);
          } catch {
            params = { input };
          }
          
          const result = await mcpTool.execute(params);
          return JSON.stringify(result);
        } catch (error) {
          return `Error executing tool ${mcpTool.name}: ${error}`;
        }
      },
    }));
  }

  /**
   * Get system prompt for the agent
   */
  private getSystemPrompt(): string {
    return `You are an AI-Showmaker agent, a helpful AI assistant with access to various tools.

Your capabilities include:
- Tool execution for various tasks
- Conversation memory
- Task planning and execution
- Web search and information gathering
- File and git operations
- Remote command execution

Always think step by step and use tools when appropriate. Be helpful, accurate, and efficient in your responses.

Available tools: ${this.mcpClient.getTools().map(t => t.name).join(', ')}`;
  }

  /**
   * Execute a query
   */
  async query(input: string): Promise<AgentResponse> {
    console.log(`🤖 Processing query: ${input}`);
    
    try {
      // Add user message to history
      this.addMessage('user', input);
      
      // Execute with agent
      const startTime = Date.now();
      const response = await this.agent.invoke({ input });
      const executionTime = Date.now() - startTime;
      
      // Extract response content
      const content = (response as any).output || (response as any).response || 'No response generated';
      
      // Add assistant message to history
      this.addMessage('assistant', content);
      
      // Create response object
      const agentResponse: AgentResponse = {
        content,
        metadata: {
          model: 'ai-showmaker-agent',
          tokensUsed: 0, // Placeholder
          executionTime,
        },
      };
      
      console.log('✅ Query processed successfully');
      return agentResponse;
      
    } catch (error) {
      console.error('❌ Query processing failed:', error);
      
      const errorResponse: AgentResponse = {
        content: `I encountered an error while processing your request: ${error}`,
        metadata: {
          model: 'ai-showmaker-agent',
          tokensUsed: 0,
          executionTime: 0,
        },
      };
      
      return errorResponse;
    }
  }

  /**
   * Add a message to conversation history
   */
  private addMessage(role: 'user' | 'assistant' | 'system', content: string): void {
    const message: ConversationMessage = {
      role,
      content,
      timestamp: new Date(),
    };
    
    this.state.conversationHistory.push(message);
  }

  /**
   * Get conversation history
   */
  getConversationHistory(): ConversationMessage[] {
    return [...this.state.conversationHistory];
  }

  /**
   * Get agent state
   */
  getState(): AgentState {
    return { ...this.state };
  }

  /**
   * Get agent capabilities
   */
  getCapabilities(): AgentCapabilities {
    return { ...this.capabilities };
  }

  /**
   * Get available tools
   */
  getAvailableTools(): MCPToolWrapper[] {
    return this.mcpClient.getTools();
  }

  /**
   * Execute a specific tool
   */
  async executeTool(toolName: string, params: Record<string, any>): Promise<any> {
    return await this.mcpClient.executeTool(toolName, params);
  }

  /**
   * Generate a unique session ID
   */
  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Cleanup resources
   */
  async cleanup(): Promise<void> {
    console.log('🧹 Cleaning up AI Agent...');
    
    try {
      // Clear memory
      if (this.memory) {
        await this.memory.clear();
      }
      
      // Clear conversation history
      this.state.conversationHistory = [];
      
      console.log('✅ AI Agent cleanup completed');
    } catch (error) {
      console.error('❌ Cleanup failed:', error);
    }
  }
}
