import { BaseLanguageModel } from '@langchain/core/language_models/base';

export interface MemoryEntry {
    id: string;
    type: 'success' | 'failure' | 'lesson' | 'pattern';
    category: string;
    content: string;
    context: string;
    examples: string[];
    confidence: number;
    timestamp: Date;
    tags: string[];
}

export interface MemoryQuery {
    taskType: string;
    currentStep: string;
    recentFailures: string[];
    availableTools: string[];
    maxResults?: number;
}

export class LightweightMemoryRAG {
    private memories: MemoryEntry[] = [];
    private llm: BaseLanguageModel;
    private maxMemories: number = 1000; // Keep it lightweight

    constructor(llm: BaseLanguageModel) {
        this.llm = llm;
        this.initializeDefaultMemories();
    }

    /**
     * Initialize with default memories (similar to current system)
     */
    private initializeDefaultMemories(): void {
        const defaultMemories: Omit<MemoryEntry, 'id' | 'timestamp'>[] = [
            {
                type: 'success',
                category: 'code_generation',
                content: 'Python code must include test execution block to produce output when run',
                context: 'When generating Python code for LeetCode problems or any executable code',
                examples: [
                    'def solve(nums): return sum(nums)\n\nif __name__ == "__main__":\n    print(solve([1,2,3]))',
                    'def numberOfPairs(nums):\n    # implementation\n    return [pairs, leftovers]\n\nif __name__ == "__main__":\n    test_input = [1,1,2,2,3]\n    result = numberOfPairs(test_input)\n    print(f"Input: {test_input}")\n    print(f"Output: {result}")'
                ],
                confidence: 1.0,
                tags: ['python', 'leetcode', 'execution', 'test', 'output']
            },
            {
                type: 'success',
                category: 'output_capture',
                content: 'Use shell redirection to capture command output for verification',
                context: 'When executing commands that should produce verifiable output',
                examples: [
                    'python3 script.py > output.txt 2>&1',
                    'echo "test" | python3 script.py > output.txt'
                ],
                confidence: 1.0,
                tags: ['shell', 'redirection', 'output', 'capture', 'verification']
            },
            {
                type: 'failure',
                category: 'code_generation',
                content: 'Function-only code without execution produces no output when run',
                context: 'When writing Python code that needs to be tested or verified',
                examples: [
                    'def solve(nums): return sum(nums)  # No output when run',
                    'def numberOfPairs(nums): return [pairs, leftovers]  # No output when run'
                ],
                confidence: 1.0,
                tags: ['python', 'function', 'no-output', 'failure', 'execution']
            },
            {
                type: 'lesson',
                category: 'error_handling',
                content: 'If read_file fails with "file not found", check if previous command actually succeeded',
                context: 'When trying to read output files after command execution',
                examples: [
                    'Command: python3 script.py > output.txt 2>&1\nResult: Exit code 2 (failure)\nThen: read_file("output.txt") fails because file was never created'
                ],
                confidence: 1.0,
                tags: ['error', 'file-not-found', 'command-failure', 'debugging']
            },
            {
                type: 'success',
                category: 'debugging',
                content: 'When Python execution fails with Exit Code 2, check syntax first using py_compile',
                context: 'When Python code fails to execute and produces no output',
                examples: [
                    'python3 -m py_compile solution.py  # Check syntax',
                    'python3 solution.py  # Run without redirection to see errors'
                ],
                confidence: 1.0,
                tags: ['python', 'debugging', 'syntax-error', 'exit-code-2']
            },
            {
                type: 'success',
                category: 'workspace_awareness',
                content: 'Always use workspace directory when executing commands in remote environment',
                context: 'When working with remote files that are written to workspace directory',
                examples: [
                    'cd /home/ec2-user/workspace && python3 solution.py',
                    'python3 /home/ec2-user/workspace/solution.py'
                ],
                confidence: 1.0,
                tags: ['workspace', 'remote', 'file-path', 'execution']
            },
            {
                type: 'success',
                category: 'execution_memory',
                content: 'When Python execution succeeds with Exit Code 0, immediately read the output file to show validator evidence',
                context: 'After successful code execution, always read output.txt to provide evidence to validator',
                examples: [
                    'python3 solution.py > output.txt 2>&1  # Exit Code: 0',
                    'read_file("output.txt")  # Show results to validator',
                    'Don\'t rewrite files after successful execution - read output instead'
                ],
                confidence: 1.0,
                tags: ['execution', 'success', 'output', 'validator', 'memory']
            }
        ];

        defaultMemories.forEach(memory => {
            this.addMemory({
                ...memory,
                id: this.generateId(),
                timestamp: new Date()
            });
        });
    }

    /**
     * Add a new memory entry
     */
    addMemory(memory: MemoryEntry): void {
        this.memories.push(memory);
        
        // Keep only the most recent memories to stay lightweight
        if (this.memories.length > this.maxMemories) {
            this.memories = this.memories
                .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
                .slice(0, this.maxMemories);
        }
    }

