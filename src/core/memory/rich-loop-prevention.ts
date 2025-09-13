/**
 * Rich Loop Prevention System
 * 
 * Detects and prevents infinite loops in task execution using rich context
 * and evidence-based analysis. Provides intelligent loop detection with
 * context-aware limits and pattern recognition.
 */

import { 
  RichTaskContext, 
  RichAction, 
  ILoopPrevention,
  EvidenceType
} from './rich-memory-types';

export class RichLoopPrevention implements ILoopPrevention {
  private maxIterations: number = 40;
  private maxDuplicateActions: number = 3;
  private maxValidationActions: number = 5;
  private maxEvidenceStagnationMinutes: number = 2;
  private maxActionStagnationMinutes: number = 5;
  
  // Track loop patterns per task
  private loopCounters: Map<string, {
    duplicateActions: Map<string, number>;
    validationCount: number;
    lastEvidenceTime: number;
    lastActionTime: number;
    stagnationCount: number;
  }> = new Map();

  detectRichLoop(taskId: string, context?: RichTaskContext): boolean {
    if (!context) return false;
    // Initialize counters if not exists
    if (!this.loopCounters.has(taskId)) {
      this.loopCounters.set(taskId, {
        duplicateActions: new Map(),
        validationCount: 0,
        lastEvidenceTime: Date.now(),
        lastActionTime: Date.now(),
        stagnationCount: 0
      });
    }

    const counters = this.loopCounters.get(taskId)!;
    
    // Check for too many iterations
    if (context.actions.length >= this.maxIterations) {
      console.warn(`[LoopPrevention] Max iterations reached for task ${taskId}`);
      return true;
    }
    
    // Check for duplicate actions
    if (this.detectDuplicateActions(context.actions, counters)) {
      console.warn(`[LoopPrevention] Too many duplicate actions for task ${taskId}`);
      return true;
    }
    
    // Check for validation loops
    if (this.detectValidationLoops(context.actions, counters)) {
      console.warn(`[LoopPrevention] Too many validation actions for task ${taskId}`);
      return true;
    }
    
    // Check for evidence stagnation
    if (this.detectEvidenceStagnation(context, counters)) {
      console.warn(`[LoopPrevention] Evidence stagnation detected for task ${taskId}`);
      return true;
    }
    
    // Check for action stagnation
    if (this.detectActionStagnation(context, counters)) {
      console.warn(`[LoopPrevention] Action stagnation detected for task ${taskId}`);
      return true;
    }
    
    // Check for circular dependencies
    if (this.detectCircularDependencies(context)) {
      console.warn(`[LoopPrevention] Circular dependencies detected for task ${taskId}`);
      return true;
    }
    
    // Check for repetitive patterns
    if (this.detectRepetitivePatterns(context)) {
      console.warn(`[LoopPrevention] Repetitive patterns detected for task ${taskId}`);
      return true;
    }
    
    return false;
  }

  getLoopReason(taskId: string): string | null {
    const counters = this.loopCounters.get(taskId);
    if (!counters) return null;
    
    // Check which condition triggered the loop
    if (counters.duplicateActions.size > 0) {
      const duplicateValues = Array.from(counters.duplicateActions.values());
      if (duplicateValues.length > 0) {
        const maxDuplicates = Math.max(...duplicateValues);
        if (maxDuplicates >= this.maxDuplicateActions) {
          return `Too many duplicate actions (${maxDuplicates} duplicates)`;
        }
      }
    }
    
    if (counters.validationCount >= this.maxValidationActions) {
      return `Too many validation actions (${counters.validationCount} validations)`;
    }
    
    const evidenceStagnation = Date.now() - counters.lastEvidenceTime;
    if (evidenceStagnation > this.maxEvidenceStagnationMinutes * 60 * 1000) {
      return `Evidence stagnation (${Math.round(evidenceStagnation / 1000)}s without new evidence)`;
    }
    
    const actionStagnation = Date.now() - counters.lastActionTime;
    if (actionStagnation > this.maxActionStagnationMinutes * 60 * 1000) {
      return `Action stagnation (${Math.round(actionStagnation / 1000)}s without new actions)`;
    }
    
    return 'Unknown loop condition';
  }

  resetLoopCounters(taskId: string): void {
    this.loopCounters.delete(taskId);
  }

