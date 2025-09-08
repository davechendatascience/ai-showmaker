import { BaseLanguageModel } from '@langchain/core/language_models/base';
import { LongTermMemorySystem } from './agentic-memory';

/**
 * Agentic RAG + Long-term Memory System
 * 
 * Combines the dynamic decision-making of Agentic RAG with persistent
 * long-term memory for optimal performance.
 */

export interface RAGDecision {
  shouldRetrieve: boolean;
  shouldGenerate: boolean;
  shouldValidate: boolean;
  confidence: number;
  reasoning: string;
}

export interface RAGContext {
  query: string;
  retrievedDocuments: string[];
  memoryContext: string;
  previousAttempts: string[];
  currentStep: string;
}

export class AgenticRAGMemory {
  private longTermMemory: LongTermMemorySystem;
  private llm: BaseLanguageModel;

  constructor(llm: BaseLanguageModel, memoryLLM: BaseLanguageModel) {
    this.llm = llm;
    this.longTermMemory = new LongTermMemorySystem(memoryLLM);
  }

  /**
   * Intelligent Query Routing (Agentic RAG)
   * Decides whether to retrieve, generate, or validate based on context
   */
  async routeQuery(
    query: string,
    context: RAGContext
  ): Promise<RAGDecision> {
    const memoryContext = await this.longTermMemory.generateMemoryContext(
      query,
      context.currentStep,
      'general',
      ['routing', 'decision-making']
    );

    const prompt = `You are an intelligent query router. Analyze this query and decide the best approach:

QUERY: ${query}
CURRENT STEP: ${context.currentStep}
PREVIOUS ATTEMPTS: ${context.previousAttempts.join(', ')}
MEMORY CONTEXT: ${memoryContext}

Available actions:
1. RETRIEVE: Get more information from external sources
2. GENERATE: Create response based on current knowledge
3. VALIDATE: Check and validate existing results

Return JSON:
{
  "shouldRetrieve": true/false,
  "shouldGenerate": true/false,
  "shouldValidate": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "Why this approach was chosen"
}`;

    try {
      const response = await this.llm.invoke([{ role: 'user', content: prompt }]);
      const decision = JSON.parse(response.content);
      
      return {
        shouldRetrieve: decision.shouldRetrieve || false,
        shouldGenerate: decision.shouldGenerate || false,
        shouldValidate: decision.shouldValidate || false,
        confidence: decision.confidence || 0.5,
        reasoning: decision.reasoning || 'Default routing decision'
      };
    } catch (error) {
      console.error('Query routing failed:', error);
      return {
        shouldRetrieve: false,
        shouldGenerate: true,
        shouldValidate: false,
        confidence: 0.3,
        reasoning: 'Fallback: generate response due to routing failure'
      };
    }
  }

  /**
   * Self-Correcting Query Generation (Agentic RAG)
   * Rephrases queries if initial attempts fail
   */
  async rephraseQuery(
    originalQuery: string,
    failureReason: string,
    context: RAGContext
  ): Promise<string> {
    const memoryContext = await this.longTermMemory.generateMemoryContext(
      `Failed query: ${originalQuery}, Reason: ${failureReason}`,
      'query_rephrasing',
      'debugging',
      ['query', 'failure', 'rephrasing']
    );

    const prompt = `Rephrase this failed query to improve results:

ORIGINAL QUERY: ${originalQuery}
FAILURE REASON: ${failureReason}
CONTEXT: ${context.currentStep}
MEMORY CONTEXT: ${memoryContext}

Generate a better version of the query that addresses the failure reason.`;

    try {
      const response = await this.llm.invoke([{ role: 'user', content: prompt }]);
      return response.content;
    } catch (error) {
      console.error('Query rephrasing failed:', error);
      return originalQuery; // Fallback to original
    }
  }

  /**
   * Multi-Stage Validation (Agentic RAG)
   * Validates both retrieved documents and generated responses
   */
  async validateResult(
    query: string,
    result: string,
    context: RAGContext
  ): Promise<{ isValid: boolean; confidence: number; issues: string[] }> {
    const memoryContext = await this.longTermMemory.generateMemoryContext(
      `Validation: ${query}`,
      'validation',
      'general',
      ['validation', 'quality-check']
    );

    const prompt = `Validate this result for the given query:

QUERY: ${query}
RESULT: ${result}
CONTEXT: ${context.currentStep}
MEMORY CONTEXT: ${memoryContext}

Return JSON:
{
  "isValid": true/false,
  "confidence": 0.0-1.0,
  "issues": ["list", "of", "issues"]
}`;

    try {
      const response = await this.llm.invoke([{ role: 'user', content: prompt }]);
      const validation = JSON.parse(response.content);
      
      return {
        isValid: validation.isValid || false,
        confidence: validation.confidence || 0.5,
        issues: validation.issues || []
      };
    } catch (error) {
      console.error('Validation failed:', error);
      return {
        isValid: true, // Default to valid if validation fails
        confidence: 0.3,
        issues: ['Validation system error']
      };
    }
  }

  /**
   * Graceful Degradation (Agentic RAG)
   * Handles cases where information is insufficient
   */
  async handleInsufficientInfo(
    query: string,
    context: RAGContext
  ): Promise<string> {
    const memoryContext = await this.longTermMemory.generateMemoryContext(
      `Insufficient info: ${query}`,
      'graceful_degradation',
      'general',
      ['degradation', 'uncertainty']
    );

    const prompt = `Handle insufficient information gracefully:

QUERY: ${query}
CONTEXT: ${context.currentStep}
MEMORY CONTEXT: ${memoryContext}

Provide a helpful response that acknowledges the limitation and suggests alternatives.`;

    try {
      const response = await this.llm.invoke([{ role: 'user', content: prompt }]);
      return response.content;
    } catch (error) {
      console.error('Graceful degradation failed:', error);
      return "I don't have enough information to provide a complete answer. Could you provide more details?";
    }
  }

  /**
   * Learn from Experience (A-MEM)
   * Records successful and failed attempts for future learning
   */
  async learnFromExperience(
    query: string,
    approach: string,
    outcome: 'success' | 'failure' | 'partial',
    result: string,
    _context: RAGContext
  ): Promise<void> {
    const experience = `Query: ${query}\nApproach: ${approach}\nOutcome: ${outcome}\nResult: ${result}`;
    
    await this.longTermMemory.learnFromTask(
      query,
      outcome,
      experience,
      'rag_execution'
    );
  }

  /**
   * Get Memory Context for Decision Making
   */
  async getMemoryContext(
    query: string,
    step: string,
    category?: string,
    tags?: string[]
  ): Promise<string> {
    return await this.longTermMemory.generateMemoryContext(
      query,
      step,
      category,
      tags
    );
  }

  /**
   * Get Long-term Memory Statistics
   */
  getLongTermMemoryStats() {
    return this.longTermMemory.getMemoryStats();
  }

  /**
   * Get All Long-term Memories (for debugging)
   */
  getAllLongTermMemories() {
    return this.longTermMemory.getAllMemories();
  }
}
