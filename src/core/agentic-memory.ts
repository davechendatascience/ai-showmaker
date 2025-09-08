import { BaseLanguageModel } from '@langchain/core/language_models/base';

/**
 * Long-term Memory System for LLM Agents
 * 
 * This system provides persistent memory that survives across sessions.
 * Uses LLM agents to dynamically manage long-term knowledge instead of hardcoded rules.
 * Inspired by the Zettelkasten method and A-MEM research, it creates interconnected
 * knowledge networks through dynamic indexing and linking.
 */

export interface MemoryNode {
  id: string;
  content: string;
  context: string;
  keywords: string[];
  tags: string[];
  connections: string[]; // IDs of connected memories
  confidence: number;
  timestamp: Date;
  category: string;
  examples: string[];
  evolutionHistory: string[]; // Track how this memory evolved
}

export interface MemoryQuery {
  query: string;
  context?: string | undefined;
  category?: string | undefined;
  tags?: string[] | undefined;
  limit?: number | undefined;
}

export interface MemoryExtraction {
  content: string;
  context: string;
  keywords: string[];
  tags: string[];
  category: string;
  examples: string[];
  confidence: number;
}

export interface MemoryRetrieval {
  memories: MemoryNode[];
  reasoning: string;
  confidence: number;
}

export interface MemoryConsolidation {
  newMemories: MemoryNode[];
  updatedMemories: MemoryNode[];
  connections: Array<{ from: string; to: string; reason: string }>;
  reasoning: string;
}

/**
 * Long-term Memory System with Agentic Management
 */
export class LongTermMemorySystem {
  private memories: Map<string, MemoryNode> = new Map();
  private memoryLLM: BaseLanguageModel; // Separate LLM for memory operations
  private nextId: number = 1;

  constructor(memoryLLM: BaseLanguageModel) {
    this.memoryLLM = memoryLLM;
    // Start with empty memory - let the system learn dynamically
  }

  /**
   * Memory Extraction Agent
   * Uses LLM to dynamically extract structured memory from experiences
   */
  async extractMemory(
    experience: string,
    context: string,
    outcome: 'success' | 'failure' | 'partial',
    taskType?: string
  ): Promise<MemoryExtraction> {
    const prompt = `You are a Memory Extraction Agent. Extract structured memory from this experience:

EXPERIENCE: ${experience}
CONTEXT: ${context}
OUTCOME: ${outcome}
TASK_TYPE: ${taskType || 'general'}

Extract the following information as JSON:
{
  "content": "Core lesson or pattern learned",
  "context": "When this applies",
  "keywords": ["key", "terms", "concepts"],
  "tags": ["category", "tags"],
  "category": "success|failure|debugging|execution|workspace|general",
  "examples": ["specific", "examples"],
  "confidence": 0.0-1.0
}

Focus on actionable insights that can guide future behavior.`;

    try {
      const response = await this.memoryLLM.invoke([{ role: 'user', content: prompt }]);
      const extraction = JSON.parse(response.content);
      
      return {
        content: extraction.content,
        context: extraction.context,
        keywords: extraction.keywords || [],
        tags: extraction.tags || [],
        category: extraction.category || 'general',
        examples: extraction.examples || [],
        confidence: extraction.confidence || 0.5
      };
    } catch (error) {
      console.error('Memory extraction failed:', error);
      // Fallback extraction
      return {
        content: experience,
        context: context,
        keywords: [outcome, taskType || 'general'],
        tags: [outcome, 'extraction-fallback'],
        category: outcome,
        examples: [experience],
        confidence: 0.3
      };
    }
  }

