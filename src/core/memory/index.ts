/**
 * Rich Memory System Exports
 * 
 * Central export point for all rich memory system components.
 * Provides a clean interface for importing memory functionality.
 */

// Core types and interfaces
export * from './rich-memory-types';

// Core components
export { RichMemoryManager } from './rich-memory-manager';
export { FileRegistry } from './file-registry';
export { CodeDocumentation } from './code-documentation';
export { RichCompletionRules } from './rich-completion-rules';
export { RichLoopPrevention } from './rich-loop-prevention';

// Factory function for easy initialization
export function createRichMemorySystem() {
  const { RichMemoryManager } = require('./rich-memory-manager');
  return new RichMemoryManager();
}

// Utility functions
export function detectTaskType(query: string): import('./rich-memory-types').TaskType {
  // Simple question patterns
  const simplePatterns = [
    /what is \d+[\+\-\*\/]\d+\?/i,
    /^\d+[\+\-\*\/]\d+$/i,
    /what is \d+ plus \d+\?/i,
    /what is \d+ minus \d+\?/i,
    /what is \d+ times \d+\?/i,
    /what is \d+ divided by \d+\?/i
  ];
  
  if (simplePatterns.some(pattern => pattern.test(query.trim()))) {
    return 'simple_question';
  }
  
  // Coding task patterns
  const codingPatterns = [
    /leetcode/i,
    /implement/i,
    /code/i,
    /function/i,
    /algorithm/i,
    /solve.*problem/i,
    /create.*script/i,
    /write.*program/i
  ];
  
  if (codingPatterns.some(pattern => pattern.test(query.trim()))) {
    return 'coding_task';
  }
  
  // Research task patterns
  const researchPatterns = [
    /research/i,
    /find information/i,
    /search for/i,
    /analyze/i,
    /investigate/i,
    /study/i,
    /explore/i
  ];
  
  if (researchPatterns.some(pattern => pattern.test(query.trim()))) {
    return 'research_task';
  }
  
  // Default to general task
  return 'general_task';
}

// Validation utilities
export function validateTaskCompletion(
  context: import('./rich-memory-types').RichTaskContext
): boolean {
  const { RichCompletionRules } = require('./rich-completion-rules');
  const completionRules = new RichCompletionRules();
  return completionRules.checkCompletion(context);
}

export function getRequiredEvidence(
  taskType: import('./rich-memory-types').TaskType
): import('./rich-memory-types').EvidenceType[] {
  const { RichCompletionRules } = require('./rich-completion-rules');
  const completionRules = new RichCompletionRules();
  return completionRules.getRequiredEvidence(taskType);
}

// File utilities
export function createFileReference(
  filePath: string,
  content: string,
  fileType: import('./rich-memory-types').FileType,
  createdBy: string
): import('./rich-memory-types').FileReference {
  const { FileRegistry } = require('./file-registry');
  const fileRegistry = new FileRegistry();
  return fileRegistry.createFileReference(filePath, content, fileType, createdBy);
}

// Code analysis utilities
export function analyzeCode(
  fileId: string,
  content: string,
  language: import('./rich-memory-types').ProgrammingLanguage
): import('./rich-memory-types').CodeReference {
  const { CodeDocumentation } = require('./code-documentation');
  const codeDocumentation = new CodeDocumentation();
  return codeDocumentation.analyzeCode(fileId, content, language);
}

// Loop prevention utilities
export function detectLoop(
  taskId: string,
  context: import('./rich-memory-types').RichTaskContext
): boolean {
  const { RichLoopPrevention } = require('./rich-loop-prevention');
  const loopPrevention = new RichLoopPrevention();
  return loopPrevention.detectRichLoop(taskId, context);
}

// Constants
export const DEFAULT_CONFIG = {
  maxIterations: 40,
  maxDuplicateActions: 3,
  maxValidationActions: 5,
  maxEvidenceStagnationMinutes: 2,
  maxActionStagnationMinutes: 5
} as const;

export const TASK_TYPE_PATTERNS = {
  simple_question: [
    /what is \d+[\+\-\*\/]\d+\?/i,
    /^\d+[\+\-\*\/]\d+$/i,
    /what is \d+ plus \d+\?/i,
    /what is \d+ minus \d+\?/i,
    /what is \d+ times \d+\?/i,
    /what is \d+ divided by \d+\?/i
  ],
  coding_task: [
    /leetcode/i,
    /implement/i,
    /code/i,
    /function/i,
    /algorithm/i,
    /solve.*problem/i,
    /create.*script/i,
    /write.*program/i
  ],
  research_task: [
    /research/i,
    /find information/i,
    /search for/i,
    /analyze/i,
    /investigate/i,
    /study/i,
    /explore/i
  ]
} as const;

export const EVIDENCE_TYPE_DESCRIPTIONS = {
  file_creation: 'File was created or written',
  code_implementation: 'Code was implemented with functions/classes',
  documentation: 'Documentation was created or updated',
  synthesis: 'Information was synthesized or summarized',
  execution: 'Action was executed successfully',
  validation: 'Task was validated or checked'
} as const;
