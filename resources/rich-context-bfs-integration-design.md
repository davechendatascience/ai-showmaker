# Rich Context Memory System with BFS Integration

## Design Philosophy

**Rich Context Requirements:**
- Code solutions must include file paths and documentation
- File operations must be tracked with metadata
- Context must be queryable and searchable
- Task-based isolation with rich cross-references
- Evidence-based completion validation

**BFS Integration Requirements:**
- Memory system as single source of truth
- Rich context for plan generation
- Loop prevention with context awareness
- Validation based on rich evidence
- Task isolation without losing context richness

## Integrated Architecture

```mermaid
graph TD
    A[User Query] --> B[BFS Agent]
    B --> C[Task Type Detection]
    C --> D[Rich Memory Manager]
    D --> E[Initialize Task Context]
    E --> F[Generate Context-Aware Plans]
    F --> G[Execute Plan with Rich Tracking]
    G --> H[Update Rich Memory]
    H --> I[Check Rich Completion]
    I --> J{Task Complete?}
    J -->|No| K[Generate Next Plans]
    K --> G
    J -->|Yes| L[Return Rich Result]
    
    M[Validator Agent] --> N[Query Rich Context]
    N --> O[Evidence-Based Validation]
    O --> P[Rich Validation Result]
    P --> Q[Update Memory with Feedback]
    Q --> B
    
    R[Rich Memory System] --> S[Task Context Store]
    R --> T[Action Evidence Log]
    R --> U[File Registry]
    R --> V[Code Documentation]
    R --> W[Completion Evidence]
    
    S --> S1[taskId: string]
    S --> S2[taskType: string]
    S --> S3[actions: RichAction[]]
    S --> S4[evidence: Evidence[]]
    S --> S5[files: FileReference[]]
    S --> S6[complete: boolean]
    
    T --> T1[actionId: string]
    T --> T2[actionType: string]
    T --> T3[inputs: object]
    T --> T4[outputs: RichOutput]
    T --> T5[evidence: Evidence[]]
    T --> T6[timestamp: number]
    
    U --> U1[fileId: string]
    U --> U2[filePath: string]
    U --> U3[fileType: string]
    U --> U4[content: string]
    U --> U5[metadata: FileMetadata]
    U --> U6[createdBy: string]
    
    V --> V1[codeId: string]
    V --> V2[fileId: string]
    V --> V3[language: string]
    V --> V4[functions: FunctionDoc[]]
    V --> V5[classes: ClassDoc[]]
    V --> V6[documentation: string]
    
    W --> W1[evidenceId: string]
    W --> W2[evidenceType: string]
    W --> W3[content: string]
    W --> W4[confidence: number]
    W --> W5[source: string]
    W --> W6[timestamp: number]
    
    X[Loop Prevention] --> Y[Action Pattern Detection]
    X --> Z[Evidence-Based Loop Detection]
    X --> AA[Context-Aware Limits]
    X --> BB[Rich Validation Limits]
    
    style A fill:#e1f5fe
    style L fill:#c8e6c9
    style R fill:#fff3e0
    style M fill:#ffebee
    style X fill:#f3e5f5
```

## Core Data Structures

### 1. Rich Task Context
```typescript
interface RichTaskContext {
  taskId: string;
  taskType: 'simple_question' | 'coding_task' | 'research_task' | 'general_task';
  task: string;
  actions: RichAction[];
  evidence: Evidence[];
  files: FileReference[];
  complete: boolean;
  completionEvidence: CompletionEvidence[];
  timestamp: number;
  metadata: TaskMetadata;
}

interface RichAction {
  actionId: string;
  actionType: string;
  inputs: object;
  outputs: RichOutput;
  evidence: Evidence[];
  timestamp: number;
  success: boolean;
  context: ActionContext;
}

interface RichOutput {
  success: boolean;
  result: string;
  files?: FileReference[];
  code?: CodeReference;
  documentation?: DocumentationReference;
  metadata: OutputMetadata;
}

interface Evidence {
  evidenceId: string;
  evidenceType: 'file_creation' | 'code_implementation' | 'documentation' | 'synthesis' | 'execution' | 'validation';
  content: string;
  confidence: number;
  source: string; // actionId or validationId
  timestamp: number;
  metadata: EvidenceMetadata;
}
```

