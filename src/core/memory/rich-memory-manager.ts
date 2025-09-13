/**
 * Rich Memory Manager
 * 
 * Central manager for the rich context memory system. Coordinates all memory
 * components including task contexts, file registry, code documentation,
 * completion rules, and loop prevention.
 */

import { 
  RichTaskContext, 
  RichAction, 
  RichOutput,
  Evidence,
  TaskType,
  IRichMemoryManager,
  RichValidationResult,
  CompletionEvidence,
  FileReference
} from './rich-memory-types';
import { FileRegistry } from './file-registry';
import { CodeDocumentation } from './code-documentation';
import { RichCompletionRules } from './rich-completion-rules';
import { RichLoopPrevention } from './rich-loop-prevention';

export class RichMemoryManager implements IRichMemoryManager {
  private taskContexts: Map<string, RichTaskContext> = new Map();
  private fileRegistry: FileRegistry;
  private codeDocumentation: CodeDocumentation;
  private completionRules: RichCompletionRules;
  private loopPrevention: RichLoopPrevention;
  private currentTaskId: string | null = null;

  constructor() {
    this.fileRegistry = new FileRegistry();
    this.codeDocumentation = new CodeDocumentation();
    this.completionRules = new RichCompletionRules();
    this.loopPrevention = new RichLoopPrevention();
  }

  // Core task management
  createTask(task: string, taskType: TaskType): string {
    const taskId = this.generateTaskId();
    const context: RichTaskContext = {
      taskId,
      taskType,
      task,
      actions: [],
      evidence: [],
      files: [],
      complete: false,
      completionEvidence: [],
      timestamp: Date.now(),
      metadata: {
        createdBy: 'bfs_agent',
        priority: 'normal',
        estimatedComplexity: this.estimateComplexity(task, taskType),
        tags: [taskType],
        description: task
      }
    };
    
    this.taskContexts.set(taskId, context);
    this.currentTaskId = taskId;
    
    console.log(`[RichMemory] Created task context: ${taskId} (${taskType})`);
    return taskId;
  }

  addAction(taskId: string, action: RichAction): void {
    const context = this.taskContexts.get(taskId);
    if (!context) {
      console.warn(`[RichMemory] Task context not found: ${taskId}`);
      return;
    }
    
    // Add action to context
    context.actions.push(action);
    
    // Extract evidence from action
    const evidence = this.extractEvidence(action);
    context.evidence.push(...evidence);
    
    // If this action involves file creation, track it in the file registry
    if (action.content?.includes('Created file:') || action.content?.includes('written successfully')) {
      this.trackFileFromAction(action, taskId);
    }
    
    // Update file registry if files were created
    if (action.outputs.files) {
      action.outputs.files.forEach(file => {
        this.fileRegistry.addFile(file);
        context.files.push(file);
      });
    }
    
    // Update code documentation if code was created
    if (action.outputs.code) {
      this.codeDocumentation.addCode(action.outputs.code);
    }
    
    console.log(`[RichMemory] Added action to task ${taskId}: ${action.actionType}`);
    console.log(`[RichMemory] Evidence extracted: ${evidence.length} items`);
    
    // Check for completion
    this.checkRichCompletion(taskId);
  }

  setResult(taskId: string, result: string, resultType: string, filePath?: string): void {
    const context = this.taskContexts.get(taskId);
    if (!context) return;

    // Create result evidence
    const resultEvidence: Evidence = {
      evidenceId: this.generateEvidenceId(),
      evidenceType: 'synthesis',
      content: `Task result: ${result}`,
      confidence: 1.0,
      source: 'result_setter',
      timestamp: Date.now(),
      metadata: {
        wordCount: result.split(' ').length
      }
    };

    context.evidence.push(resultEvidence);
    
    // If file path provided, create file reference
    if (filePath) {
      const fileRef = this.fileRegistry.createFileReference(
        filePath,
        result,
        'output',
        'result_setter'
      );
      context.files.push(fileRef);
    }
    
    console.log(`[RichMemory] Set result for task ${taskId}: ${resultType}`);
    
    // Check for completion
    this.checkRichCompletion(taskId);
  }