  /**
   * Memory Retrieval Agent
   * Uses LLM to dynamically find relevant memories for a query
   */
  async retrieveMemories(query: MemoryQuery): Promise<MemoryRetrieval> {
    const allMemories = Array.from(this.memories.values());
    
    console.log(`[LongTermMemory] Retrieval query: "${query.query}"`);
    console.log(`[LongTermMemory] Total memories available: ${allMemories.length}`);
    
    if (allMemories.length === 0) {
      console.log(`[LongTermMemory] No memories available for retrieval`);
      return {
        memories: [],
        reasoning: 'No memories available',
        confidence: 0.0
      };
    }

    // Log all available memories for debugging
    console.log(`[LongTermMemory] Available memories:`);
    allMemories.forEach((m, i) => {
      console.log(`[LongTermMemory]   ${i+1}. ID: ${m.id}, Content: "${m.content.substring(0, 50)}...", Tags: [${m.tags.join(', ')}], Category: ${m.category}`);
    });

    const prompt = `You are a Memory Retrieval Agent. Find relevant memories for this query:

QUERY: ${query.query}
CONTEXT: ${query.context || 'general'}
CATEGORY: ${query.category || 'any'}
TAGS: ${query.tags?.join(', ') || 'any'}
LIMIT: ${query.limit || 5}

Available memories:
${allMemories.map(m => 
  `ID: ${m.id}
Content: ${m.content}
Context: ${m.context}
Tags: ${m.tags.join(', ')}
Category: ${m.category}
Confidence: ${m.confidence}`
).join('\n\n')}

Return JSON with:
{
  "relevant_ids": ["id1", "id2", ...],
  "reasoning": "Why these memories are relevant",
  "confidence": 0.0-1.0
}

Select memories that are most relevant to the query.`;

    try {
      console.log(`[LongTermMemory] Sending retrieval prompt to LLM...`);
      const response = await this.memoryLLM.invoke([{ role: 'user', content: prompt }]);
      console.log(`[LongTermMemory] LLM response: ${response.content}`);
      
      const result = JSON.parse(response.content);
      console.log(`[LongTermMemory] Parsed result:`, result);
      
      const relevantMemories = result.relevant_ids
        .map((id: string) => {
          const memory = this.memories.get(id);
          console.log(`[LongTermMemory] Looking for memory ID: ${id}, found: ${memory ? 'YES' : 'NO'}`);
          return memory;
        })
        .filter((memory: MemoryNode | undefined) => memory !== undefined)
        .slice(0, query.limit || 5);

      console.log(`[LongTermMemory] Retrieved ${relevantMemories.length} memories after filtering`);

      return {
        memories: relevantMemories,
        reasoning: result.reasoning,
        confidence: result.confidence
      };
    } catch (error) {
      console.error('[LongTermMemory] Memory retrieval failed:', error);
      // Fallback: return memories with matching tags
      const fallbackMemories = allMemories
        .filter(m => 
          query.tags ? query.tags.some(tag => m.tags.includes(tag)) : true
        )
        .sort((a, b) => b.confidence - a.confidence)
        .slice(0, query.limit || 5);

      return {
        memories: fallbackMemories,
        reasoning: 'Fallback retrieval based on tag matching',
        confidence: 0.3
      };
    }
  }

