/**
 * Rich Memory System Types
 * 
 * Core data structures for the rich context memory system that provides
 * evidence-based task tracking, file registry, and code documentation.
 */

// Core task types
export type TaskType = 'simple_question' | 'coding_task' | 'research_task' | 'general_task';

// Evidence types for tracking task progress
export type EvidenceType = 
  | 'file_creation' 
  | 'code_implementation' 
  | 'documentation' 
  | 'synthesis' 
  | 'execution' 
  | 'validation';

// File types for registry
export type FileType = 'code' | 'documentation' | 'data' | 'config' | 'output';

// Programming languages for code documentation
export type ProgrammingLanguage = 'python' | 'javascript' | 'typescript' | 'java' | 'cpp' | 'go' | 'rust' | 'other';

// Core task context
export interface RichTaskContext {
  taskId: string;
  taskType: TaskType;
  task: string;
  actions: RichAction[];
  evidence: Evidence[];
  files: FileReference[];
  complete: boolean;
  completionEvidence: CompletionEvidence[];
  timestamp: number;
  metadata: TaskMetadata;
  // Compatibility properties
  taskHash?: string;
  validationCount?: number;
  lastValidationTime?: Date;
  confidenceHistory?: number[];
}

// Rich action with evidence tracking
export interface RichAction {
  actionId: string;
  actionType: string;
  inputs: object;
  outputs: RichOutput;
  evidence: Evidence[];
  timestamp: number;
  success: boolean;
  context: ActionContext;
  // Compatibility properties
  type?: string;
  content?: string;
  reasoning?: string;
  confidence?: number;
  alternatives?: string[];
  tools?: string[];
  executionTime?: number;
}

// Rich output with file and code references
export interface RichOutput {
  success: boolean;
  result: string;
  files?: FileReference[];
  code?: CodeReference;
  documentation?: DocumentationReference;
  metadata: OutputMetadata;
}

// Action context
export interface ActionContext {
  taskId: string;
  agentId?: string;
  sessionId?: string;
}

// Evidence for task completion tracking
export interface Evidence {
  evidenceId: string;
  evidenceType: EvidenceType;
  content: string;
  confidence: number;
  source: string; // actionId or validationId
  timestamp: number;
  metadata: EvidenceMetadata;
  // Compatibility property
  description?: string;
}

// File reference with rich metadata
export interface FileReference {
  fileId: string;
  filePath: string;
  fileType: FileType;
  content: string;
  size: number;
  createdBy: string; // actionId
  createdAt: number;
  modifiedAt: number;
  metadata: FileMetadata;
  checksum: string;
}

// File metadata for code analysis
export interface FileMetadata {
  language?: ProgrammingLanguage;
  functions?: string[];
  classes?: string[];
  imports?: string[];
  dependencies?: string[];
  purpose?: string;
  documentation?: string;
  lineCount?: number;
  complexity?: number;
}

// Code reference with documentation
export interface CodeReference {
  codeId: string;
  fileId: string;
  language: ProgrammingLanguage;
  functions: FunctionDocumentation[];
  classes: ClassDocumentation[];
  imports: ImportReference[];
  dependencies: DependencyReference[];
  documentation: string;
  complexity: number;
  testCoverage?: number;
}

// Function documentation
export interface FunctionDocumentation {
  name: string;
  parameters: ParameterDocumentation[];
  returnType: string;
  description: string;
  examples: string[];
  complexity: number;
  lineStart: number;
  lineEnd: number;
}

// Class documentation
export interface ClassDocumentation {
  name: string;
  methods: MethodDocumentation[];
  properties: PropertyDocumentation[];
  description: string;
  inheritance?: string[];
  lineStart: number;
  lineEnd: number;
}

// Method documentation
export interface MethodDocumentation {
  name: string;
  parameters: ParameterDocumentation[];
  returnType: string;
  description: string;
  visibility: 'public' | 'private' | 'protected';
  lineStart: number;
  lineEnd: number;
}

// Property documentation
export interface PropertyDocumentation {
  name: string;
  type: string;
  description: string;
  visibility: 'public' | 'private' | 'protected';
  lineNumber: number;
}

// Parameter documentation
export interface ParameterDocumentation {
  name: string;
  type: string;
  description: string;
  required: boolean;
  defaultValue?: string;
}