  checkRichCompletion(taskId: string): boolean {
    const context = this.taskContexts.get(taskId);
    if (!context) return false;

    const isComplete = this.completionRules.checkCompletion(context);
    
    if (isComplete && !context.complete) {
      context.complete = true;
      console.log(`[RichMemory] Task ${taskId} marked as complete`);
      
      // Generate completion evidence
      const completionEvidence = this.generateCompletionEvidence(context);
      context.completionEvidence.push(completionEvidence);
    }
    
    return isComplete;
  }

  getTaskContext(taskId: string): RichTaskContext | undefined {
    return this.taskContexts.get(taskId);
  }

  getActionHistory(taskId: string): RichAction[] {
    const context = this.taskContexts.get(taskId);
    return context ? context.actions : [];
  }

  getResult(taskId: string): string | null {
    const context = this.taskContexts.get(taskId);
    if (!context) return null;
    
    // Find the most recent result
    const resultEvidence = context.evidence
      .filter(e => e.evidenceType === 'synthesis')
      .sort((a, b) => b.timestamp - a.timestamp)[0];
    
    return resultEvidence ? resultEvidence.content : null;
  }

  getRichResult(taskId: string): RichOutput | null {
    const context = this.taskContexts.get(taskId);
    if (!context) return null;
    
    const result = this.getResult(taskId);
    if (!result) return null;
    
    return {
      success: true,
      result,
      files: context.files,
      metadata: {
        executionTime: Date.now() - context.timestamp,
        tool: 'memory_manager',
        timestamp: Date.now()
      }
    };
  }

  getAllTasks(): RichTaskContext[] {
    return Array.from(this.taskContexts.values());
  }

  clearTask(taskId: string): void {
    const context = this.taskContexts.get(taskId);
    if (!context) return;
    
    // Clean up related data
    context.files.forEach(file => {
      this.fileRegistry.removeFile(file.fileId);
    });
    
    // Remove code documentation
    const codeRef = this.codeDocumentation.getCodeByFile(context.files[0]?.fileId || '');
    if (codeRef) {
      this.codeDocumentation.removeCode(codeRef.codeId);
    }
    
    // Clean up loop prevention
    this.loopPrevention.resetLoopCounters(taskId);
    
    this.taskContexts.delete(taskId);
    
    if (this.currentTaskId === taskId) {
      this.currentTaskId = null;
    }
    
    console.log(`[RichMemory] Cleared task context: ${taskId}`);
  }

  // Evidence extraction and management
  private extractEvidence(action: RichAction): Evidence[] {
    const evidence: Evidence[] = [];
    
    // File creation evidence
    if (action.actionType === 'write_file' && action.outputs.success) {
      const fileEvidence: Evidence = {
        evidenceId: this.generateEvidenceId(),
        evidenceType: 'file_creation',
        content: `File created: ${action.outputs.files?.[0]?.filePath || 'unknown'}`,
        confidence: 1.0,
        source: action.actionId,
        timestamp: action.timestamp,
        metadata: {
          fileType: action.outputs.files?.[0]?.fileType || 'output',
          fileSize: action.outputs.files?.[0]?.size || 0
        }
      };
      evidence.push(fileEvidence);
    }
    
    // Code implementation evidence
    if (action.outputs.code) {
      const codeEvidence: Evidence = {
        evidenceId: this.generateEvidenceId(),
        evidenceType: 'code_implementation',
        content: `Code implemented: ${action.outputs.code.language} with ${action.outputs.code.functions.length} functions`,
        confidence: 1.0,
        source: action.actionId,
        timestamp: action.timestamp,
        metadata: {
          language: action.outputs.code.language,
          functionCount: action.outputs.code.functions.length,
          complexity: action.outputs.code.complexity
        }
      };
      evidence.push(codeEvidence);
    }
    
    // Documentation evidence
    if (action.outputs.documentation) {
      const docEvidence: Evidence = {
        evidenceId: this.generateEvidenceId(),
        evidenceType: 'documentation',
        content: `Documentation created: ${action.outputs.documentation.title}`,
        confidence: 1.0,
        source: action.actionId,
        timestamp: action.timestamp,
        metadata: {
          docType: action.outputs.documentation.type,
          wordCount: action.outputs.documentation.wordCount
        }
      };
      evidence.push(docEvidence);
    }
    
    // Execution evidence
    if (action.success) {
      const execEvidence: Evidence = {
        evidenceId: this.generateEvidenceId(),
        evidenceType: 'execution',
        content: `Action executed successfully: ${action.actionType}`,
        confidence: 1.0,
        source: action.actionId,
        timestamp: action.timestamp,
        metadata: {
          confidence: 1.0
        }
      };
      evidence.push(execEvidence);
    }
    
    return evidence;
  }