  private detectDuplicateActions(actions: RichAction[], counters: any): boolean {
    // Update duplicate action counters
    actions.forEach(action => {
      const actionKey = this.getActionKey(action);
      const currentCount = counters.duplicateActions.get(actionKey) || 0;
      counters.duplicateActions.set(actionKey, currentCount + 1);
    });
    
    // Check if any action has too many duplicates
    const duplicateValues = Array.from(counters.duplicateActions.values());
    if (duplicateValues.length === 0) return false;
    const maxDuplicates = Math.max(...duplicateValues.map(v => Number(v)));
    return maxDuplicates >= this.maxDuplicateActions;
  }

  private detectValidationLoops(actions: RichAction[], counters: any): boolean {
    // Count validation actions
    const validationActions = actions.filter(action => action.actionType === 'validate');
    counters.validationCount = validationActions.length;
    
    return counters.validationCount >= this.maxValidationActions;
  }

  private detectEvidenceStagnation(context: RichTaskContext, counters: any): boolean {
    // Check if we have recent evidence
    const recentEvidence = context.evidence.filter(e => 
      Date.now() - e.timestamp < this.maxEvidenceStagnationMinutes * 60 * 1000
    );
    
    if (recentEvidence.length === 0 && context.actions.length > 3) {
      // No recent evidence and we have some actions
      counters.stagnationCount++;
      return counters.stagnationCount >= 2; // Allow 2 periods of stagnation
    } else if (recentEvidence.length > 0) {
      // Reset stagnation counter if we have recent evidence
      counters.stagnationCount = 0;
      counters.lastEvidenceTime = Date.now();
    }
    
    return false;
  }

  private detectActionStagnation(context: RichTaskContext, counters: any): boolean {
    // Check if we have recent actions
    const recentActions = context.actions.filter(action => 
      Date.now() - action.timestamp < this.maxActionStagnationMinutes * 60 * 1000
    );
    
    if (recentActions.length === 0 && context.actions.length > 0) {
      // No recent actions but we have some actions
      const timeSinceLastAction = Date.now() - counters.lastActionTime;
      return timeSinceLastAction > this.maxActionStagnationMinutes * 60 * 1000;
    } else if (recentActions.length > 0) {
      // Update last action time
      counters.lastActionTime = Date.now();
    }
    
    return false;
  }

  private detectCircularDependencies(context: RichTaskContext): boolean {
    // Check for circular file dependencies
    const fileDependencies = this.extractFileDependencies(context);
    return this.hasCircularDependency(fileDependencies);
  }

  private detectRepetitivePatterns(context: RichTaskContext): boolean {
    // Check for repetitive action patterns
    const actionPatterns = this.extractActionPatterns(context.actions);
    return this.hasRepetitivePattern(actionPatterns);
  }

  private getActionKey(action: RichAction): string {
    // Create a unique key for the action based on type and inputs
    const inputKey = JSON.stringify(action.inputs);
    return `${action.actionType}:${inputKey}`;
  }

  private extractFileDependencies(context: RichTaskContext): Map<string, string[]> {
    const dependencies = new Map<string, string[]>();
    
    context.actions.forEach(action => {
      if (action.actionType === 'read_file' && (action.inputs as any).filename) {
        const filename = (action.inputs as any).filename as string;
        if (!dependencies.has(filename)) {
          dependencies.set(filename, []);
        }
      }
      
      if (action.actionType === 'write_file' && (action.inputs as any).filename) {
        const filename = (action.inputs as any).filename as string;
        // Check if this file was read before
        const readActions = context.actions.filter(a => 
          a.actionType === 'read_file' && 
          (a.inputs as any).filename === filename &&
          a.timestamp < action.timestamp
        );
        
        if (readActions.length > 0) {
          if (!dependencies.has(filename)) {
            dependencies.set(filename, []);
          }
          const deps = dependencies.get(filename);
          if (deps) {
            deps.push(filename); // Self-dependency
          }
        }
      }
    });
    
    return dependencies;
  }

  private hasCircularDependency(dependencies: Map<string, string[]>): boolean {
    // Simple circular dependency detection
    for (const [file, deps] of Array.from(dependencies.entries())) {
      if (deps && deps.includes(file)) {
        return true;
      }
    }
    return false;
  }