// Import reference
export interface ImportReference {
  module: string;
  imports: string[];
  lineNumber: number;
  type: 'import' | 'from' | 'require';
}

// Dependency reference
export interface DependencyReference {
  name: string;
  version?: string;
  type: 'package' | 'module' | 'library';
  source: string;
}

// Documentation reference
export interface DocumentationReference {
  docId: string;
  title: string;
  type: 'readme' | 'api' | 'guide' | 'tutorial' | 'reference';
  content: string;
  wordCount: number;
  sections: DocumentationSection[];
  createdAt: number;
}

// Documentation section
export interface DocumentationSection {
  title: string;
  content: string;
  level: number;
  lineStart: number;
  lineEnd: number;
}

// Completion evidence
export interface CompletionEvidence {
  evidenceId: string;
  evidenceType: EvidenceType;
  content: string;
  confidence: number;
  source: string;
  timestamp: number;
  requirements: string[];
  validation: ValidationEvidence;
}

// Validation evidence
export interface ValidationEvidence {
  validatorId: string;
  confidence: number;
  rationale: string;
  requirements: string[];
  timestamp: number;
}

// Task metadata
export interface TaskMetadata {
  createdBy: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  estimatedComplexity: number;
  tags: string[];
  description?: string;
}

// Action context
export interface ActionContext {
  planId?: string;
  reasoning?: string;
  taskId: string;
  iteration?: number;
  parentActionId?: string;
}

// Output metadata
export interface OutputMetadata {
  executionTime: number;
  tool: string;
  timestamp: number;
  error?: string;
  warnings?: string[];
}

// Evidence metadata
export interface EvidenceMetadata {
  fileType?: FileType;
  fileSize?: number;
  language?: ProgrammingLanguage;
  functionCount?: number;
  complexity?: number;
  docType?: string;
  wordCount?: number;
  confidence?: number;
}

// Rich validation result
export interface RichValidationResult {
  completed: boolean;
  confidence: number;
  rationale: string;
  evidence: Evidence[];
  requirements: string[];
  missingRequirements?: string[];
  suggestions?: string[];
}

// Rich plan node
export interface RichPlanNode {
  id: string;
  action: string;
  tool: string;
  inputs: object;
  reasoning: string;
  score: number;
  expectedEvidence: EvidenceType[];
  scenarios?: any[];
}

// Memory manager interface
export interface IRichMemoryManager {
  createTask(task: string, taskType: TaskType): string;
  addAction(taskId: string, action: RichAction): void;
  setResult(taskId: string, result: string, resultType: string, filePath?: string): void;
  checkRichCompletion(taskId: string): boolean;
  getTaskContext(taskId: string): RichTaskContext | undefined;
  getActionHistory(taskId: string): RichAction[];
  getResult(taskId: string): string | null;
  getRichResult(taskId: string): RichOutput | null;
  getAllTasks(): RichTaskContext[];
  clearTask(taskId: string): void;
}

// File registry interface
export interface IFileRegistry {
  addFile(file: FileReference): void;
  getFile(fileId: string): FileReference | undefined;
  getFilesByType(fileType: FileType): FileReference[];
  getFilesByLanguage(language: ProgrammingLanguage): FileReference[];
  updateFile(fileId: string, updates: Partial<FileReference>): void;
  removeFile(fileId: string): void;
  getAllFiles(): FileReference[];
}

// Code documentation interface
export interface ICodeDocumentation {
  addCode(code: CodeReference): void;
  getCode(codeId: string): CodeReference | undefined;
  getCodeByFile(fileId: string): CodeReference | undefined;
  getFunctionsByLanguage(language: ProgrammingLanguage): FunctionDocumentation[];
  getClassesByLanguage(language: ProgrammingLanguage): ClassDocumentation[];
  updateCode(codeId: string, updates: Partial<CodeReference>): void;
  removeCode(codeId: string): void;
  getAllCode(): CodeReference[];
}

// Completion rules interface
export interface ICompletionRules {
  checkCompletion(context: RichTaskContext): boolean;
  getRequiredEvidence(taskType: TaskType): EvidenceType[];
  getCompletionCriteria(taskType: TaskType): string[];
}

// Loop prevention interface
export interface ILoopPrevention {
  detectRichLoop(taskId: string): boolean;
  getLoopReason(taskId: string): string | null;
  resetLoopCounters(taskId: string): void;
}
