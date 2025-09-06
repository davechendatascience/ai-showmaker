/**
 * Inference.net LLM integration for TypeScript agent
 */

import { BaseLanguageModel } from '@langchain/core/language_models/base';
import { CallbackManagerForLLMRun } from '@langchain/core/callbacks/manager';
import { BaseMessage, AIMessage, HumanMessage, SystemMessage } from '@langchain/core/messages';
import { Generation, LLMResult } from '@langchain/core/outputs';

export interface InferenceNetConfig {
  apiKey: string;
  model: string;
  temperature?: number;
  maxTokens?: number;
  baseUrl?: string;
}

export class InferenceNetLLM extends BaseLanguageModel {
  override name: string;
  apiKey: string;
  model: string;
  temperature: number;
  maxTokens: number;
  baseUrl: string;
  lc_namespace = ['inference-net'];

  constructor(config: InferenceNetConfig) {
    super({});
    this.name = 'inference-net-llm';
    this.apiKey = config.apiKey;
    this.model = config.model;
    this.temperature = config.temperature || 0.1;
    this.maxTokens = config.maxTokens || 1000;
    this.baseUrl = config.baseUrl || 'https://api.inference.net';
  }

  /**
   * Generate a response using inference.net API
   */
  async _generate(
    messages: BaseMessage[],
    _options?: any,
    _runManager?: CallbackManagerForLLMRun
  ): Promise<LLMResult> {
    if (!messages || messages.length === 0) {
      throw new Error('No messages provided');
    }

    try {
      // Convert LangChain messages to inference.net format
      const formattedMessages = this.formatMessages(messages);
      
      // Make API request to inference.net
      const response = await this.makeAPIRequest(formattedMessages);
      
      // Extract the response text
      const responseText = this.extractResponseText(response);
      
      const generation: Generation = {
        text: responseText,
      };

      return {
        generations: [[generation]],
        llmOutput: {
          tokenUsage: {
            promptTokens: this.estimateTokens(messages),
            completionTokens: this.estimateTokens([new AIMessage(responseText)]),
            totalTokens: this.estimateTokens(messages) + this.estimateTokens([new AIMessage(responseText)]),
          },
        },
      };
    } catch (error) {
      console.error('Inference.net API error:', error);
      throw new Error(`Inference.net API error: ${error}`);
    }
  }

  /**
   * Format LangChain messages for inference.net API
   */
  private formatMessages(messages: BaseMessage[]): any[] {
    return messages.map(message => {
      if (message instanceof SystemMessage) {
        return {
          role: 'system',
          content: message.content
        };
      } else if (message instanceof HumanMessage) {
        return {
          role: 'user',
          content: message.content
        };
      } else if (message instanceof AIMessage) {
        return {
          role: 'assistant',
          content: message.content
        };
      } else {
        return {
          role: 'user',
          content: String(message.content)
        };
      }
    });
  }

  /**
   * Make API request to inference.net
   */
  private async makeAPIRequest(messages: any[]): Promise<any> {
    const requestBody = {
      model: this.model,
      messages: messages,
      temperature: this.temperature,
      max_tokens: this.maxTokens,
      stream: false
    };

    const response = await fetch(`${this.baseUrl}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    return await response.json();
  }

  /**
   * Extract response text from inference.net API response
   */
  private extractResponseText(response: any): string {
    if (response.choices && response.choices.length > 0) {
      return response.choices[0].message?.content || 'No response generated';
    }
    return 'No response generated';
  }

  /**
   * Estimate token count (rough approximation)
   */
  private estimateTokens(messages: BaseMessage[]): number {
    const totalText = messages.map(m => String(m.content)).join(' ');
    return Math.ceil(totalText.length / 4); // Rough approximation: 4 chars per token
  }

  /**
   * Get the model name
   */
  _llmType(): string {
    return 'inference-net-llm';
  }

  /**
   * Get the model identifier
   */
  _modelType(): string {
    return 'inference-net';
  }

  /**
   * Generate prompt (required by base class)
   */
  async generatePrompt(): Promise<LLMResult> {
    throw new Error('generatePrompt not implemented for InferenceNetLLM');
  }

  /**
   * Predict (required by base class)
   */
  async predict(): Promise<string> {
    throw new Error('predict not implemented for InferenceNetLLM');
  }

  /**
   * Predict messages (required by base class)
   */
  async predictMessages(): Promise<BaseMessage> {
    throw new Error('predictMessages not implemented for InferenceNetLLM');
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