  private extractActionPatterns(actions: RichAction[]): string[] {
    // Extract patterns of consecutive actions
    const patterns: string[] = [];
    
    for (let i = 0; i < actions.length - 2; i++) {
      const action1 = actions[i];
      const action2 = actions[i + 1];
      const action3 = actions[i + 2];
      
      if (action1 && action2 && action3) {
        const pattern = [
          action1.actionType,
          action2.actionType,
          action3.actionType
        ].join(' -> ');
        patterns.push(pattern);
      }
    }
    
    return patterns;
  }

  private hasRepetitivePattern(patterns: string[]): boolean {
    // Check if the same pattern repeats too many times
    const patternCounts = new Map<string, number>();
    
    patterns.forEach(pattern => {
      const count = patternCounts.get(pattern) || 0;
      patternCounts.set(pattern, count + 1);
    });
    
    // If any pattern appears more than 3 times, it's repetitive
    const counts = Array.from(patternCounts.values());
    if (counts.length === 0) return false;
    const maxCount = Math.max(...counts);
    return maxCount >= 3;
  }

  // Advanced loop detection methods
  detectEvidenceBasedLoop(context: RichTaskContext): boolean {
    // Check if evidence is not progressing
    const evidenceTypes = new Set<EvidenceType>();
    context.evidence.forEach(e => evidenceTypes.add(e.evidenceType));
    
    // If we have many actions but few evidence types, it might be a loop
    if (context.actions.length > 10 && evidenceTypes.size < 2) {
      return true;
    }
    
    // Check for evidence regression
    const evidenceByTime = context.evidence.sort((a, b) => a.timestamp - b.timestamp);
    let lastEvidenceCount = 0;
    
    for (let i = 0; i < evidenceByTime.length; i++) {
      const currentCount = i + 1;
      if (currentCount < lastEvidenceCount) {
        return true; // Evidence count decreased
      }
      lastEvidenceCount = currentCount;
    }
    
    return false;
  }

  detectContextBasedLoop(context: RichTaskContext): boolean {
    // Check if task context is not evolving
    const recentActions = context.actions.slice(-5); // Last 5 actions
    const actionTypes = new Set(recentActions.map(a => a.actionType));
    
    // If all recent actions are the same type, it might be a loop
    if (actionTypes.size === 1 && recentActions.length >= 3) {
      return true;
    }
    
    // Check if we're not making progress on the task
    const hasProgressEvidence = context.evidence.some(e => 
      e.evidenceType === 'file_creation' || 
      e.evidenceType === 'code_implementation' ||
      e.evidenceType === 'synthesis'
    );
    
    if (context.actions.length > 8 && !hasProgressEvidence) {
      return true;
    }
    
    return false;
  }

  // Configuration methods
  setMaxIterations(max: number): void {
    this.maxIterations = max;
  }

  setMaxDuplicateActions(max: number): void {
    this.maxDuplicateActions = max;
  }

  setMaxValidationActions(max: number): void {
    this.maxValidationActions = max;
  }

  setMaxEvidenceStagnationMinutes(minutes: number): void {
    this.maxEvidenceStagnationMinutes = minutes;
  }

  setMaxActionStagnationMinutes(minutes: number): void {
    this.maxActionStagnationMinutes = minutes;
  }

  // Statistics and monitoring
  getLoopStatistics(taskId: string): {
    totalActions: number;
    duplicateActions: number;
    validationActions: number;
    evidenceCount: number;
    stagnationPeriods: number;
    lastActivity: number;
  } | null {
    const counters = this.loopCounters.get(taskId);
    if (!counters) return null;
    
    const duplicateValues = Array.from(counters.duplicateActions.values());
    return {
      totalActions: counters.duplicateActions.size,
      duplicateActions: duplicateValues.length > 0 ? Math.max(...duplicateValues.map(v => Number(v))) : 0,
      validationActions: counters.validationCount,
      evidenceCount: 0, // Would need context to calculate
      stagnationPeriods: counters.stagnationCount,
      lastActivity: Math.max(counters.lastEvidenceTime, counters.lastActionTime)
    };
  }

  // Cleanup methods
  cleanup(): void {
    this.loopCounters.clear();
  }

  cleanupOldTasks(maxAgeMinutes: number = 60): void {
    const cutoff = Date.now() - (maxAgeMinutes * 60 * 1000);
    
    for (const [taskId, counters] of Array.from(this.loopCounters.entries())) {
      const lastActivity = Math.max(counters.lastEvidenceTime, counters.lastActionTime);
      if (lastActivity < cutoff) {
        this.loopCounters.delete(taskId);
      }
    }
  }
}