    /**
     * Query memories using lightweight semantic matching
     */
    async queryMemories(query: MemoryQuery): Promise<MemoryEntry[]> {
        const { taskType, currentStep, recentFailures, maxResults = 5 } = query;
        
        // Step 1: Tag-based filtering (fast)
        const relevantMemories = this.filterByTags(taskType, currentStep, recentFailures);
        
        // Step 2: Lightweight semantic scoring using LLM (not vector embeddings)
        const scoredMemories = await this.scoreMemories(relevantMemories, query);
        
        // Step 3: Return top results
        return scoredMemories
            .sort((a, b) => b.confidence - a.confidence)
            .slice(0, maxResults);
    }

    /**
     * Fast tag-based filtering
     */
    private filterByTags(taskType: string, currentStep: string, recentFailures: string[]): MemoryEntry[] {
        const queryTags = new Set<string>();
        
        // Add tags based on task type
        if (taskType === 'leetcode') {
            queryTags.add('python');
            queryTags.add('leetcode');
            queryTags.add('code');
        }
        if (taskType === 'calculation') {
            queryTags.add('math');
            queryTags.add('calculation');
        }
        
        // Add tags based on current step
        if (currentStep.includes('write') || currentStep.includes('code')) {
            queryTags.add('code_generation');
            queryTags.add('python');
        }
        if (currentStep.includes('execute') || currentStep.includes('run')) {
            queryTags.add('execution');
            queryTags.add('output');
        }
        if (currentStep.includes('read') || currentStep.includes('file')) {
            queryTags.add('file');
            queryTags.add('output');
        }
        
        // Add tags based on recent failures
        if (recentFailures.some(f => f.includes('file not found'))) {
            queryTags.add('file-not-found');
            queryTags.add('error');
        }
        if (recentFailures.some(f => f.includes('exit code'))) {
            queryTags.add('command-failure');
            queryTags.add('error');
        }
        
        // Filter memories that have at least one matching tag
        return this.memories.filter(memory => 
            memory.tags.some(tag => queryTags.has(tag))
        );
    }

    /**
     * Lightweight semantic scoring using LLM (not vector embeddings)
     */
    private async scoreMemories(memories: MemoryEntry[], query: MemoryQuery): Promise<MemoryEntry[]> {
        if (memories.length === 0) return [];
        
        // Create a simple prompt to score relevance
        const memoryDescriptions = memories.map((mem, i) => 
            `${i + 1}. [${mem.type.toUpperCase()}] ${mem.content}\n   Context: ${mem.context}\n   Tags: ${mem.tags.join(', ')}`
        ).join('\n\n');

        const prompt = `Rate the relevance of each memory to this query context:

QUERY CONTEXT:
- Task Type: ${query.taskType}
- Current Step: ${query.currentStep}
- Recent Failures: ${query.recentFailures.join(', ') || 'None'}
- Available Tools: ${query.availableTools.join(', ')}

MEMORIES:
${memoryDescriptions}

Rate each memory's relevance from 0.0 to 1.0:
- 1.0: Perfectly relevant, directly addresses the current situation
- 0.8-0.9: Highly relevant, provides valuable guidance
- 0.6-0.7: Moderately relevant, some useful information
- 0.4-0.5: Somewhat relevant, minimal value
- 0.0-0.3: Not relevant, doesn't help with current situation

Respond with ONLY the scores in order, one per line:
0.8
0.3
0.9
...`;

        try {
            const response = await this.llm.invoke(prompt);
            const scores = this.parseScores(String(response.content || ''));
            
            // Update memory confidence with relevance scores
            return memories.map((memory, index) => ({
                ...memory,
                confidence: scores[index] || 0.1
            }));
        } catch (error) {
            console.error('Failed to score memories:', error);
            // Return memories with original confidence if scoring fails
            return memories;
        }
    }

    /**
     * Parse scores from LLM response
     */
    private parseScores(content: string): number[] {
        const lines = content.split('\n');
        const scores: number[] = [];
        
        for (const line of lines) {
            const match = line.match(/^(\d+\.?\d*)$/);
            if (match && match[1]) {
                const score = parseFloat(match[1]);
                if (score >= 0 && score <= 1) {
                    scores.push(score);
                }
            }
        }
        
        return scores;
    }

    /**
     * Generate memory-enhanced context for LLM calls
     */
    async generateMemoryContext(query: MemoryQuery): Promise<string> {
        const relevantMemories = await this.queryMemories(query);
        
        if (relevantMemories.length === 0) {
            return '';
        }

        const memoryContext = relevantMemories.map(memory => {
            const examples = memory.examples.slice(0, 2).join('\n');
            return `MEMORY [${memory.type.toUpperCase()}]: ${memory.content}\nContext: ${memory.context}\nExamples:\n${examples}`;
        }).join('\n\n');

        return `\n\n# MEMORY-BASED GUIDANCE:\n${memoryContext}\n\n# CRITICAL: Follow the patterns above to avoid known failures and replicate known successes.\n`;
    }