  private generateCompletionEvidence(context: RichTaskContext): CompletionEvidence {
    const completionEvidence: CompletionEvidence = {
      evidenceId: this.generateEvidenceId(),
      evidenceType: 'synthesis',
      content: `Task completed: ${context.task}`,
      confidence: 1.0,
      source: 'completion_rules',
      timestamp: Date.now(),
      requirements: this.completionRules.getCompletionCriteria(context.taskType),
      validation: {
        validatorId: 'completion_rules',
        confidence: 1.0,
        rationale: 'Task completion criteria met',
        requirements: this.completionRules.getCompletionCriteria(context.taskType),
        timestamp: Date.now()
      }
    };
    
    return completionEvidence;
  }

  // Loop prevention integration
  detectLoop(taskId: string): boolean {
    const context = this.taskContexts.get(taskId);
    if (!context) return false;
    
    return this.loopPrevention.detectRichLoop(taskId, context);
  }

  getLoopReason(taskId: string): string | null {
    return this.loopPrevention.getLoopReason(taskId);
  }

  // Validation integration
  validateTask(taskId: string): RichValidationResult {
    const context = this.taskContexts.get(taskId);
    if (!context) {
      return {
        completed: false,
        confidence: 0,
        rationale: 'Task context not found',
        evidence: [],
        requirements: []
      };
    }
    
    const isComplete = this.completionRules.checkCompletion(context);
    const analysis = this.completionRules.getCompletionAnalysis(context);
    
    return {
      completed: isComplete,
      confidence: analysis.completionPercentage / 100,
      rationale: isComplete ? 
        'Task completion criteria met with rich evidence' : 
        'Task completion criteria not met',
      evidence: context.evidence,
      requirements: analysis.completedRequirements,
      missingRequirements: analysis.missingRequirements,
      suggestions: analysis.recommendations
    };
  }

  // Utility methods
  private estimateComplexity(task: string, taskType: TaskType): number {
    // Simple complexity estimation based on task type and content
    let complexity = 1;
    
    switch (taskType) {
      case 'simple_question':
        complexity = 1;
        break;
      case 'coding_task':
        complexity = 3;
        if (task.includes('algorithm') || task.includes('leetcode')) complexity = 4;
        break;
      case 'research_task':
        complexity = 2;
        if (task.includes('comprehensive') || task.includes('detailed')) complexity = 3;
        break;
      case 'general_task':
        complexity = 2;
        break;
    }
    
    // Adjust based on task length and keywords
    if (task.length > 100) complexity += 1;
    if (task.includes('complex') || task.includes('advanced')) complexity += 1;
    
    return Math.min(complexity, 5); // Cap at 5
  }