### 2. File Registry
```typescript
interface FileRegistry {
  [fileId: string]: FileReference;
}

interface FileReference {
  fileId: string;
  filePath: string;
  fileType: 'code' | 'documentation' | 'data' | 'config' | 'output';
  content: string;
  size: number;
  createdBy: string; // actionId
  createdAt: number;
  modifiedAt: number;
  metadata: FileMetadata;
  checksum: string;
}

interface FileMetadata {
  language?: string;
  functions?: string[];
  classes?: string[];
  imports?: string[];
  dependencies?: string[];
  purpose?: string;
  documentation?: string;
}
```

### 3. Code Documentation
```typescript
interface CodeDocumentation {
  [codeId: string]: CodeReference;
}

interface CodeReference {
  codeId: string;
  fileId: string;
  language: string;
  functions: FunctionDocumentation[];
  classes: ClassDocumentation[];
  imports: ImportReference[];
  dependencies: DependencyReference[];
  documentation: string;
  complexity: number;
  testCoverage?: number;
}

interface FunctionDocumentation {
  name: string;
  parameters: ParameterDocumentation[];
  returnType: string;
  description: string;
  examples: string[];
  complexity: number;
  lineStart: number;
  lineEnd: number;
}

interface ClassDocumentation {
  name: string;
  methods: MethodDocumentation[];
  properties: PropertyDocumentation[];
  description: string;
  inheritance?: string[];
  lineStart: number;
  lineEnd: number;
}
```

### 4. Completion Evidence
```typescript
interface CompletionEvidence {
  evidenceId: string;
  evidenceType: 'file_creation' | 'code_implementation' | 'documentation' | 'synthesis' | 'execution_success';
  content: string;
  confidence: number;
  source: string;
  timestamp: number;
  requirements: string[];
  validation: ValidationEvidence;
}

interface ValidationEvidence {
  validatorId: string;
  confidence: number;
  rationale: string;
  requirements: string[];
  timestamp: number;
}
```

## Rich Memory Manager

### 1. Core Memory Manager
```typescript
class RichMemoryManager {
  private taskContexts: Map<string, RichTaskContext> = new Map();
  private fileRegistry: FileRegistry = {};
  private codeDocumentation: CodeDocumentation = {};
  private evidenceStore: Map<string, Evidence[]> = new Map();
  private completionRules: RichCompletionRules;
  
  createTask(task: string, taskType: string): string {
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
        estimatedComplexity: this.estimateComplexity(task, taskType)
      }
    };
    
    this.taskContexts.set(taskId, context);
    return taskId;
  }
  
  addAction(taskId: string, action: RichAction): void {
    const context = this.taskContexts.get(taskId);
    if (!context) return;
    
    context.actions.push(action);
    
    // Extract evidence from action
    const evidence = this.extractEvidence(action);
    context.evidence.push(...evidence);
    this.evidenceStore.set(taskId, context.evidence);
    
    // Update file registry if files were created
    if (action.outputs.files) {
      action.outputs.files.forEach(file => {
        this.fileRegistry[file.fileId] = file;
        context.files.push(file);
      });
    }
    
    // Update code documentation if code was created
    if (action.outputs.code) {
      this.codeDocumentation[action.outputs.code.codeId] = action.outputs.code;
    }
    
    // Check for completion
    this.checkRichCompletion(taskId);
  }
  
  private extractEvidence(action: RichAction): Evidence[] {
    const evidence: Evidence[] = [];
    
    // File creation evidence
    if (action.actionType === 'write_file' && action.outputs.success) {
      evidence.push({
        evidenceId: this.generateEvidenceId(),
        evidenceType: 'file_creation',
        content: `File created: ${action.outputs.files?.[0]?.filePath}`,
        confidence: 1.0,
        source: action.actionId,
        timestamp: action.timestamp,
        metadata: {
          fileType: action.outputs.files?.[0]?.fileType,
          fileSize: action.outputs.files?.[0]?.size
        }
      });
    }
    
    // Code implementation evidence
    if (action.outputs.code) {
      evidence.push({
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
      });
    }
    
    // Documentation evidence
    if (action.outputs.documentation) {
      evidence.push({
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
      });
    }
    
    return evidence;
  }
}
```