    /**
     * Learn from task execution and add new memories
     */
    async learnFromTask(
        _taskId: string,
        taskType: string,
        scratchpad: any[],
        finalOutcome: 'success' | 'failure' | 'partial'
    ): Promise<void> {
        // Extract lessons using LLM
        const lessons = await this.extractLessons(scratchpad, finalOutcome);
        
        // Create memory entries for new lessons
        for (const lesson of lessons) {
            const memory: MemoryEntry = {
                id: this.generateId(),
                type: 'lesson',
                category: this.categorizeLesson(lesson),
                content: lesson,
                context: `Learned from ${taskType} task execution`,
                examples: this.extractExamplesFromScratchpad(scratchpad),
                confidence: 0.8, // Start with high confidence for learned lessons
                timestamp: new Date(),
                tags: this.generateTagsFromLesson(lesson, taskType)
            };
            
            this.addMemory(memory);
        }
    }

    /**
     * Extract lessons from scratchpad using LLM
     */
    private async extractLessons(scratchpad: any[], outcome: string): Promise<string[]> {
        const scratchpadText = scratchpad.map(entry => 
            `Step: ${entry.step}\nTool: ${entry.tool || 'none'}\nSuccess: ${entry.success}\nObservation: ${entry.observation}`
        ).join('\n\n');

        const prompt = `Analyze this task execution and extract 1-2 key lessons learned.

OUTCOME: ${outcome}

EXECUTION LOG:
${scratchpadText}

Extract concise, actionable lessons that would help in similar future tasks. Focus on:
1. What worked well and should be repeated
2. What failed and should be avoided

Respond with lessons in this format:
LESSON: [specific actionable lesson]`;

        try {
            const response = await this.llm.invoke(prompt);
            const content = String(response.content || '');
            return this.parseLessons(content);
        } catch (error) {
            console.error('Failed to extract lessons:', error);
            return [];
        }
    }

    /**
     * Parse lessons from LLM response
     */
    private parseLessons(content: string): string[] {
        const lessons: string[] = [];
        const lines = content.split('\n');
        
        for (const line of lines) {
            const match = line.match(/^LESSON:\s*(.+)$/i);
            if (match && match[1]) {
                lessons.push(match[1].trim());
            }
        }
        
        return lessons;
    }

    /**
     * Categorize a lesson
     */
    private categorizeLesson(lesson: string): string {
        const lowerLesson = lesson.toLowerCase();
        if (lowerLesson.includes('code') || lowerLesson.includes('python') || lowerLesson.includes('function')) {
            return 'code_generation';
        }
        if (lowerLesson.includes('execute') || lowerLesson.includes('run') || lowerLesson.includes('command')) {
            return 'execution';
        }
        if (lowerLesson.includes('file') || lowerLesson.includes('read') || lowerLesson.includes('write')) {
            return 'file_operations';
        }
        if (lowerLesson.includes('error') || lowerLesson.includes('fail') || lowerLesson.includes('debug')) {
            return 'error_handling';
        }
        return 'general';
    }

    /**
     * Extract examples from scratchpad
     */
    private extractExamplesFromScratchpad(scratchpad: any[]): string[] {
        const examples: string[] = [];
        
        for (const entry of scratchpad) {
            if (entry.observation && entry.observation.length > 10) {
                examples.push(entry.observation.slice(0, 200));
            }
        }
        
        return examples.slice(0, 3); // Keep only first 3 examples
    }

    /**
     * Generate tags from lesson content
     */
    private generateTagsFromLesson(lesson: string, taskType: string): string[] {
        const tags = new Set<string>();
        
        // Add task type tag
        tags.add(taskType);
        
        // Add content-based tags
        const lowerLesson = lesson.toLowerCase();
        if (lowerLesson.includes('python')) tags.add('python');
        if (lowerLesson.includes('code')) tags.add('code');
        if (lowerLesson.includes('execute')) tags.add('execution');
        if (lowerLesson.includes('file')) tags.add('file');
        if (lowerLesson.includes('error')) tags.add('error');
        if (lowerLesson.includes('output')) tags.add('output');
        if (lowerLesson.includes('test')) tags.add('test');
        
        return Array.from(tags);
    }

    /**
     * Generate unique ID
     */
    private generateId(): string {
        return `mem_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Get memory statistics
     */
    getMemoryStats(): {
        totalMemories: number;
        byType: Record<string, number>;
        byCategory: Record<string, number>;
        averageConfidence: number;
    } {
        const byType: Record<string, number> = {};
        const byCategory: Record<string, number> = {};
        let totalConfidence = 0;
        
        for (const memory of this.memories) {
            byType[memory.type] = (byType[memory.type] || 0) + 1;
            byCategory[memory.category] = (byCategory[memory.category] || 0) + 1;
            totalConfidence += memory.confidence;
        }
        
        return {
            totalMemories: this.memories.length,
            byType,
            byCategory,
            averageConfidence: this.memories.length > 0 ? totalConfidence / this.memories.length : 0
        };
    }
}
