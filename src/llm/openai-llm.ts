/**
 * OpenAI LLM wrapper for the AI-Showmaker project
 */

import { BaseLanguageModel } from '@langchain/core/language_models/base';
import { CallbackManagerForLLMRun } from '@langchain/core/callbacks/manager';
import { BaseMessage, AIMessage } from '@langchain/core/messages';
import { Generation, LLMResult } from '@langchain/core/outputs';
import { ChatOpenAI } from '@langchain/openai';

export interface OpenAILLMConfig {
  apiKey: string;
  model: string;
  temperature: number;
  maxTokens: number;
}

export class OpenAILLM extends BaseLanguageModel {
  private chatOpenAI: ChatOpenAI;
  lc_namespace = ['openai-llm'];

  constructor(config: OpenAILLMConfig) {
    super({});
    this.chatOpenAI = new ChatOpenAI({
      openAIApiKey: config.apiKey,
      modelName: config.model,
      temperature: config.temperature,
      maxTokens: config.maxTokens,
    });
  }

  /**
   * Generate a response based on the input
   */
  async _generate(
    messages: BaseMessage[],
    _options?: any,
    _runManager?: CallbackManagerForLLMRun
  ): Promise<LLMResult> {
    try {
      const response = await this.chatOpenAI.invoke(messages);
      const text = response.content as string;

      const generation: Generation = {
        text: text,
      };

      return {
        generations: [[generation]],
        llmOutput: {
          tokenUsage: {
            promptTokens: 0, // OpenAI doesn't provide this in the response
            completionTokens: 0,
            totalTokens: 0,
          },
        },
      };
    } catch (error) {
      console.error('OpenAI API error:', error);
      throw error;
    }
  }

  /**
   * Get the model name
   */
  _llmType(): string {
    return 'openai-llm';
  }

  /**
   * Get the model identifier
   */
  _modelType(): string {
    return 'openai';
  }

  /**
   * Generate prompt (required by base class)
   */
  async generatePrompt(): Promise<LLMResult> {
    throw new Error('generatePrompt not implemented for OpenAILLM');
  }

  /**
   * Predict (required by base class)
   */
  async predict(): Promise<string> {
    throw new Error('predict not implemented for OpenAILLM');
  }

  /**
   * Predict messages (required by base class)
   */
  async predictMessages(): Promise<BaseMessage> {
    throw new Error('predictMessages not implemented for OpenAILLM');
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