### 2. Rich Completion Rules
```typescript
class RichCompletionRules {
  checkCompletion(context: RichTaskContext): boolean {
    switch (context.taskType) {
      case 'simple_question':
        return this.checkSimpleQuestionCompletion(context);
      case 'coding_task':
        return this.checkCodingTaskCompletion(context);
      case 'research_task':
        return this.checkResearchTaskCompletion(context);
      case 'general_task':
        return this.checkGeneralTaskCompletion(context);
      default:
        return false;
    }
  }
  
  private checkSimpleQuestionCompletion(context: RichTaskContext): boolean {
    // Simple question requires answer with evidence
    const hasAnswer = context.evidence.some(e => 
      e.evidenceType === 'synthesis' || 
      e.evidenceType === 'file_creation'
    );
    
    const hasResult = context.actions.some(action => 
      action.actionType === 'write_file' && 
      action.outputs.success
    );
    
    return hasAnswer && hasResult;
  }
  
  private checkCodingTaskCompletion(context: RichTaskContext): boolean {
    // Coding task requires code file with documentation
    const hasCodeFile = context.evidence.some(e => 
      e.evidenceType === 'file_creation' && 
      e.metadata?.fileType === 'code'
    );
    
    const hasCodeImplementation = context.evidence.some(e => 
      e.evidenceType === 'code_implementation'
    );
    
    const hasDocumentation = context.evidence.some(e => 
      e.evidenceType === 'documentation'
    );
    
    // Check if code file is properly documented
    const codeFiles = context.files.filter(f => f.fileType === 'code');
    const documentedFiles = codeFiles.filter(f => 
      f.metadata?.documentation && f.metadata.documentation.length > 50
    );
    
    return hasCodeFile && hasCodeImplementation && 
           (hasDocumentation || documentedFiles.length > 0);
  }
  
  private checkResearchTaskCompletion(context: RichTaskContext): boolean {
    // Research task requires summary with sources
    const hasSummary = context.evidence.some(e => 
      e.evidenceType === 'synthesis' || 
      e.evidenceType === 'documentation'
    );
    
    const hasSources = context.evidence.some(e => 
      e.evidenceType === 'file_creation' && 
      e.metadata?.fileType === 'documentation'
    );
    
    return hasSummary && hasSources;
  }
  
  private checkGeneralTaskCompletion(context: RichTaskContext): boolean {
    // General task requires result with evidence
    const hasResult = context.actions.some(action => 
      action.actionType === 'write_file' && 
      action.outputs.success
    );
    
    const hasEvidence = context.evidence.length > 0;
    
    return hasResult && hasEvidence;
  }
}
```

## BFS Integration with Rich Context

### 1. BFS Agent with Rich Memory
```typescript
class BFSAgentWithRichMemory {
  private memoryManager: RichMemoryManager;
  private taskTypeDetector: TaskTypeDetector;
  private loopPrevention: RichLoopPrevention;
  private planGenerator: RichPlanGenerator;
  
  async executeTask(task: string): Promise<string> {
    // 1. Detect task type
    const taskType = this.taskTypeDetector.detectTaskType(task);
    
    // 2. Initialize rich memory context
    const taskId = this.memoryManager.createTask(task, taskType);
    
    // 3. BFS loop with rich context
    let iteration = 0;
    const maxIterations = 40;
    
    while (iteration < maxIterations) {
      // Check for completion with rich evidence
      if (this.memoryManager.checkRichCompletion(taskId)) {
        return this.memoryManager.getRichResult(taskId);
      }
      
      // Check for loops with rich context
      if (this.loopPrevention.detectRichLoop(taskId)) {
        console.warn(`Rich loop detected for task ${taskId}`);
        break;
      }
      
      // Generate context-aware plans
      const plans = await this.planGenerator.generateRichPlans(task, taskId, taskType);
      
      // Execute best plan with rich tracking
      const result = await this.executeRichPlan(plans[0], taskId);
      
      // Update rich memory
      this.memoryManager.addAction(taskId, result);
      
      iteration++;
    }
    
    return this.memoryManager.getRichResult(taskId) || "Task incomplete";
  }
  
  private async executeRichPlan(plan: RichPlanNode, taskId: string): Promise<RichAction> {
    const startTime = Date.now();
    
    try {
      // Execute the plan
      const result = await this.execute(plan.tool, plan.inputs);
      
      // Create rich output with evidence
      const richOutput: RichOutput = {
        success: result.success,
        result: result.text,
        metadata: {
          executionTime: Date.now() - startTime,
          tool: plan.tool,
          timestamp: Date.now()
        }
      };
      
      // Extract files if created
      if (plan.tool === 'write_file' && result.success) {
        const fileRef = await this.createFileReference(plan.inputs, result);
        richOutput.files = [fileRef];
        
        // Extract code documentation if it's a code file
        if (this.isCodeFile(plan.inputs.filename)) {
          const codeRef = await this.extractCodeDocumentation(fileRef);
          richOutput.code = codeRef;
        }
      }
      
      // Create rich action
      const richAction: RichAction = {
        actionId: this.generateActionId(),
        actionType: plan.tool,
        inputs: plan.inputs,
        outputs: richOutput,
        evidence: [],
        timestamp: Date.now(),
        success: result.success,
        context: {
          planId: plan.id,
          reasoning: plan.reasoning,
          taskId
        }
      };
      
      return richAction;
      
    } catch (error) {
      return {
        actionId: this.generateActionId(),
        actionType: plan.tool,
        inputs: plan.inputs,
        outputs: {
          success: false,
          result: `Error: ${error.message}`,
          metadata: {
            executionTime: Date.now() - startTime,
            tool: plan.tool,
            timestamp: Date.now(),
            error: error.message
          }
        },
        evidence: [],
        timestamp: Date.now(),
        success: false,
        context: {
          planId: plan.id,
          reasoning: plan.reasoning,
          taskId
        }
      };
    }
  }
}
```