  /**
   * Memory Consolidation Agent
   * Uses LLM to dynamically consolidate and connect memories
   */
  async consolidateMemories(
    newExtraction: MemoryExtraction,
    existingMemories: MemoryNode[]
  ): Promise<MemoryConsolidation> {
    const prompt = `You are a Memory Consolidation Agent. Consolidate this new memory with existing ones:

NEW MEMORY:
Content: ${newExtraction.content}
Context: ${newExtraction.context}
Tags: ${newExtraction.tags.join(', ')}
Category: ${newExtraction.category}

EXISTING MEMORIES:
${existingMemories.map(m => 
  `ID: ${m.id}
Content: ${m.content}
Context: ${m.context}
Tags: ${m.tags.join(', ')}
Category: ${m.category}`
).join('\n\n')}

IMPORTANT: Create NEW memories for distinct experiences. Only update existing memories if they are EXACTLY the same concept.
- If the new memory is about a different tool, task, or outcome, CREATE A NEW MEMORY
- If the new memory adds new information to an existing concept, CREATE A NEW MEMORY
- Only update if it's the exact same memory being reinforced

Return JSON with:
{
  "should_create_new": true/false,
  "should_update_existing": ["id1", "id2", ...],
  "connections": [{"from": "new_id", "to": "existing_id", "reason": "why connected"}],
  "reasoning": "Consolidation strategy explanation"
}

Decide whether to create a new memory, update existing ones, or both.`;

    try {
      console.log(`[LongTermMemory] Consolidation prompt sent to LLM...`);
      const response = await this.memoryLLM.invoke([{ role: 'user', content: prompt }]);
      console.log(`[LongTermMemory] Consolidation LLM response: ${response.content}`);
      
      const result = JSON.parse(response.content);
      console.log(`[LongTermMemory] Consolidation decision:`, result);
      
      const newMemories: MemoryNode[] = [];
      const updatedMemories: MemoryNode[] = [];
      const connections: Array<{ from: string; to: string; reason: string }> = [];

      if (result.should_create_new) {
        const newMemory = this.createMemoryNode(newExtraction);
        newMemories.push(newMemory);
        
        // Add connections
        result.connections?.forEach((conn: any) => {
          if (conn.from === 'new_id') {
            connections.push({
              from: newMemory.id,
              to: conn.to,
              reason: conn.reason
            });
          }
        });
      }

      // Update existing memories
      result.should_update_existing?.forEach((id: string) => {
        const existing = this.memories.get(id);
        if (existing) {
          const updated = this.updateMemoryNode(existing, newExtraction);
          updatedMemories.push(updated);
          this.memories.set(id, updated);
        }
      });

      // Safety check: if no new memories and no updates, force create a new memory
      if (newMemories.length === 0 && updatedMemories.length === 0) {
        console.log(`[LongTermMemory] Consolidation too conservative, forcing new memory creation`);
        const newMemory = this.createMemoryNode(newExtraction);
        newMemories.push(newMemory);
      }

      return {
        newMemories,
        updatedMemories,
        connections,
        reasoning: result.reasoning
      };
    } catch (error) {
      console.error('Memory consolidation failed:', error);
      // Fallback: create new memory
      const newMemory = this.createMemoryNode(newExtraction);
      return {
        newMemories: [newMemory],
        updatedMemories: [],
        connections: [],
        reasoning: 'Fallback: created new memory due to consolidation failure'
      };
    }
  }

  /**
   * Add a new experience to memory using agentic extraction and consolidation
   */
  async addExperience(
    experience: string,
    context: string,
    outcome: 'success' | 'failure' | 'partial',
    taskType?: string
  ): Promise<string[]> {
    console.log(`[LongTermMemory] Adding experience: "${experience.substring(0, 100)}..."`);
    console.log(`[LongTermMemory] Context: ${context}, Outcome: ${outcome}, TaskType: ${taskType || 'none'}`);
    
    // Step 1: Extract memory using extraction agent
    const extraction = await this.extractMemory(experience, context, outcome, taskType);
    console.log(`[LongTermMemory] Extracted memory: "${extraction.content}"`);
    
    // Step 2: Retrieve potentially related memories
    const relatedMemories = await this.retrieveMemories({
      query: extraction.content,
      context: extraction.context,
      category: extraction.category,
      tags: extraction.tags,
      limit: 10
    });
    
    // Step 3: Consolidate with existing memories
    const consolidation = await this.consolidateMemories(extraction, relatedMemories.memories);
    console.log(`[LongTermMemory] Consolidation result: ${consolidation.newMemories.length} new memories, ${consolidation.updatedMemories.length} updated memories`);
    
    // Step 4: Store new memories
    const newMemoryIds: string[] = [];
    consolidation.newMemories.forEach(memory => {
      console.log(`[LongTermMemory] Storing new memory: ID=${memory.id}, Content="${memory.content.substring(0, 50)}..."`);
      this.memories.set(memory.id, memory);
      newMemoryIds.push(memory.id);
    });
    
    console.log(`[LongTermMemory] Total memories after storage: ${this.memories.size}`);
    
    // Step 5: Update connections
    consolidation.connections.forEach(conn => {
      const fromMemory = this.memories.get(conn.from);
      const toMemory = this.memories.get(conn.to);
      if (fromMemory && toMemory) {
        fromMemory.connections.push(conn.to);
        toMemory.connections.push(conn.from);
      }
    });
    
    return newMemoryIds;
  }