  private generateTaskId(): string {
    return `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateEvidenceId(): string {
    return `evidence_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // Query methods
  getTasksByType(taskType: TaskType): RichTaskContext[] {
    return this.getAllTasks().filter(task => task.taskType === taskType);
  }

  getCompletedTasks(): RichTaskContext[] {
    return this.getAllTasks().filter(task => task.complete);
  }

  getActiveTasks(): RichTaskContext[] {
    return this.getAllTasks().filter(task => !task.complete);
  }

  getTasksByCreator(createdBy: string): RichTaskContext[] {
    return this.getAllTasks().filter(task => task.metadata.createdBy === createdBy);
  }

  getRecentTasks(minutes: number = 60): RichTaskContext[] {
    const cutoff = Date.now() - (minutes * 60 * 1000);
    return this.getAllTasks().filter(task => task.timestamp > cutoff);
  }

  // Statistics and monitoring
  getStats(): {
    totalTasks: number;
    completedTasks: number;
    activeTasks: number;
    byType: Record<TaskType, number>;
    totalActions: number;
    totalEvidence: number;
    totalFiles: number;
    averageComplexity: number;
  } {
    const tasks = this.getAllTasks();
    const completed = tasks.filter(t => t.complete).length;
    const active = tasks.filter(t => !t.complete).length;
    
    const byType: Record<TaskType, number> = {} as any;
    tasks.forEach(task => {
      byType[task.taskType] = (byType[task.taskType] || 0) + 1;
    });
    
    const totalActions = tasks.reduce((sum, task) => sum + task.actions.length, 0);
    const totalEvidence = tasks.reduce((sum, task) => sum + task.evidence.length, 0);
    const totalFiles = tasks.reduce((sum, task) => sum + task.files.length, 0);
    const totalComplexity = tasks.reduce((sum, task) => sum + task.metadata.estimatedComplexity, 0);
    
    return {
      totalTasks: tasks.length,
      completedTasks: completed,
      activeTasks: active,
      byType,
      totalActions,
      totalEvidence,
      totalFiles,
      averageComplexity: tasks.length > 0 ? totalComplexity / tasks.length : 0
    };
  }

  // Cleanup methods
  cleanup(): void {
    this.taskContexts.clear();
    this.fileRegistry = new FileRegistry();
    this.codeDocumentation = new CodeDocumentation();
    this.loopPrevention.cleanup();
    this.currentTaskId = null;
  }

  cleanupOldTasks(maxAgeMinutes: number = 60): void {
    const cutoff = Date.now() - (maxAgeMinutes * 60 * 1000);
    const oldTasks = this.getAllTasks().filter(task => task.timestamp < cutoff);
    
    oldTasks.forEach(task => {
      this.clearTask(task.taskId);
    });
    
    console.log(`[RichMemory] Cleaned up ${oldTasks.length} old tasks`);
  }

  // Export/Import methods
  exportTask(taskId: string): string {
    const context = this.taskContexts.get(taskId);
    if (!context) throw new Error(`Task not found: ${taskId}`);
    
    return JSON.stringify(context, null, 2);
  }

  importTask(taskData: string): string {
    const context: RichTaskContext = JSON.parse(taskData);
    
    // Validate and regenerate IDs if needed
    if (this.taskContexts.has(context.taskId)) {
      context.taskId = this.generateTaskId();
    }
    
    this.taskContexts.set(context.taskId, context);
    return context.taskId;
  }

  // Compatibility methods for existing agent API
  async updateMemoryBank(data: any): Promise<void> {
    // Convert old memory bank format to new rich memory format
    if (data.task && data.taskType) {
      this.createTask(data.task, data.taskType);
    }
  }

  private captureFileContent(toolData: any, taskId: string): void {
    // Extract file path and content from tool data
    const filePath = toolData.filename || toolData.filePath;
    const fileContent = toolData.content;
    
    if (!filePath || !fileContent) return;
    
    // Create file reference with proper structure
    const fileRef: FileReference = {
      fileId: this.generateActionId(),
      filePath: filePath,
      fileType: this.detectFileType(filePath),
      content: fileContent,
      size: fileContent.length,
      createdBy: 'agent',
      checksum: this.generateChecksum(fileContent),
      metadata: {
        language: this.detectLanguage(filePath)
      },
      createdAt: Date.now(),
      modifiedAt: Date.now()
    };
    
    // Add to file registry
    this.fileRegistry.addFile(fileRef, taskId);
  }

  private trackFileFromAction(action: RichAction, taskId: string): void {
    // Extract file path and content from action
    const content = action.content || '';
    const filenameMatch = content.match(/Created file: (.*?) -/);
    const successMatch = content.match(/File '(.*?)' written successfully/);
    
    const filePath = filenameMatch?.[1] || successMatch?.[1];
    if (!filePath) return;
    
    // Extract file content from action inputs or outputs
    let fileContent = '';
    
    // First, try to get content from action inputs (tool parameters)
    if (action.inputs && typeof action.inputs === 'object') {
      const inputs = action.inputs as any;
      if (inputs.content) {
        fileContent = inputs.content;
      } else if (inputs.content && typeof inputs.content === 'string') {
        fileContent = inputs.content;
      }
    }
    
    // If no content found in inputs, try to extract from the execution context
    // This is a fallback for when the content is passed through the execution context
    if (!fileContent && action.content) {
      // Look for content in the action content that might contain the file content
      const contentMatch = action.content.match(/content: '(.*?)'/);
      if (contentMatch && contentMatch[1]) {
        fileContent = contentMatch[1];
      }
    }
    
    // If still no content, use the result as fallback (though it's usually just success message)
    if (!fileContent) {
      fileContent = action.outputs?.result || '';
    }
    
    // Create file reference with proper structure
    const fileRef: FileReference = {
      fileId: this.generateActionId(),
      filePath: filePath,
      fileType: this.detectFileType(filePath),
      content: fileContent,
      size: fileContent.length,
      createdBy: 'agent',
      checksum: this.generateChecksum(fileContent),
      metadata: {
        language: this.detectLanguage(filePath)
      },
      createdAt: Date.now(),
      modifiedAt: Date.now()
    };
    
    // Add to file registry
    this.fileRegistry.addFile(fileRef, taskId);
  }

  private generateChecksum(content: string): string {
    const crypto = require('crypto');
    return crypto.createHash('md5').update(content).digest('hex');
  }

  private detectFileType(filePath: string): any {
    const ext = filePath.split('.').pop()?.toLowerCase();
    if (['py', 'js', 'ts', 'java', 'cpp', 'go', 'rs'].includes(ext || '')) return 'code';
    if (['md', 'txt', 'rst'].includes(ext || '')) return 'documentation';
    if (['json', 'xml', 'yaml', 'yml'].includes(ext || '')) return 'data';
    if (['conf', 'config', 'ini'].includes(ext || '')) return 'config';
    return 'output';
  }

  private detectLanguage(filePath: string): any {
    const ext = filePath.split('.').pop()?.toLowerCase();
    const langMap: { [key: string]: string } = {
      'py': 'python',
      'js': 'javascript',
      'ts': 'typescript',
      'java': 'java',
      'cpp': 'cpp',
      'go': 'go',
      'rs': 'rust'
    };
    return langMap[ext || ''] || 'other';
  }

  private createCompatibilityAction(type: string, content: string, additionalData: any = {}): RichAction {
    return {
      actionId: this.generateActionId(),
      actionType: type,
      inputs: {},
      outputs: {
        success: true,
        result: content,
        metadata: {
          executionTime: additionalData.executionTime || 0,
          tool: additionalData.tools?.[0] || 'unknown',
          timestamp: Date.now()
        }
      },
      evidence: [],
      timestamp: Date.now(),
      success: true,
      context: {
        taskId: this.currentTaskId || '',
        agentId: 'compatibility',
        sessionId: 'compatibility'
      },
      // Compatibility properties
      type,
      content,
      reasoning: additionalData.reasoning,
      confidence: additionalData.confidence,
      alternatives: additionalData.alternatives,
      tools: additionalData.tools,
      executionTime: additionalData.executionTime
    };
  }

  async logDecision(decision: string, reasoning: string, _iteration: number, confidence: number, alternatives: string[]): Promise<void> {
    if (!this.currentTaskId) return;
    
    const action = this.createCompatibilityAction('decision', decision, {
      reasoning,
      confidence,
      alternatives
    });
    this.addAction(this.currentTaskId, action);
  }

  async updateActiveContext(_task: string, _iteration: number, tools: string[], confidence: number, executionTime: number, description: string): Promise<void> {
    if (!this.currentTaskId) return;
    
    const action = this.createCompatibilityAction('execution', description, {
      tools,
      confidence,
      executionTime
    });
    this.addAction(this.currentTaskId, action);
  }

  async logError(error: string, context: string, _iteration: number, tools: string[]): Promise<void> {
    if (!this.currentTaskId) return;
    
    const action = this.createCompatibilityAction('error', error, {
      reasoning: context,
      tools
    });
    this.addAction(this.currentTaskId, action);
  }

  async logSuccessPattern(pattern: string, tools: string[], confidence: number, executionTime: number, toolData?: any): Promise<void> {
    if (!this.currentTaskId) return;
    
    const action = this.createCompatibilityAction('success', pattern, {
      tools,
      confidence,
      executionTime,
      toolData
    });
    this.addAction(this.currentTaskId, action);
    
    // If this is a write_file tool execution, capture the file content
    if (tools.includes('write_file') && toolData && toolData.content) {
      this.captureFileContent(toolData, this.currentTaskId);
    }
  }

  getCurrentTaskContext(): RichTaskContext | undefined {
    if (!this.currentTaskId) return undefined;
    return this.taskContexts.get(this.currentTaskId);
  }

  startTaskContext(task: string): RichTaskContext {
    const taskType = this.detectTaskType(task);
    const taskId = this.createTask(task, taskType);
    this.currentTaskId = taskId;
    return this.taskContexts.get(taskId)!;
  }

  completeTask(status: string): void {
    if (!this.currentTaskId) return;
    
    const context = this.taskContexts.get(this.currentTaskId);
    if (context) {
      context.complete = status === 'completed';
      this.taskContexts.set(this.currentTaskId, context);
    }
  }

  recordValidation(confidence: number): void {
    if (!this.currentTaskId) return;
    
    const context = this.taskContexts.get(this.currentTaskId);
    if (context) {
      if (!context.confidenceHistory) {
        context.confidenceHistory = [];
      }
      context.confidenceHistory.push(confidence);
      this.taskContexts.set(this.currentTaskId, context);
    }
  }

  addEntry(entry: any): void {
    if (!this.currentTaskId) return;
    
    const action = this.createCompatibilityAction('entry', entry.content || entry.thought || entry.step || '', {
      reasoning: entry.observation || '',
      confidence: entry.confidence || 0.5
    });
    this.addAction(this.currentTaskId, action);
  }

  queryMemories(_query: any): any[] {
    if (!this.currentTaskId) return [];
    
    const context = this.taskContexts.get(this.currentTaskId);
    if (!context) return [];
    
    // Convert rich memory actions to old format
    return context.actions.map(action => ({
      content: action.content || action.outputs.result,
      metadata: {
        type: action.type || action.actionType,
        confidence: action.confidence || 0.5,
        timestamp: action.timestamp
      }
    }));
  }

  getTaskCompletionProof(): any {
    if (!this.currentTaskId) return null;
    
    const context = this.taskContexts.get(this.currentTaskId);
    if (!context) return null;
    
    // Get actual files created during this task
    const createdFiles = this.fileRegistry.getFilesByTask(this.currentTaskId);
    
    // Analyze file content to determine evidence types
    const fileCreationEntries = createdFiles.map(file => ({
      filePath: file.filePath,
      filename: file.filePath.split('/').pop() || file.filePath, // Extract just filename for compatibility
      content: file.content,
      metadata: file.metadata
    }));
    
    // Check for synthesis evidence by examining file content
    const synthesisEntries = createdFiles.filter(file => {
      const content = file.content?.toLowerCase() || '';
      const filename = file.filePath?.toLowerCase() || '';
      
      // Look for synthesis indicators in content
      return content.includes('answer') ||
             content.includes('summary') ||
             content.includes('solution') ||
             content.includes('explanation') ||
             filename.includes('answer') ||
             filename.includes('summary') ||
             filename.includes('solution') ||
             filename.endsWith('.md');
    });
    
    // Check for implementation evidence by examining file content
    const implementationEntries = createdFiles.filter(file => {
      const content = file.content || '';
      const filename = file.filePath?.toLowerCase() || '';
      
      // Look for code implementation indicators
      return content.includes('def ') ||
             content.includes('function ') ||
             content.includes('class ') ||
             content.includes('import ') ||
             content.includes('return ') ||
             filename.endsWith('.py') ||
             filename.endsWith('.js') ||
             filename.endsWith('.ts') ||
             filename.endsWith('.java') ||
             filename.endsWith('.cpp');
    });
    
    const completionEntries = context.completionEvidence;
    
    return {
      taskId: context.taskId,
      complete: context.complete,
      evidence: context.completionEvidence,
      actions: context.actions.length,
      // Direct file access for validator
      hasFileCreation: fileCreationEntries.length > 0,
      fileCreationEntries: fileCreationEntries,
      hasSynthesis: synthesisEntries.length > 0,
      synthesisEntries: synthesisEntries,
      hasImplementation: implementationEntries.length > 0,
      implementationEntries: implementationEntries,
      completionEntries: completionEntries,
      // Additional context for validator
      createdFiles: createdFiles,
      totalFiles: createdFiles.length
    };
  }

  getBFSContext(_task: string, limit: number): string {
    if (!this.currentTaskId) return '';
    
    const context = this.taskContexts.get(this.currentTaskId);
    if (!context) return '';
    
    // Generate context from actions and evidence
    const actions = context.actions.slice(-limit);
    const evidence = context.evidence.slice(-limit);
    
    let contextStr = `Task: ${context.task}\n`;
    contextStr += `Type: ${context.taskType}\n`;
    contextStr += `Actions: ${actions.map(a => a.content || a.outputs.result).join(', ')}\n`;
    contextStr += `Evidence: ${evidence.map(e => e.description || e.content).join(', ')}\n`;
    
    return contextStr;
  }


  // Additional compatibility methods for longTermMemory
  async learnFromTask(task: string, result: string, success: boolean, executionTime: number): Promise<void> {
    if (!this.currentTaskId) return;
    
    const action = this.createCompatibilityAction('learning', `Task: ${task}, Result: ${result}`, {
      reasoning: success ? 'successful' : 'failed',
      confidence: success ? 1.0 : 0.0,
      executionTime
    });
    this.addAction(this.currentTaskId, action);
  }

  async generateMemoryContext(_task: string, maxTokens: number): Promise<string> {
    if (!this.currentTaskId) return '';
    
    const context = this.taskContexts.get(this.currentTaskId);
    if (!context) return '';
    
    // Generate context from recent actions
    const recentActions = context.actions.slice(-10);
    let contextStr = `Task: ${context.task}\n`;
    contextStr += `Recent Actions:\n`;
    
    for (const action of recentActions) {
      contextStr += `- ${action.type || action.actionType}: ${action.content || action.outputs.result}\n`;
    }
    
    // Truncate if too long
    if (contextStr.length > maxTokens) {
      contextStr = contextStr.substring(0, maxTokens) + '...';
    }
    
    return contextStr;
  }

  private detectTaskType(task: string): TaskType {
    const lowerTask = task.toLowerCase();
    
    if (lowerTask.includes('?') && (lowerTask.includes('what') || lowerTask.includes('how') || lowerTask.includes('why'))) {
      return 'simple_question';
    } else if (lowerTask.includes('implement') || lowerTask.includes('create') || lowerTask.includes('write') || lowerTask.includes('code')) {
      return 'coding_task';
    } else if (lowerTask.includes('research') || lowerTask.includes('find') || lowerTask.includes('analyze')) {
      return 'research_task';
    } else {
      return 'general_task';
    }
  }

  private generateActionId(): string {
    return `action_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}