### 2. Rich Loop Prevention
```typescript
class RichLoopPrevention {
  private memoryManager: RichMemoryManager;
  
  detectRichLoop(taskId: string): boolean {
    const context = this.memoryManager.getTaskContext(taskId);
    if (!context) return false;
    
    // Check for too many iterations
    if (context.actions.length >= 40) {
      return true;
    }
    
    // Check for duplicate actions with rich context
    const duplicateCount = this.countDuplicateActions(context.actions);
    if (duplicateCount >= 3) {
      return true;
    }
    
    // Check for validation loops
    const validationCount = this.countValidationActions(context.actions);
    if (validationCount >= 5) {
      return true;
    }
    
    // Check for evidence stagnation
    const recentEvidence = context.evidence.filter(e => 
      Date.now() - e.timestamp < 60000 // Last minute
    );
    if (recentEvidence.length === 0 && context.actions.length > 5) {
      return true;
    }
    
    return false;
  }
  
  private countDuplicateActions(actions: RichAction[]): number {
    const actionCounts = new Map<string, number>();
    
    for (const action of actions) {
      const key = `${action.actionType}:${JSON.stringify(action.inputs)}`;
      actionCounts.set(key, (actionCounts.get(key) || 0) + 1);
    }
    
    return Math.max(...actionCounts.values());
  }
  
  private countValidationActions(actions: RichAction[]): number {
    return actions.filter(action => action.actionType === 'validate').length;
  }
}
```

### 3. Rich Plan Generator
```typescript
class RichPlanGenerator {
  private memoryManager: RichMemoryManager;
  
  async generateRichPlans(task: string, taskId: string, taskType: string): Promise<RichPlanNode[]> {
    const context = this.memoryManager.getTaskContext(taskId);
    const plans: RichPlanNode[] = [];
    
    if (taskType === 'coding_task') {
      // Generate plans that create code with documentation
      plans.push({
        id: this.generatePlanId(),
        action: 'Create code implementation with documentation',
        tool: 'write_file',
        inputs: {
          filename: 'solution.py',
          content: this.generateCodeWithDocumentation(task)
        },
        reasoning: 'Coding task requires implementation with proper documentation',
        score: 1.0,
        expectedEvidence: ['file_creation', 'code_implementation', 'documentation']
      });
    } else if (taskType === 'simple_question') {
      plans.push({
        id: this.generatePlanId(),
        action: 'Answer question with evidence',
        tool: 'write_file',
        inputs: {
          filename: 'answer.md',
          content: this.generateAnswerWithEvidence(task)
        },
        reasoning: 'Simple question requires direct answer with evidence',
        score: 1.0,
        expectedEvidence: ['file_creation', 'synthesis']
      });
    }
    
    // Add validation plan if needed
    if (this.shouldAddValidationPlan(context)) {
      plans.push({
        id: this.generatePlanId(),
        action: 'Validate task completion with rich evidence',
        tool: 'validate',
        inputs: {
          trigger: 'manual',
          criteria: {
            requiredEvidence: this.getRequiredEvidence(taskType),
            minConfidence: 0.8
          }
        },
        reasoning: 'Validate completion based on rich evidence',
        score: 0.8,
        expectedEvidence: ['validation']
      });
    }
    
    return plans;
  }
  
  private getRequiredEvidence(taskType: string): string[] {
    switch (taskType) {
      case 'coding_task':
        return ['file_creation', 'code_implementation', 'documentation'];
      case 'research_task':
        return ['file_creation', 'synthesis', 'documentation'];
      case 'simple_question':
        return ['file_creation', 'synthesis'];
      default:
        return ['file_creation'];
    }
  }
}
```

