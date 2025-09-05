/**
 * Mock LLM for testing tool execution without API keys
 */

import { BaseLanguageModel } from '@langchain/core/language_models/base';
import { CallbackManagerForLLMRun } from '@langchain/core/callbacks/manager';
import { BaseMessage, AIMessage } from '@langchain/core/messages';
import { Generation, LLMResult } from '@langchain/core/outputs';
import { StructuredTool } from 'langchain/tools';

export interface MockLLMConfig {
  name: string;
  temperature: number;
  maxTokens: number;
}

export class MockLLM extends BaseLanguageModel {
  override name: string;
  temperature: number;
  maxTokens: number;
  tools: StructuredTool[] = [];
  lc_namespace = ['mock-llm'];

  constructor(config: MockLLMConfig) {
    super({});
    this.name = config.name;
    this.temperature = config.temperature;
    this.maxTokens = config.maxTokens;
  }

  /**
   * Set available tools for the mock LLM
   */
  setTools(tools: StructuredTool[]): void {
    this.tools = tools;
  }

  /**
   * Generate a response based on the input
   */
  async _generate(
    messages: BaseMessage[],
    _options?: any,
    _runManager?: CallbackManagerForLLMRun
  ): Promise<LLMResult> {
    if (!messages || messages.length === 0) {
      throw new Error('No messages provided');
    }
    const lastMessage = messages[messages.length - 1];
    if (!lastMessage) {
      throw new Error('No messages provided');
    }
    const content = lastMessage.content as string;

    // Simple mock responses based on content
    let response = this.generateMockResponse(content);

    // If this looks like a tool-calling scenario, generate a tool call
    if (this.shouldCallTool(content)) {
      response = this.generateToolCall(content);
    }

    const generation: Generation = {
      text: response,
    };

    return {
      generations: [[generation]],
      llmOutput: {
        tokenUsage: {
          promptTokens: (content || '').length,
          completionTokens: response.length,
          totalTokens: (content || '').length + response.length,
        },
      },
    };
  }

  /**
   * Generate a mock response based on the input
   */
  private generateMockResponse(content: string): string {
    if (!content) {
      return "I understand your request. Let me help you with that.";
    }
    const lowerContent = content.toLowerCase();

    if (lowerContent.includes('calculate') || lowerContent.includes('math') || lowerContent.includes('*') || lowerContent.includes('+')) {
      return "I'll help you with that calculation. Let me use the calculate tool.";
    }

    if (lowerContent.includes('search') || lowerContent.includes('find') || lowerContent.includes('web')) {
      return "I'll search for that information for you.";
    }

    if (lowerContent.includes('todo') || lowerContent.includes('task') || lowerContent.includes('list')) {
      return "I'll help you manage your todos.";
    }

    if (lowerContent.includes('file') || lowerContent.includes('directory') || lowerContent.includes('python')) {
      return "I'll help you find and work with files.";
    }

    return "I understand your request. Let me help you with that.";
  }

  /**
   * Determine if we should call a tool based on the content
   */
  private shouldCallTool(content: string): boolean {
    if (!content) {
      return false;
    }
    const lowerContent = content.toLowerCase();
    
    return (
      lowerContent.includes('calculate') ||
      lowerContent.includes('search') ||
      lowerContent.includes('todo') ||
      lowerContent.includes('file') ||
      lowerContent.includes('find') ||
      lowerContent.includes('*') ||
      lowerContent.includes('+') ||
      lowerContent.includes('-') ||
      lowerContent.includes('/')
    );
  }

  /**
   * Generate a tool call response
   */
  private generateToolCall(content: string): string {
    if (!content) {
      return "I'll use the appropriate tool to help you with that.";
    }
    const lowerContent = content.toLowerCase();

    if (lowerContent.includes('calculate') || lowerContent.includes('*') || lowerContent.includes('+') || lowerContent.includes('-') || lowerContent.includes('/')) {
      // Extract numbers and operation
      const numbers = content.match(/\d+/g);
      const operation = content.match(/[\+\-\*\/]/);
      
      if (numbers && numbers.length >= 2 && operation) {
        const a = parseInt(numbers[0]);
        const b = parseInt(numbers[1] || '0');
        let result = 0;
        
        switch (operation[0]) {
          case '+': result = a + b; break;
          case '-': result = a - b; break;
          case '*': result = a * b; break;
          case '/': result = Math.floor(a / b); break;
        }
        
        return `I'll calculate ${a} ${operation[0]} ${b} for you. The result is ${result}.`;
      }
      
      return "I'll help you with that calculation using the calculate tool.";
    }

    if (lowerContent.includes('search') || lowerContent.includes('web')) {
      return "I'll search for that information using the web search tool.";
    }

    if (lowerContent.includes('todo')) {
      return "I'll help you manage your todos using the todo management tools.";
    }

    if (lowerContent.includes('file') || lowerContent.includes('find')) {
      return "I'll help you find files using the file search tools.";
    }

    return "I'll use the appropriate tool to help you with that.";
  }

  /**
   * Get the model name
   */
  _llmType(): string {
    return 'mock-llm';
  }

  /**
   * Get the model identifier
   */
  _modelType(): string {
    return 'mock';
  }

  /**
   * Generate prompt (required by base class)
   */
  async generatePrompt(): Promise<LLMResult> {
    throw new Error('generatePrompt not implemented for MockLLM');
  }

  /**
   * Predict (required by base class)
   */
  async predict(): Promise<string> {
    throw new Error('predict not implemented for MockLLM');
  }

  /**
   * Predict messages (required by base class)
   */
  async predictMessages(): Promise<BaseMessage> {
    throw new Error('predictMessages not implemented for MockLLM');
  }

  /**
   * Invoke (required by base class)
   */
  async invoke(input: any): Promise<BaseMessage> {
    const messages = Array.isArray(input) ? input : [input];
    const result = await this._generate(messages);
    const text = result.generations[0]?.[0]?.text || 'No response generated';
    return new AIMessage(text);
  }
}