  /**
   * Generate memory context for a query using retrieval agent
   */
  async generateMemoryContext(
    query: string,
    context?: string,
    category?: string,
    tags?: string[]
  ): Promise<string> {
    console.log(`[LongTermMemory] Generating context for query: "${query}"`);
    console.log(`[LongTermMemory] Context: ${context || 'none'}, Category: ${category || 'none'}, Tags: ${tags?.join(', ') || 'none'}`);
    
    const retrieval = await this.retrieveMemories({
      query,
      context,
      category,
      tags,
      limit: 5
    });

    console.log(`[LongTermMemory] Retrieved ${retrieval.memories.length} memories`);
    retrieval.memories.forEach((m, i) => {
      console.log(`[LongTermMemory] Memory ${i+1}: "${m.content.substring(0, 100)}..." (confidence: ${m.confidence.toFixed(2)})`);
    });

    if (retrieval.memories.length === 0) {
      console.log(`[LongTermMemory] No relevant memories found for query: "${query}"`);
      return 'No relevant memories found.';
    }

    const memoryContext = retrieval.memories
      .map(memory => 
        `Memory: ${memory.content}\nContext: ${memory.context}\nExamples: ${memory.examples.join(', ')}`
      )
      .join('\n\n');

    console.log(`[LongTermMemory] Generated context: ${memoryContext.substring(0, 200)}...`);
    return `Relevant Memories:\n${memoryContext}\n\nReasoning: ${retrieval.reasoning}`;
  }

  /**
   * Learn from a task outcome using agentic memory
   */
  async learnFromTask(
    task: string,
    outcome: 'success' | 'failure' | 'partial',
    evidence: string,
    taskType?: string
  ): Promise<void> {
    console.log(`[LongTermMemory] Learning from task: "${task}" with outcome: ${outcome}`);
    console.log(`[LongTermMemory] Evidence: ${evidence.substring(0, 200)}...`);
    
    const experience = `Task: ${task}\nOutcome: ${outcome}\nEvidence: ${evidence}`;
    const context = `Task execution with ${outcome} outcome`;
    
    await this.addExperience(experience, context, outcome, taskType);
    console.log(`[LongTermMemory] Successfully learned from task outcome`);
  }

  /**
   * Get all memories (for debugging)
   */
  getAllMemories(): MemoryNode[] {
    return Array.from(this.memories.values());
  }

  /**
   * Get memory statistics
   */
  getMemoryStats(): {
    totalMemories: number;
    categories: Record<string, number>;
    avgConfidence: number;
  } {
    const memories = Array.from(this.memories.values());
    const categories: Record<string, number> = {};
    let totalConfidence = 0;

    memories.forEach(memory => {
      categories[memory.category] = (categories[memory.category] || 0) + 1;
      totalConfidence += memory.confidence;
    });

    return {
      totalMemories: memories.length,
      categories,
      avgConfidence: memories.length > 0 ? totalConfidence / memories.length : 0
    };
  }

  private createMemoryNode(extraction: MemoryExtraction): MemoryNode {
    const id = `mem_${this.nextId++}`;
    return {
      id,
      content: extraction.content,
      context: extraction.context,
      keywords: extraction.keywords,
      tags: extraction.tags,
      connections: [],
      confidence: extraction.confidence,
      timestamp: new Date(),
      category: extraction.category,
      examples: extraction.examples,
      evolutionHistory: [`Created from extraction: ${extraction.content}`]
    };
  }

  private updateMemoryNode(existing: MemoryNode, newExtraction: MemoryExtraction): MemoryNode {
    return {
      ...existing,
      content: `${existing.content}\n\nUpdated: ${newExtraction.content}`,
      keywords: [...new Set([...existing.keywords, ...newExtraction.keywords])],
      tags: [...new Set([...existing.tags, ...newExtraction.tags])],
      examples: [...existing.examples, ...newExtraction.examples],
      confidence: Math.max(existing.confidence, newExtraction.confidence),
      evolutionHistory: [
        ...existing.evolutionHistory,
        `Updated with: ${newExtraction.content}`
      ]
    };
  }

}