## Rich Validator Integration

### 1. Rich Validator
```typescript
class RichValidator {
  private memoryManager: RichMemoryManager;
  private completionRules: RichCompletionRules;
  
  async validate(taskId: string): Promise<RichValidationResult> {
    const context = this.memoryManager.getTaskContext(taskId);
    if (!context) {
      return {
        completed: false,
        confidence: 0,
        rationale: 'Task context not found',
        evidence: [],
        requirements: []
      };
    }
    
    // Check completion with rich evidence
    const isComplete = this.completionRules.checkCompletion(context);
    
    if (isComplete) {
      return {
        completed: true,
        confidence: 1.0,
        rationale: 'Task completion criteria met with rich evidence',
        evidence: context.evidence,
        requirements: this.getCompletedRequirements(context)
      };
    } else {
      return {
        completed: false,
        confidence: 0.5,
        rationale: 'Task completion criteria not met',
        evidence: context.evidence,
        requirements: this.getMissingRequirements(context)
      };
    }
  }
  
  private getCompletedRequirements(context: RichTaskContext): string[] {
    const requirements: string[] = [];
    
    if (context.evidence.some(e => e.evidenceType === 'file_creation')) {
      requirements.push('File creation');
    }
    
    if (context.evidence.some(e => e.evidenceType === 'code_implementation')) {
      requirements.push('Code implementation');
    }
    
    if (context.evidence.some(e => e.evidenceType === 'documentation')) {
      requirements.push('Documentation');
    }
    
    return requirements;
  }
  
  private getMissingRequirements(context: RichTaskContext): string[] {
    const requirements: string[] = [];
    
    if (!context.evidence.some(e => e.evidenceType === 'file_creation')) {
      requirements.push('File creation');
    }
    
    if (context.taskType === 'coding_task' && 
        !context.evidence.some(e => e.evidenceType === 'code_implementation')) {
      requirements.push('Code implementation');
    }
    
    if (context.taskType === 'coding_task' && 
        !context.evidence.some(e => e.evidenceType === 'documentation')) {
      requirements.push('Documentation');
    }
    
    return requirements;
  }
}
```

## Benefits of Rich Context Design

### 1. Rich Evidence Tracking
- **File operations**: Track file creation, modification, and metadata
- **Code documentation**: Extract and store function/class documentation
- **Evidence chains**: Link actions to their evidence
- **Confidence scoring**: Rate evidence quality

### 2. Queryable Context
- **File registry**: Search files by type, content, or metadata
- **Code documentation**: Query functions, classes, and dependencies
- **Evidence search**: Find evidence by type, confidence, or source
- **Cross-references**: Link related files and code

### 3. BFS Integration
- **Context-aware planning**: Plans consider existing evidence
- **Rich completion rules**: Evidence-based completion validation
- **Loop prevention**: Detect stagnation in evidence generation
- **Validation integration**: Validator uses same evidence system

### 4. Task Isolation with Rich Context
- **Task-specific evidence**: Each task has isolated evidence
- **Cross-task references**: Optional linking between related tasks
- **Rich metadata**: Track task complexity, progress, and outcomes
- **Evidence persistence**: Maintain evidence across sessions

This design provides the rich context you requested while maintaining clean BFS integration and task isolation. The system tracks file operations, code documentation, and evidence chains, making everything queryable and searchable while preventing the conflicts we identified earlier.
