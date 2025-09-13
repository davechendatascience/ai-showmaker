/**
 * Enhanced Best-First Search Agent with Memory Bank Integration
 * 
 * This version integrates the Cline-aligned Memory Bank system for persistent,
 * file-based memory storage that survives agent restarts and provides
 * context-aware planning and learning capabilities.
 */

import { HTTPMCPClient } from '../mcp/http-mcp-client';
import { SessionManager } from '../core/session-manager';
import { RichMemoryManager, createRichMemorySystem } from '../core/memory';
import { BaseLanguageModel } from '@langchain/core/language_models/base';
import { HumanMessage, SystemMessage } from '@langchain/core/messages';
import { ValidatorAgent } from './validator-agent';
import {
  SearchState,
  PlanNode,
  ExecutionEntry,
  ScenarioPrediction,
  ToolScenario,
  ScenarioType,
  ScenarioOutcome,
  SearchConfig
} from '../types/enhanced-state';

// Validation action interface
export interface ValidationAction {
  type: 'validate';
  trigger: 'progress' | 'confidence' | 'level' | 'manual';
  criteria: {
    minProgress?: number;
    minConfidence?: number;
    levelThreshold?: number;
    customCondition?: string;
  };
  description: string;
}

export class EnhancedBestFirstSearchAgentWithMemoryBank {
  private mcpClient: HTTPMCPClient;
  private llm: BaseLanguageModel;
  private sessionManager: SessionManager;
  private richMemory: RichMemoryManager;
  private validator: ValidatorAgent;
  private sharedMemory: RichMemoryManager; // Alias for compatibility
  
  // Enhanced state management
  private state: SearchState;
  private stateHistory: SearchState[] = [];
  private scenarioCache: Map<string, ScenarioPrediction> = new Map();
  
  // Configuration with defaults
  private config: SearchConfig = {
    maxIterations: Number(process.env['BFS_MAX_ITER'] || 40),
    beamWidth: Number(process.env['BFS_BEAM_WIDTH'] || 4),
    minScore: Number(process.env['BFS_MIN_SCORE'] || 0.4),
    debug: String(process.env['BFS_DEBUG'] || 'false').toLowerCase() === 'true',
    validator: {
      every: Number(process.env['BFS_VALIDATOR_EVERY'] || 1),
      minConfidence: Number(process.env['BFS_VALIDATOR_CONF'] || 0.4),
      mode: (String(process.env['BFS_VALIDATOR_MODE'] || 'action').toLowerCase() as 'action' | 'periodic' | 'both'),
      valueTrigger: Number(process.env['BFS_VALUE_TRIGGER'] || 0.8),
      cooldown: Number(process.env['BFS_VALIDATION_COOLDOWN'] || 1),
      hintBoost: Number(process.env['BFS_HINT_BOOST'] || 0.35),
      specialHintBoost: Number(process.env['BFS_SPECIAL_HINT_BOOST'] || 0.1)
    },
    scenarioPrediction: {
      enabled: String(process.env['BFS_SCENARIO_PREDICTION'] || 'true').toLowerCase() === 'true',
      maxScenariosPerTool: Number(process.env['BFS_MAX_SCENARIOS'] || 5),
      minProbabilityThreshold: Number(process.env['BFS_MIN_PROBABILITY'] || 0.1),
      confidenceThreshold: Number(process.env['BFS_PREDICTION_CONFIDENCE'] || 0.6),
      learnFromOutcomes: String(process.env['BFS_LEARN_FROM_OUTCOMES'] || 'true').toLowerCase() === 'true',
      cacheDuration: Number(process.env['BFS_CACHE_DURATION'] || 300000) // 5 minutes
    }
  };

  constructor(mcpClient: HTTPMCPClient, llm: BaseLanguageModel, sessionManager: SessionManager) {
    this.mcpClient = mcpClient;
    this.llm = llm;
    this.sessionManager = sessionManager;
    
    // Initialize Rich Memory system
    this.richMemory = createRichMemorySystem();
    this.sharedMemory = this.richMemory; // Alias for compatibility
    
    this.validator = new ValidatorAgent(this.llm, this.richMemory);
    
    // Initialize state
    this.state = this.initializeState();
  }

  private initializeState(): SearchState {
    return {
      iteration: 0,
      task: '',
      sessionId: '',
      frontier: [],
      scratchpad: [],
      validatorState: {
        validationHistory: [],
        hints: [],
        confidenceTrend: [],
        lastValidationIteration: -Infinity,
        cooldownRemaining: 0
      },
      scenarioPredictions: [],
      metrics: {
        totalIterations: 0,
        plansGenerated: 0,
        plansExecuted: 0,
        averageExecutionTime: 0,
        successRate: 0,
        validatorInteractions: 0,
        predictionAccuracy: 0,
        efficiencyScore: 0
      },
      config: this.config
    };
  }

  // Public methods for debugging and state access
  getState(): SearchState {
    return this.state;
  }

  getScenarioCache(): Map<string, ScenarioPrediction> {
    return this.scenarioCache;
  }

  async executeTask(task: string, sessionId: string): Promise<string> {
    try {
      this.sessionManager.addMessage(sessionId, { role: 'user', content: task });
    } catch {}

    // Start task context for isolation
    const taskContext = this.sharedMemory.startTaskContext(task);
    console.log(`[EnhancedBFS-Memory] Started task context: ${taskContext.taskId}`);

    // Initialize state for this task
    this.state = this.initializeState();
    this.state.task = task;
    this.state.sessionId = sessionId;

    // Log task start in memory bank
    await this.richMemory.updateMemoryBank({
      type: 'active_context',
      content: `Starting task: ${task}`,
      metadata: {
        timestamp: new Date(),
        agent: 'main',
        iteration: 0,
        confidence: 1.0,
        tags: ['task-start', 'active']
      },
      context: {
        task,
        toolsUsed: [],
        successRate: 0,
        executionTime: 0
      }
    });

    const tools = this.mcpClient.getTools().map(t => ({ 
      name: t.name, 
      description: t.description, 
      schema: t.schema 
    }));

    // Get memory context for planning (limit size to prevent overwhelming LLM)
    // For simple questions, don't load memory bank context to avoid contamination
    const isSimpleQuestion = this.isSimpleQuestion(task);
    const fullMemoryContext = isSimpleQuestion ? '' : await this.richMemory.getBFSContext(task, 0);
    const memoryContext = fullMemoryContext.length > 5000 ? 
      fullMemoryContext.substring(0, 5000) + '...' : 
      fullMemoryContext;
    
    console.log(`[EnhancedBFS-Memory] ===== TASK INITIALIZATION =====`);
    console.log(`[EnhancedBFS-Memory] Task: "${task}"`);
    console.log(`[EnhancedBFS-Memory] Available Tools: ${tools.length}`);
    console.log(`[EnhancedBFS-Memory] Memory Context Loaded: ${memoryContext.length} chars`);

    // Generate complete plan tree upfront for efficiency
    console.log(`[EnhancedBFS-Memory] Generating initial plans...`);
    const planStartTime = Date.now();
    const initialPlans = await this.proposePlansWithMemory(task, tools, this.config.beamWidth, 0, memoryContext);
    const planTime = Date.now() - planStartTime;
    console.log(`[EnhancedBFS-Memory] Generated ${initialPlans.length} initial plans in ${planTime}ms`);
    
    // Apply failure awareness to plans
    const failureAwarePlans = this.applyFailureAwareness(initialPlans, task);
    console.log(`[EnhancedBFS-Memory] Applied failure awareness to ${failureAwarePlans.length} plans`);
    
    const scoreStartTime = Date.now();
    const scoredPlans = await this.scorePlansWithValidatorIntegration(task, failureAwarePlans);
    const scoreTime = Date.now() - scoreStartTime;
    console.log(`[EnhancedBFS-Memory] Scored initial plans with validator integration in ${scoreTime}ms`);
    
    this.sortFrontier(scoredPlans);
    this.state.frontier = scoredPlans;
    
    console.log(`[EnhancedBFS-Memory] Initial Plan Ranking:`);
    this.state.frontier.slice(0, 3).forEach((plan, idx) => {
      console.log(`  ${idx + 1}. ${plan.action} (score: ${plan.score?.toFixed(2)}, tool: ${plan.tool || 'none'})`);
    });
    console.log(`[EnhancedBFS-Memory] ===== STARTING SEARCH =====\n`);

    for (let iter = 0; iter < this.config.maxIterations; iter++) {
      this.state.iteration = iter;
      
      if (this.state.frontier.length === 0) break;
      
      const node = this.state.frontier.shift()!;
      console.log(`\n[EnhancedBFS-Memory] ===== ITERATION ${iter + 1} =====`);
      console.log(`[EnhancedBFS-Memory] Selected Plan: ${node.action}`);
      console.log(`[EnhancedBFS-Memory] Plan Score: ${node.score?.toFixed(2)}`);
      console.log(`[EnhancedBFS-Memory] Tool: ${node.tool || 'none'}`);
      
      // Log decision in memory bank
      await this.richMemory.logDecision(
        `Execute plan: ${node.action}`,
        `Selected plan with score ${node.score?.toFixed(2)}`,
        iter,
        node.score || 0.5,
        this.state.frontier.slice(0, 2).map(p => p.action)
      );

      // Execute with scenario-aware handling
      console.log(`[EnhancedBFS-Memory] Executing plan with scenario-aware handling...`);
      const executionResult = await this.executePlan(node, task, tools);
      
      // Update state with execution result
      this.updateStateWithExecution(executionResult, node);
      
      // Log execution in memory bank
      await this.richMemory.updateActiveContext(
        task,
        iter,
        [executionResult.tool || 'none'],
        executionResult.success ? 1.0 : 0.0,
        executionResult.executionTime || 0,
        `Executed: ${executionResult.step} - Success: ${executionResult.success}`
      );

      // Log errors or successes
      if (!executionResult.success) {
        await this.richMemory.logError(
          `Execution failed: ${executionResult.observation}`,
          `Tool: ${executionResult.tool}, Step: ${executionResult.step}`,
          iter,
          [executionResult.tool || 'none']
        );
      } else {
        // Prepare tool data for file content capture
        let toolData = undefined;
        if (executionResult.tool === 'write_file' && executionResult.params) {
          toolData = {
            filename: executionResult.params['filename'],
            content: executionResult.params['content'],
            filePath: executionResult.params['filename']
          };
        }
        
        await this.richMemory.logSuccessPattern(
          `Successful execution: ${executionResult.step}`,
          [executionResult.tool || 'none'],
          1.0,
          executionResult.executionTime || 0,
          toolData
        );
      }

      // Check if goal reached
      const isGoalReached = await this.isGoalStateReached(task);
      
      if (isGoalReached) {
        console.log(`[EnhancedBFS-Memory] ✅ GOAL STATE REACHED - Task complete!`);
        
        // Complete task context
        this.sharedMemory.completeTask('completed');
        
        // Log task completion
        await this.richMemory.updateMemoryBank({
          type: 'progress_summary',
          content: `Task completed successfully: ${task}`,
          metadata: {
            timestamp: new Date(),
            agent: 'main',
            iteration: iter,
            confidence: 1.0,
            tags: ['task-complete', 'success']
          },
          context: {
            task,
            toolsUsed: this.getExecutionHistory().map(e => e.metadata?.tool || 'none').filter(Boolean),
            successRate: 1.0,
            executionTime: this.state.metrics.averageExecutionTime
          }
        });
        
        return await this.renderFinalAnswer(task);
      }

      // Generate next plans
      const children = await this.proposePlansWithMemory(task, tools, this.config.beamWidth, node.depth + 1, memoryContext);
      const scored = await this.scorePlansWithValidatorIntegration(task, children);
      
      this.sortFrontier(scored);
      this.state.frontier.push(...scored);
      
      // Update metrics
      this.updateMetrics(executionResult);
      
      // Save state snapshot
      this.saveStateSnapshot();
    }

    // Task completed or timed out
    console.log(`\n[EnhancedBFS-Memory] ===== TASK COMPLETION =====`);
    
    // Log final outcome
    const finalOutcome = this.determineTaskOutcome();
    await this.richMemory.updateMemoryBank({
      type: 'progress_summary',
      content: `Task ${finalOutcome}: ${task} after ${this.state.metrics.totalIterations} iterations`,
      metadata: {
        timestamp: new Date(),
        agent: 'main',
        iteration: this.state.metrics.totalIterations,
        confidence: this.state.metrics.successRate,
        tags: [`task-${finalOutcome}`, 'final']
      },
      context: {
        task,
        toolsUsed: this.getExecutionHistory().map(e => e.metadata?.tool || 'none').filter(Boolean),
        successRate: this.state.metrics.successRate,
        executionTime: this.state.metrics.averageExecutionTime
      }
    });

    return await this.renderFinalAnswer(task);
  }

  // ==== ALL REQUIRED METHODS ====

  /**
   * Execute a validation action
   */
  private async executeValidationAction(inputs: any, task: string): Promise<{ success: boolean; text: string; completionSignal: boolean }> {
    try {
      const { trigger, criteria } = inputs;
      
      console.log(`[EnhancedBFS-Memory] 🔍 VALIDATION REQUEST DETAILS:`);
      console.log(`[EnhancedBFS-Memory] - Trigger: ${trigger}`);
      console.log(`[EnhancedBFS-Memory] - Criteria: ${JSON.stringify(criteria)}`);
      console.log(`[EnhancedBFS-Memory] - Task: "${task}"`);
      console.log(`[EnhancedBFS-Memory] - Current iteration: ${this.state.iteration}`);
      console.log(`[EnhancedBFS-Memory] - Execution history length: ${this.getExecutionHistory().length}`);
      
      // Check if validation criteria are met
      const shouldTrigger = this.shouldTriggerValidation(trigger, criteria);
      console.log(`[EnhancedBFS-Memory] - Should trigger validation: ${shouldTrigger}`);
      
      if (!shouldTrigger) {
        console.log(`[EnhancedBFS-Memory] ⏭️ Validation skipped: trigger conditions not met`);
        return {
          success: true,
          text: `Validation skipped - criteria not met for trigger: ${trigger}`,
          completionSignal: false
        };
      }

      console.log(`[EnhancedBFS-Memory] ✅ Proceeding with validation...`);
      
      // Execute validation
      const verdict = await this.validator.validate(task, this.getExecutionHistory());
      
      console.log(`[EnhancedBFS-Memory] 📊 VALIDATION RESULTS:`);
      console.log(`[EnhancedBFS-Memory] - Completed: ${verdict.completed}`);
      console.log(`[EnhancedBFS-Memory] - Confidence: ${verdict.confidence}`);
      console.log(`[EnhancedBFS-Memory] - Issues: ${JSON.stringify(verdict.issues)}`);
      console.log(`[EnhancedBFS-Memory] - Suggested actions: ${JSON.stringify(verdict.suggested_next_actions)}`);
      console.log(`[EnhancedBFS-Memory] - Evidence needed: ${JSON.stringify(verdict.evidence_needed)}`);
      console.log(`[EnhancedBFS-Memory] - Rationale: ${verdict.rationale}`);
      
      // Record validation in task context
      this.sharedMemory.recordValidation(verdict.confidence);
      
      // Add validation result to shared memory
      this.sharedMemory.addEntry({
        type: 'validation',
        content: `Validation triggered by ${trigger}: ${verdict.rationale}`,
        metadata: {
          agent: 'main',
          iteration: this.state.iteration,
          confidence: verdict.confidence,
          tool: 'validate',
          success: verdict.completed
        },
        context: {
          task,
          availableTools: [],
          iteration: this.state.iteration,
          frontierSize: this.state.frontier.length,
          taskId: this.sharedMemory.getCurrentTaskContext()?.taskId || '',
          taskHash: this.sharedMemory.getCurrentTaskContext()?.taskHash || ''
        }
      });

      const resultText = `Validation completed: ${verdict.completed ? 'TASK COMPLETE' : 'CONTINUE EXPLORATION'} (confidence: ${verdict.confidence})`;
      console.log(`[EnhancedBFS-Memory] 🎯 Validation result: ${resultText}`);

      return {
        success: true,
        text: resultText,
        completionSignal: verdict.completed
      };
    } catch (error) {
      console.log(`[EnhancedBFS-Memory] ❌ Validation failed: ${error}`);
      return {
        success: false,
        text: `Validation failed: ${error}`,
        completionSignal: false
      };
    }
  }

  /**
   * Determine if validation should be triggered based on criteria
   */
  private shouldTriggerValidation(trigger: string, criteria: any): boolean {
    const taskContext = this.sharedMemory.getCurrentTaskContext();
    if (!taskContext) {
      console.log(`[EnhancedBFS-Memory] ❌ No task context available for validation trigger`);
      return false;
    }

    console.log(`[EnhancedBFS-Memory] 🔍 Evaluating validation trigger: ${trigger}`);
    console.log(`[EnhancedBFS-Memory] - Task context: ${taskContext.taskId}`);
    console.log(`[EnhancedBFS-Memory] - Current iteration: ${this.state.iteration}`);
    console.log(`[EnhancedBFS-Memory] - Validation count: ${taskContext.validationCount}`);

    switch (trigger) {
      case 'progress':
        const progress = this.calculateProgress();
        const minProgress = criteria.minProgress || 0.5;
        const progressResult = progress >= minProgress;
        console.log(`[EnhancedBFS-Memory] 📈 Progress trigger evaluation:`);
        console.log(`[EnhancedBFS-Memory] - Current progress: ${progress}`);
        console.log(`[EnhancedBFS-Memory] - Minimum required: ${minProgress}`);
        console.log(`[EnhancedBFS-Memory] - Result: ${progressResult} (${progress} >= ${minProgress})`);
        return progressResult;
        
      case 'confidence':
        const confidence = this.calculateConfidence();
        const minConfidence = criteria.minConfidence || 0.7;
        const confidenceResult = confidence <= minConfidence;
        console.log(`[EnhancedBFS-Memory] 🎯 Confidence trigger evaluation:`);
        console.log(`[EnhancedBFS-Memory] - Current confidence: ${confidence}`);
        console.log(`[EnhancedBFS-Memory] - Maximum threshold: ${minConfidence}`);
        console.log(`[EnhancedBFS-Memory] - Result: ${confidenceResult} (${confidence} <= ${minConfidence})`);
        return confidenceResult;
        
      case 'level':
        const levelThreshold = criteria.levelThreshold || 3;
        const levelResult = this.state.iteration >= levelThreshold;
        console.log(`[EnhancedBFS-Memory] 📊 Level trigger evaluation:`);
        console.log(`[EnhancedBFS-Memory] - Current iteration: ${this.state.iteration}`);
        console.log(`[EnhancedBFS-Memory] - Required threshold: ${levelThreshold}`);
        console.log(`[EnhancedBFS-Memory] - Result: ${levelResult} (${this.state.iteration} >= ${levelThreshold})`);
        return levelResult;
        
      case 'manual':
        console.log(`[EnhancedBFS-Memory] ✋ Manual validation triggered - always proceed`);
        return true; // Always trigger manual validation
        
      case 'adaptive':
        console.log(`[EnhancedBFS-Memory] 🧠 Adaptive validation trigger - evaluating multiple factors`);
        return this.shouldTriggerAdaptiveValidation(criteria);
        
      default:
        console.log(`[EnhancedBFS-Memory] ❓ Unknown validation trigger: ${trigger} - skipping`);
        return false;
    }
  }

  /**
   * Smart adaptive validation triggering
   */
  private shouldTriggerAdaptiveValidation(criteria: any): boolean {
    const taskContext = this.sharedMemory.getCurrentTaskContext();
    if (!taskContext) return false;

    const progress = this.calculateProgress();
    const confidence = this.calculateConfidence();
    const iteration = this.state.iteration;
    const validationCount = taskContext.validationCount;
    const timeSinceLastValidation = taskContext.lastValidationTime 
      ? Date.now() - taskContext.lastValidationTime.getTime()
      : Infinity;

    // Adaptive criteria
    const minProgress = criteria.minProgress || 0.3;
    const maxConfidence = criteria.maxConfidence || 0.8;
    const minIteration = criteria.minIteration || 2;
    const maxValidations = criteria.maxValidations || 5;
    const minTimeBetweenValidations = criteria.minTimeBetweenValidations || 10000; // 10 seconds

    console.log(`[EnhancedBFS-Memory] 🧠 ADAPTIVE VALIDATION EVALUATION:`);
    console.log(`[EnhancedBFS-Memory] - Current progress: ${progress} (min: ${minProgress})`);
    console.log(`[EnhancedBFS-Memory] - Current confidence: ${confidence} (max: ${maxConfidence})`);
    console.log(`[EnhancedBFS-Memory] - Current iteration: ${iteration} (min: ${minIteration})`);
    console.log(`[EnhancedBFS-Memory] - Validation count: ${validationCount} (max: ${maxValidations})`);
    console.log(`[EnhancedBFS-Memory] - Time since last validation: ${timeSinceLastValidation}ms (min: ${minTimeBetweenValidations}ms)`);

    // Multiple conditions for adaptive triggering
    const conditions = [
      progress >= minProgress, // Progress threshold
      confidence <= maxConfidence, // Confidence threshold
      iteration >= minIteration, // Minimum iterations
      (validationCount || 0) < maxValidations, // Not too many validations
      timeSinceLastValidation > minTimeBetweenValidations // Time-based throttling
    ];

    const conditionNames = [
      'progress >= minProgress',
      'confidence <= maxConfidence', 
      'iteration >= minIteration',
      'validationCount < maxValidations',
      'timeSinceLastValidation > minTimeBetweenValidations'
    ];

    console.log(`[EnhancedBFS-Memory] 📋 CONDITION EVALUATION:`);
    conditions.forEach((condition, index) => {
      console.log(`[EnhancedBFS-Memory] - ${conditionNames[index]}: ${condition}`);
    });

    const metConditions = conditions.filter(Boolean).length;
    const shouldTrigger = metConditions >= 3; // At least 3 conditions met
    
    console.log(`[EnhancedBFS-Memory] 🎯 ADAPTIVE RESULT:`);
    console.log(`[EnhancedBFS-Memory] - Conditions met: ${metConditions}/5`);
    console.log(`[EnhancedBFS-Memory] - Required: 3+ conditions`);
    console.log(`[EnhancedBFS-Memory] - Should trigger: ${shouldTrigger}`);
    
    return shouldTrigger;
  }

  /**
   * Calculate current progress based on execution history
   */
  private calculateProgress(): number {
    const executions = this.getExecutionHistory();
    const totalExecutions = executions.length;
    const successfulExecutions = executions.filter(e => e.success).length;
    
    if (totalExecutions === 0) return 0;
    
    const successRate = successfulExecutions / totalExecutions;
    
    // Enhanced progress calculation with multiple factors
    const hasFileCreation = executions.some(e => 
      e.tool === 'write_file' && e.success
    );
    const hasSynthesis = executions.some(e => 
      e.tool === 'write_file' && e.success && 
      (e.params?.filename?.includes('recommendations') || 
       e.params?.filename?.includes('final-answer') ||
       e.params?.filename?.includes('summary') ||
       e.params?.filename?.includes('solution'))
    );
    const hasWebResearch = executions.some(e => 
      e.tool === 'search_web' && e.success
    );
    const hasCommandExecution = executions.some(e => 
      e.tool === 'execute_command' && e.success
    );
    const hasValidation = executions.some(e => 
      e.tool === 'validate' && e.success
    );
    
    // Weighted progress calculation
    let progress = 0;
    progress += successRate * 0.2; // Base success rate (20%)
    if (hasWebResearch) progress += 0.1; // Research phase (10%)
    if (hasCommandExecution) progress += 0.2; // Implementation phase (20%)
    if (hasFileCreation) progress += 0.2; // File creation (20%)
    if (hasSynthesis) progress += 0.2; // Synthesis phase (20%)
    if (hasValidation) progress += 0.1; // Validation phase (10%)
    
    return Math.min(progress, 1.0);
  }

  /**
   * Calculate current confidence based on recent performance
   */
  private calculateConfidence(): number {
    const executions = this.getExecutionHistory();
    if (executions.length === 0) return 0.5;
    
    // Recent performance (last 5 executions)
    const recentExecutions = executions.slice(-5);
    const recentSuccessRate = recentExecutions.length > 0 
      ? recentExecutions.filter(e => e.success).length / recentExecutions.length 
      : 0.5;
    
    // Overall performance
    const overallSuccessRate = executions.filter(e => e.success).length / executions.length;
    
    // Task context confidence
    const taskContext = this.richMemory.getCurrentTaskContext();
    const validationHistory = taskContext?.confidenceHistory || [];
    const avgValidationConfidence = validationHistory.length > 0 
      ? validationHistory.reduce((a: number, b: number) => a + b, 0) / validationHistory.length 
      : 0.5;
    
    // Weighted confidence calculation
    let confidence = 0;
    confidence += recentSuccessRate * 0.4; // Recent performance (40%)
    confidence += overallSuccessRate * 0.3; // Overall performance (30%)
    confidence += avgValidationConfidence * 0.3; // Validation history (30%)
    
    return Math.min(Math.max(confidence, 0), 1);
  }

  private async executePlan(node: PlanNode, task: string, tools: any[]): Promise<ExecutionEntry> {
    const startTime = Date.now();
    
    try {
      const resolved = this.resolvePlan(task, tools, node);
      
      let observation = { success: true, text: 'No-op', completionSignal: false };
      let actualScenario: ToolScenario | undefined;
      
      // Handle validation actions
      if (resolved.tool === 'validate') {
        observation = await this.executeValidationAction(resolved.inputs, task);
        actualScenario = this.determineActualScenario(observation, node.scenarios);
      } else if (resolved.tool) {
        observation = await this.execute(resolved.tool, resolved.inputs);
        actualScenario = this.determineActualScenario(observation, node.scenarios);
        
        if (this.config.scenarioPrediction.learnFromOutcomes && actualScenario) {
          this.learnFromOutcome(node, actualScenario);
        }
      }
      
      const executionTime = Date.now() - startTime;
      
      const entry: ExecutionEntry = {
        id: this.generateExecutionId(),
        planId: node.id,
        thought: node.reasoning,
        step: node.action,
        params: resolved.inputs,
        observation: observation.text,
        success: observation.success,
        meta: (observation as any).meta,
        score: node.score,
        executionTime,
        actualScenario
      };
      
      if (resolved.tool) entry.tool = resolved.tool;
      
      node.metadata.executed = true;
      node.metadata.executionAttempts++;
      node.metadata.updatedAt = Date.now();
      
      return entry;
      
    } catch (error) {
      const executionTime = Date.now() - startTime;
      
      return {
        id: this.generateExecutionId(),
        planId: node.id,
        thought: node.reasoning,
        step: node.action,
        observation: `Error: ${error}`,
        success: false,
        score: node.score,
        executionTime
      };
    }
  }

  private isSimpleQuestion(task: string): boolean {
    const simplePatterns = [
      /what is \d+\s*[+\-*/]\s*\d+\?/i,  // Math questions like "what is 2+2?"
      /^\d+\s*[+\-*/]\s*\d+$/i,          // Direct math like "2+2"
      /what is \d+\s*plus\s*\d+\?/i,     // "what is 2 plus 2?"
      /what is \d+\s*minus\s*\d+\?/i,    // "what is 5 minus 3?"
      /what is \d+\s*times\s*\d+\?/i,    // "what is 3 times 4?"
      /what is \d+\s*divided by\s*\d+\?/i, // "what is 8 divided by 2?"
    ];
    
    return simplePatterns.some(pattern => pattern.test(task.trim()));
  }

  private async renderFinalAnswer(task: string): Promise<string> {
    const executionHistory = this.getExecutionHistory();
    
    const sys = new SystemMessage(`# Role
You are the final answer composer with access to enhanced execution state and memory bank.
Provide a comprehensive answer based on the execution trace and state information.`);

    const trace = executionHistory.map((e, i) => 
      `${i + 1}. step=${e.content} tool=${e.metadata?.tool || 'none'} success=${e.metadata?.success} -> ${e.content.slice(0, 200)}`
    ).join('\n');

    const human = new HumanMessage(`Task: ${task}
Execution Trace:
${trace || 'None'}

State Metrics:
- Total iterations: ${this.state.metrics.totalIterations}
- Success rate: ${(this.state.metrics.successRate * 100).toFixed(1)}%
- Average execution time: ${this.state.metrics.averageExecutionTime.toFixed(0)}ms
- Validator interactions: ${this.state.metrics.validatorInteractions}

Write the final answer now.`);

    try {
      const resp = await this.llm.invoke([sys, human]);
      const answer = String(resp.content || '').trim();
      return `Task: ${task}\n\nEnhanced Execution Summary:\n${trace}\n\nAnswer:\n${answer}`;
    } catch {
      return `Task: ${task}\n\nExecution completed with ${executionHistory.length} steps.`;
    }
  }

  private getExecutionHistory(): any[] {
    return this.sharedMemory.queryMemories({
      types: ['execution', 'validation', 'error'],
      maxResults: 50,
      currentTaskOnly: true
    });
  }

  private async proposePlansWithMemory(
    task: string, 
    tools: any[], 
    k: number, 
    depth: number,
    memoryContext: string
  ): Promise<PlanNode[]> {
    
    const sys = new SystemMessage(`# Task Planner
Create exactly ${k} specific action plans to complete the task.

TASK ANALYSIS:
- If the task is a simple question (math, facts, definitions), provide a direct answer
- If the task requires research, use search_web to find information
- If the task requires implementation, create appropriate files
- If the task requires documentation, create relevant documents
- Only use complex tools when the task specifically requires them

GUIDELINES:
- For simple math questions (like "what is 2+2?"), just answer directly
- For factual questions, search for information if needed
- For complex tasks, gather information and synthesize findings
- For coding tasks, create ACTUAL working code, not just comments or placeholders
- Create deliverables only when the task specifically requires documentation
- Consider validation actions when meaningful progress has been made

CRITICAL PARAMETER REQUIREMENTS:
- write_file: {"filename": "name.ext", "content": "..."}
- read_file: {"filename": "name.ext"}
- execute_command: {"command": "actual command"}
- search_web: {"query": "search terms"}
- validate: {"trigger": "progress|confidence|level|manual|adaptive", "criteria": {...}}

VALIDATION ACTIONS:
- Use "validate" action when you want to check task completion status
- Trigger types: "progress" (after significant progress), "confidence" (when uncertain), "level" (at specific depths), "manual" (when explicitly needed)
- Validation can lead to goal state or provide feedback for continued exploration

MEMORY CONTEXT:
${memoryContext}

TASK: ${task}
Available Tools: ${tools.map(t => t.name).join(', ')}`);

    const examples = `
Examples for simple questions:
PROPOSAL:
ACTION: Answer the simple math question directly
TOOL: write_file
INPUTS: {"filename": "answer.md", "content": "# Answer\\n\\nThe answer to 2+2 is 4."}

PROPOSAL:
ACTION: Validate simple task completion
TOOL: validate
INPUTS: {"trigger": "manual", "criteria": {}}

Examples for research questions:
PROPOSAL:
ACTION: Search for information about the topic
TOOL: search_web
INPUTS: {"query": "relevant search terms"}

PROPOSAL:
ACTION: Create answer document with findings
TOOL: write_file
INPUTS: {"filename": "answer.md", "content": "# Answer\\n\\nBased on research: [findings]"}

Examples for complex tasks:
PROPOSAL:
ACTION: Create implementation file with actual working code
TOOL: write_file
INPUTS: {"filename": "solution.py", "content": "def solve_problem(input_data):\\n    # Actual implementation logic here\\n    result = process_data(input_data)\\n    return result\\n\\n# Test the solution\\nif __name__ == '__main__':\\n    test_input = [1, 2, 3]\\n    print(solve_problem(test_input))"}

PROPOSAL:
ACTION: Synthesize findings into comprehensive answer
TOOL: write_file
INPUTS: {"filename": "final-answer.md", "content": "# Task Completion Summary\\n\\n## Answer\\nThe solution has been implemented and tested.\\n\\n## Key findings\\n- Problem solved using [approach]\\n- Time complexity: O(n)\\n\\n## Recommendations\\n- Consider edge cases\\n- Add error handling"}
`;

    const human = new HumanMessage(`Create ${k} specific actions to complete this task.

Format each action as:
PROPOSAL:
ACTION: [specific action description]
TOOL: [tool name]
INPUTS: [JSON with correct parameters]

${examples}`);

    const res = await this.llm.invoke([sys, human]);
    const text = String(res.content || '');
    const blocks = text.split(/PROPOSAL:/i).map(s => s.trim()).filter(Boolean);
    
    let out: PlanNode[] = [];
    for (const b of blocks.slice(0, k)) {
      const action = this.extractSection(b, 'ACTION') || '';
      const toolName = this.extractSection(b, 'TOOL') || '';
      const inputsStr = this.extractSection(b, 'INPUTS');
      const reasoning = this.extractSection(b, 'REASONING') || '';
      const scenariosStr = this.extractSection(b, 'SCENARIOS') || '';
      
      let inputs: any = {};
      try { inputs = inputsStr ? JSON.parse(inputsStr) : {}; } catch {}
      
      if (action && this.validatePlan(action, toolName, inputs)) {
        const planId = this.generatePlanId();
        const tool = toolName || this.predictTool(task, tools, { action, inputs });
        
        const plan: PlanNode = {
          id: planId,
          action,
          inputs,
          reasoning,
          depth,
          score: 0.5,
          tool: tool || undefined,
          scenarios: this.predictScenariosFromString(tool || '', inputs, scenariosStr),
          validatorIntegration: {
            scoreModifier: 0,
            alignsWithHints: false,
            confidenceImpact: 0,
            addressesIssues: false,
            suggestedImprovements: []
          },
          metadata: {
            createdAt: Date.now(),
            updatedAt: Date.now(),
            considerationCount: 0,
            executed: false,
            executionAttempts: 0,
            tags: [],
            priority: 'MEDIUM'
          }
        };
        
        out.push(plan);
      }
    }
    
    return out;
  }

  private predictScenariosFromString(tool: string, _inputs: any, scenariosStr: string): ToolScenario[] {
    if (!this.config.scenarioPrediction.enabled || !tool) {
      return [];
    }

    const scenarios: ToolScenario[] = [];
    const scenarioTypes = scenariosStr.split(',').map(s => s.trim().toUpperCase() as ScenarioType);
    
    for (const scenarioType of scenarioTypes) {
      const scenario = this.generateScenario(tool, _inputs, scenarioType);
      if (scenario) {
        scenarios.push(scenario);
      }
    }
    
    return scenarios;
  }

  private generateScenario(_tool: string, _inputs: any, type: ScenarioType): ToolScenario | null {
    const baseProbability = this.getBaseProbability(type);
    if (baseProbability < this.config.scenarioPrediction.minProbabilityThreshold) {
      return null;
    }

    return {
      type,
      probability: baseProbability,
      outcome: this.generateScenarioOutcome(_tool, type),
      conditions: this.generateScenarioConditions(_tool, type),
      impact: this.generateScenarioImpact(type),
      followUpActions: this.generateFollowUpActions(_tool, type)
    };
  }

  private getBaseProbability(type: ScenarioType): number {
    const probabilities: Record<ScenarioType, number> = {
      'SUCCESS': 0.7,
      'PARTIAL_SUCCESS': 0.15,
      'VALIDATION_ERROR': 0.05,
      'SECURITY_ERROR': 0.02,
      'CONNECTION_ERROR': 0.03,
      'TIMEOUT': 0.02,
      'TOOL_NOT_FOUND': 0.01,
      'UNKNOWN_ERROR': 0.01,
      'RATE_LIMITED': 0.01,
      'INSUFFICIENT_DATA': 0.02,
      'CANCELLED': 0.01
    };
    return probabilities[type] || 0.01;
  }

  private generateScenarioOutcome(_tool: string, type: ScenarioType): ScenarioOutcome {
    switch (type) {
      case 'SUCCESS':
        return {
          resultType: 'SUCCESS',
          expectedData: this.getExpectedSuccessData(_tool),
          executionTimeRange: this.getExpectedExecutionTime(_tool),
          expectedMetadata: this.getExpectedMetadata(_tool)
        };
      case 'PARTIAL_SUCCESS':
        return {
          resultType: 'PARTIAL',
          expectedData: this.getExpectedPartialData(_tool),
          executionTimeRange: this.getExpectedExecutionTime(_tool),
          expectedMetadata: this.getExpectedMetadata(_tool)
        };
      default:
        return {
          resultType: 'ERROR',
          expectedData: { error: true },
          expectedError: this.getExpectedError(_tool, type),
          executionTimeRange: [100, 5000],
          expectedMetadata: { error: true }
        };
    }
  }

  private generateScenarioConditions(_tool: string, _type: ScenarioType): any[] {
    return [
      {
        type: 'INPUT_VALIDATION',
        description: `Input validation for ${_tool}`,
        isMet: true,
        confidence: 0.8
      }
    ];
  }

  private generateScenarioImpact(type: ScenarioType): any {
    switch (type) {
      case 'SUCCESS':
        return {
          progressImpact: 0.8,
          confidenceImpact: 0.1,
          timeImpact: 0.1,
          shouldTriggerValidation: false,
          shouldUpdateScoring: true
        };
      case 'PARTIAL_SUCCESS':
        return {
          progressImpact: 0.4,
          confidenceImpact: -0.1,
          timeImpact: 0.2,
          shouldTriggerValidation: true,
          shouldUpdateScoring: true
        };
      default:
        return {
          progressImpact: -0.3,
          confidenceImpact: -0.2,
          timeImpact: 0.3,
          shouldTriggerValidation: true,
          shouldUpdateScoring: true
        };
    }
  }

  private generateFollowUpActions(_tool: string, type: ScenarioType): string[] {
    switch (type) {
      case 'SUCCESS':
        return ['continue', 'validate', 'synthesize'];
      case 'PARTIAL_SUCCESS':
        return ['retry', 'alternative_approach', 'validate'];
      case 'CONNECTION_ERROR':
        return ['retry', 'alternative_tool', 'fallback'];
      case 'VALIDATION_ERROR':
        return ['fix_inputs', 'alternative_approach'];
      default:
        return ['retry', 'alternative_approach'];
    }
  }

  private getExpectedSuccessData(_tool: string): any {
    if (_tool.includes('search')) return { results: [], total_results: 0 };
    if (_tool.includes('calculate')) return { result: 0 };
    if (_tool.includes('extract')) return { content: '', length: 0 };
    return {};
  }

  private getExpectedPartialData(_tool: string): any {
    if (_tool.includes('search')) return { results: [], total_results: 0, partial: true };
    if (_tool.includes('extract')) return { content: '', length: 0, partial: true };
    return { partial: true };
  }

  private getExpectedExecutionTime(_tool: string): [number, number] {
    if (_tool.includes('search')) return [1000, 5000];
    if (_tool.includes('calculate')) return [100, 1000];
    if (_tool.includes('extract')) return [2000, 10000];
    return [500, 3000];
  }

  private getExpectedMetadata(_tool: string): any {
    if (_tool.includes('search')) return { source: 'web', cached: false };
    if (_tool.includes('extract')) return { content_type: 'text/html' };
    return {};
  }

  private getExpectedError(_tool: string, type: ScenarioType): string {
    const errors: Record<ScenarioType, string> = {
      'SUCCESS': 'Success',
      'PARTIAL_SUCCESS': 'Partial success',
      'VALIDATION_ERROR': 'Invalid input parameters',
      'SECURITY_ERROR': 'Access denied',
      'CONNECTION_ERROR': 'Network connection failed',
      'TIMEOUT': 'Operation timed out',
      'TOOL_NOT_FOUND': 'Tool not available',
      'UNKNOWN_ERROR': 'Unexpected error occurred',
      'RATE_LIMITED': 'Rate limit exceeded',
      'INSUFFICIENT_DATA': 'Insufficient data to proceed',
      'CANCELLED': 'Operation was cancelled'
    };
    return errors[type] || 'Unknown error';
  }

  private calculatePredictionConfidence(_tool: string, scenarios: ToolScenario[]): number {
    const diversity = new Set(scenarios.map(s => s.type)).size / scenarios.length;
    const avgProbability = scenarios.reduce((sum, s) => sum + s.probability, 0) / scenarios.length;
    return (diversity + avgProbability) / 2;
  }

  private async scorePlansWithValidatorIntegration(
    task: string, 
    plans: PlanNode[]
  ): Promise<PlanNode[]> {
    const executionHistory = this.getExecutionHistory();
    const scored = await this.scorePlans(task, plans, executionHistory);
    
    for (const plan of scored) {
      plan.validatorIntegration = this.calculateValidatorIntegration(plan);
      plan.score = Math.min(1, plan.score + plan.validatorIntegration.scoreModifier);
    }
    
    return scored;
  }

  private calculateValidatorIntegration(plan: PlanNode): any {
    const hints = this.state.validatorState.hints;
    const lastValidation = this.state.validatorState.lastValidation;
    const taskContext = this.sharedMemory.getCurrentTaskContext();
    
    let scoreModifier = 0;
    let alignsWithHints = false;
    let confidenceImpact = 0;
    let addressesIssues = false;
    let suggestedImprovements: string[] = [];
    
    // Check for repeated validator feedback (stuck in loop)
    const recentValidations = this.state.validatorState.validationHistory.slice(-5);
    const isRepeatingFeedback = recentValidations.length >= 3 && 
      recentValidations.every(v => v.suggested_next_actions?.join(',') === hints.join(','));
    
    if (isRepeatingFeedback) {
      console.log(`[EnhancedBFS-Memory] WARNING: Detected repeated validator feedback, boosting plans that address issues`);
      // Give significant boost to plans that address the repeated issues
      scoreModifier += 0.4;
    }
    
    // Enhanced hint alignment with semantic matching
    if (hints.length > 0) {
      const actionLower = plan.action.toLowerCase();
      const toolLower = plan.tool?.toLowerCase() || '';
      
      alignsWithHints = hints.some(hint => {
        const hintLower = hint.toLowerCase();
        return actionLower.includes(hintLower) || 
               hintLower.includes(actionLower) ||
               this.semanticActionMatch(actionLower, hintLower) ||
               this.toolActionMatch(toolLower, hintLower);
      });
      
      if (alignsWithHints) {
        scoreModifier += this.config.validator.hintBoost;
        console.log(`[EnhancedBFS-Memory] Plan aligns with validator hint: ${plan.action} -> ${hints.join(', ')}`);
      }
    }
    
    // Enhanced issue addressing with context awareness
    if (lastValidation?.issues) {
      addressesIssues = lastValidation.issues.some(issue => {
        const issueLower = issue.toLowerCase();
        return plan.action.toLowerCase().includes(issueLower) ||
               plan.reasoning.toLowerCase().includes(issueLower) ||
               this.semanticIssueMatch(plan, issueLower);
      });
      
      if (addressesIssues) {
        scoreModifier += 0.2;
        console.log(`[EnhancedBFS-Memory] Plan addresses validator issue: ${plan.action} -> ${lastValidation.issues.join(', ')}`);
      }
    }
    
    // Task context-aware scoring
    if (taskContext) {
      const progress = this.calculateProgress();
      const confidence = this.calculateConfidence();
      
      // Boost validation actions when appropriate
      if (plan.tool === 'validate') {
        if (progress >= 0.5 || confidence <= 0.6) {
          scoreModifier += 0.3; // Boost validation when progress is good or confidence is low
          console.log(`[EnhancedBFS-Memory] Boosting validation action: progress=${progress}, confidence=${confidence}`);
        }
      }
      
      // Boost synthesis actions when we have implementation evidence
      if (plan.tool === 'write_file' && 
          (plan.action.toLowerCase().includes('synthesis') || 
           plan.action.toLowerCase().includes('recommendations') ||
           plan.action.toLowerCase().includes('final'))) {
        const hasImplementation = this.getExecutionHistory().some(e => 
          e.tool === 'write_file' && e.success
        );
        if (hasImplementation) {
          scoreModifier += 0.2;
          console.log(`[EnhancedBFS-Memory] Boosting synthesis action after implementation`);
        }
      }
    }
    
    // Reduce confidence if we're stuck in a validation loop
    if (isRepeatingFeedback && !alignsWithHints) {
      confidenceImpact = -0.1;
    }
    
    // Generate improvement suggestions
    if (!alignsWithHints && hints.length > 0) {
      suggestedImprovements.push(`Consider incorporating: ${hints.join(', ')}`);
    }
    if (!addressesIssues && lastValidation?.issues && lastValidation.issues.length > 0) {
      suggestedImprovements.push(`Address issues: ${lastValidation.issues.join(', ')}`);
    }
    
    return {
      scoreModifier,
      alignsWithHints,
      confidenceImpact,
      addressesIssues,
      suggestedImprovements
    };
  }

  /**
   * Semantic matching for actions and hints
   */
  private semanticActionMatch(action: string, hint: string): boolean {
    const actionWords = action.split(/\s+/);
    const hintWords = hint.split(/\s+/);
    
    // Check for semantic similarity
    const semanticPairs = [
      ['create', 'write', 'generate', 'build'],
      ['search', 'find', 'lookup', 'research'],
      ['execute', 'run', 'command', 'install'],
      ['validate', 'check', 'verify', 'test'],
      ['synthesize', 'summarize', 'recommend', 'final']
    ];
    
    for (const pair of semanticPairs) {
      const actionMatch = actionWords.some(word => pair.includes(word));
      const hintMatch = hintWords.some(word => pair.includes(word));
      if (actionMatch && hintMatch) return true;
    }
    
    return false;
  }

  /**
   * Tool-action matching
   */
  private toolActionMatch(tool: string, hint: string): boolean {
    const toolHintMap: Record<string, string[]> = {
      'write_file': ['create', 'write', 'generate', 'synthesize', 'document'],
      'search_web': ['search', 'find', 'research', 'lookup'],
      'execute_command': ['execute', 'run', 'install', 'command'],
      'validate': ['validate', 'check', 'verify', 'test']
    };
    
    const toolHints = toolHintMap[tool] || [];
    return toolHints.some(h => hint.includes(h));
  }

  /**
   * Semantic issue matching
   */
  private semanticIssueMatch(plan: PlanNode, issue: string): boolean {
    const issueActionMap: Record<string, string[]> = {
      'no implementation': ['write', 'create', 'implement', 'code'],
      'no synthesis': ['synthesize', 'recommendations', 'final', 'summary'],
      'no file creation': ['write_file', 'create', 'generate'],
      'no final answer': ['final', 'answer', 'summary', 'conclusion']
    };
    
    const actionWords = plan.action.toLowerCase().split(/\s+/);
    const relevantActions = issueActionMap[issue] || [];
    
    return relevantActions.some(action => 
      actionWords.some(word => word.includes(action))
    );
  }

  private async scorePlans(task: string, plans: PlanNode[], executionHistory: any[]): Promise<PlanNode[]> {
    const recentActions = executionHistory.slice(-5).map((e: any) => e.content).join(', ');
    const planDescriptions = plans.map((p, i) => 
      `${i + 1}. ${p.action}${p.tool ? ` (tool: ${p.tool})` : ' (no-op)'} - ${p.reasoning}`
    ).join('\n');

    const prompt = `You are an expert at evaluating action plans for task completion. Analyze each plan's utility in the current context.

TASK: "${task}"

RECENT ACTIONS: ${recentActions || 'None'}

AVAILABLE PLANS:
${planDescriptions}

Rate each plan's utility on a scale of 0.0 to 1.0 based on direct task relevance and information value.

Respond with ONLY the scores in order, separated by newlines:`;

    try {
      const response = await this.llm.invoke(prompt);
      const responseText = typeof response === 'string' ? response : response.content || response.text || String(response);
      const scores = responseText.trim().split('\n').map((s: string) => parseFloat(s.trim())).filter((s: number) => !isNaN(s));
      
      plans.forEach((plan, i) => {
        if (scores[i] !== undefined) {
          plan.score = Math.max(0.0, Math.min(1.0, scores[i]));
        } else {
          plan.score = plan.tool ? 0.6 : 0.2;
        }
      });
    } catch (error) {
      console.warn(`[EnhancedBFS-Memory] LLM scoring failed, using fallback: ${error}`);
      plans.forEach(plan => {
        plan.score = plan.tool ? 0.6 : 0.2;
      });
    }
    
    return plans;
  }

  private sortFrontier(frontier: PlanNode[]): void {
    frontier.sort((a, b) => (b.score || 0) - (a.score || 0));
    if (frontier.length > this.config.beamWidth) {
      frontier.splice(this.config.beamWidth);
    }
  }

  private predictTool(_task: string, tools: any[], plan: { action: string; inputs: any }): string | undefined {
    const name = plan.action.toLowerCase();
    const toolNames = new Set(tools.map((t: any) => String(t.name)));
    
    if (/gather|search|discover|info/.test(name)) {
      if (toolNames.has('search_web')) return 'search_web';
      if (toolNames.has('search_and_extract')) return 'search_and_extract';
    }
    if (/extract|parse|scrape|content/.test(name)) {
      if (toolNames.has('extract_content')) return 'extract_content';
    }
    if (/calculate|compute|math/.test(name)) {
      if (toolNames.has('calculate')) return 'calculate';
    }
    
    return undefined;
  }

  private resolvePlan(_task: string, _tools: any[], plan: PlanNode): { tool?: string | undefined; inputs: any } {
    return {
      tool: plan.tool,
      inputs: plan.inputs
    };
  }

  private async execute(tool: string, params: any): Promise<{ success: boolean; text: string; completionSignal: boolean; meta?: any }> {
    try {
      // Fix parameter mapping for write_file tool
      let fixedParams = params || {};
      if (tool === 'write_file' && params && params.file_name && !params.filename) {
        fixedParams = { ...params, filename: params.file_name };
        delete fixedParams.file_name;
      }
      
      const result = await this.mcpClient.executeTool(tool, fixedParams);
      const ok = typeof result?.success === 'boolean' ? Boolean(result.success) : true;
      const blob = JSON.stringify(result || '').slice(0, 800);
      return { success: ok, text: blob, completionSignal: false, meta: result };
    } catch (e: any) {
      return { success: false, text: String(e || 'execution error'), completionSignal: false };
    }
  }

  private updateStateWithExecution(execution: ExecutionEntry, _node: PlanNode): void {
    // Enhanced execution logging with file creation detection
    let executionContent = `Executed: ${execution.step} with tool ${execution.tool || 'none'} - Success: ${execution.success}`;
    
    // Check if this is a file creation operation
    if (execution.tool === 'write_file' && execution.success) {
      // Extract filename from the step or observation
      const filenameMatch = execution.step.match(/filename['"]?\s*:\s*['"]?([^'"\s]+)/) || 
                           execution.observation.match(/File ['"]([^'"]+)['"] written successfully/);
      const filename = filenameMatch ? filenameMatch[1] : 'unknown file';
      executionContent = `Created file: ${filename} - ${execution.step}`;
    }
    
    // Store execution in shared memory instead of scratchpad
    this.sharedMemory.addEntry({
      type: 'execution',
      content: executionContent,
      metadata: {
        agent: 'main',
        iteration: this.state.iteration,
        tool: execution.tool || 'none',
        success: execution.success,
        confidence: execution.score || 0.5
      },
      context: {
        task: this.state.task,
        availableTools: this.mcpClient.getTools().map(t => t.name),
        iteration: this.state.iteration,
        frontierSize: this.state.frontier.length,
        taskId: this.sharedMemory.getCurrentTaskContext()?.taskId || '',
        taskHash: this.sharedMemory.getCurrentTaskContext()?.taskHash || ''
      }
    });
      this.state.metrics.plansExecuted++;
  }

  // ==== MISSING METHODS ====

  private updateMetrics(execution: ExecutionEntry): void {
    this.state.metrics.totalIterations++;
    if (execution.executionTime) {
      const total = this.state.metrics.averageExecutionTime * (this.state.metrics.plansExecuted - 1) + execution.executionTime;
      this.state.metrics.averageExecutionTime = total / this.state.metrics.plansExecuted;
    }
    
    const executionHistory = this.getExecutionHistory();
    const successful = executionHistory.filter(e => e.metadata?.success).length;
    this.state.metrics.successRate = successful / executionHistory.length;
  }

  private saveStateSnapshot(): void {
    this.stateHistory.push(JSON.parse(JSON.stringify(this.state)));
  }

  private determineTaskOutcome(): 'success' | 'failure' | 'partial' {
    const executionHistory = this.getExecutionHistory();
    const recentEntries = executionHistory.slice(-3);
    const hasSuccess = recentEntries.some(entry => entry.metadata?.success);
    const hasFailure = recentEntries.some(entry => !entry.metadata?.success);
    
    if (hasSuccess && !hasFailure) return 'success';
    if (hasFailure && !hasSuccess) return 'failure';
    return 'partial';
  }

  private determineActualScenario(observation: any, predictedScenarios: ToolScenario[]): ToolScenario | undefined {
    const success = observation.success;
    const text = observation.text.toLowerCase();
    
    if (success) {
      return predictedScenarios.find(s => s.type === 'SUCCESS') || 
             predictedScenarios.find(s => s.type === 'PARTIAL_SUCCESS');
    }
    
    if (text.includes('validation')) return predictedScenarios.find(s => s.type === 'VALIDATION_ERROR');
    if (text.includes('connection') || text.includes('network')) return predictedScenarios.find(s => s.type === 'CONNECTION_ERROR');
    if (text.includes('timeout')) return predictedScenarios.find(s => s.type === 'TIMEOUT');
    if (text.includes('not found')) return predictedScenarios.find(s => s.type === 'TOOL_NOT_FOUND');
    if (text.includes('rate limit')) return predictedScenarios.find(s => s.type === 'RATE_LIMITED');
    
    return predictedScenarios.find(s => s.type === 'UNKNOWN_ERROR');
  }

  private learnFromOutcome(node: PlanNode, actualScenario: ToolScenario): void {
    const cacheKey = `${node.tool || 'unknown'}:${JSON.stringify(node.inputs)}`;
    const cached = this.scenarioCache.get(cacheKey);
    
    if (cached) {
      cached.scenarios.forEach(scenario => {
        if (scenario.type === actualScenario.type) {
          scenario.probability = Math.min(1, scenario.probability + 0.1);
        } else {
          scenario.probability = Math.max(0, scenario.probability - 0.05);
        }
      });
      
      cached.confidence = this.calculatePredictionConfidence(node.tool || '', cached.scenarios);
    }
  }

  private generateExecutionId(): string {
    return `exec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generatePlanId(): string {
    return `plan_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private extractSection(text: string, key: string): string | null {
    const re = new RegExp(`${key}\\s*:\\s*([\\s\\S]*?)(?:\\n[A-Z_]+\\s*:|$)`, 'i');
    const m = text.match(re);
    return m && m[1] ? m[1].trim() : null;
  }

  private validatePlan(action: string, toolName: string, inputs: any): boolean {
    // Basic validation - ensure we have action and tool
    if (!action || !toolName) {
      return false;
    }
    
    // Check for correct parameter names based on tool
    if (toolName === 'write_file' && !inputs.filename) {
      console.log(`[EnhancedBFS-Memory] Invalid plan: write_file missing filename parameter`);
      return false;
    }
    
    if (toolName === 'read_file' && !inputs.filename) {
      console.log(`[EnhancedBFS-Memory] Invalid plan: read_file missing filename parameter`);
      return false;
    }
    
    if (toolName === 'execute_command' && !inputs.command) {
      console.log(`[EnhancedBFS-Memory] Invalid plan: execute_command missing command parameter`);
      return false;
    }
    
    if (toolName === 'search_web' && !inputs.query) {
      console.log(`[EnhancedBFS-Memory] Invalid plan: search_web missing query parameter`);
      return false;
    }
    
    return true;
  }




  private async isGoalStateReached(task: string): Promise<boolean> {
    try {
      // Debug: Log current state
      console.log(`[EnhancedBFS-Memory] Checking goal state at iteration ${this.state.iteration}`);
      
      // Get execution history from shared memory for the validator
      const executionHistory = this.sharedMemory.queryMemories({
        types: ['execution', 'validation', 'error'],
        maxResults: 20,
        currentTaskOnly: true
      });
      
      console.log(`[EnhancedBFS-Memory] Shared memory entries: ${executionHistory.length}`);
      console.log(`[EnhancedBFS-Memory] Recent executions:`, executionHistory.slice(-3).map((e: any) => e.content));
      console.log(`[EnhancedBFS-Memory] Validator hints:`, this.state.validatorState.hints);

      // Debug: Log memory bank state
      const memoryBankStats = this.richMemory.getStats();
      console.log(`[EnhancedBFS-Memory] Memory Bank Stats:`, memoryBankStats);
      
      // Filter for code-related executions and synthesis evidence
      const codeExecutions = executionHistory.filter((e: any) => 
        e.content.includes('write_file') || 
        e.content.includes('execute_command') ||
        e.content.includes('written successfully') ||
        e.content.includes('created') ||
        e.content.includes('executed') ||
        e.content.includes('synthesize') ||
        e.content.includes('recommendations') ||
        e.content.includes('final-answer') ||
        e.content.includes('comprehensive')
      );
      
      // Create synthetic entries for validator
      const syntheticEntries: ExecutionEntry[] = codeExecutions.map((entry: any, index: number) => ({
        id: `synthetic_${index}`,
        planId: 'synthetic',
        thought: entry.content,
        step: entry.content,
        observation: entry.content,
        success: entry.metadata?.success !== false,
        tool: entry.metadata?.tool || 'unknown',
        executionTime: 0
      }));
      
      const verdict = await this.validator.validate(task, syntheticEntries);
      
      // Debug: Log validator verdict
      console.log(`[EnhancedBFS-Memory] Validator verdict:`, {
        completed: verdict.completed,
        confidence: verdict.confidence,
        issues: verdict.issues,
        suggested_next_actions: verdict.suggested_next_actions,
        evidence_needed: verdict.evidence_needed,
        rationale: verdict.rationale
      });
      
      // Store validator feedback in shared memory
      this.sharedMemory.addEntry({
        type: 'validation',
        content: `Validator: completed=${verdict.completed}, confidence=${verdict.confidence}, issues=${verdict.issues?.join(', ') || 'none'}`,
        metadata: {
          agent: 'validator',
          iteration: this.state.iteration,
          confidence: verdict.confidence,
          success: verdict.completed
        },
        context: {
          task,
          availableTools: this.mcpClient.getTools().map(t => t.name),
          iteration: this.state.iteration,
          frontierSize: this.state.frontier.length,
          taskId: this.sharedMemory.getCurrentTaskContext()?.taskId || '',
          taskHash: this.sharedMemory.getCurrentTaskContext()?.taskHash || ''
        }
      });

      // Update validator state with feedback
      if (verdict.suggested_next_actions) {
        this.state.validatorState.hints = verdict.suggested_next_actions;
      }

      // Log validation in memory bank for pattern learning
      await this.richMemory.updateMemoryBank({
        type: 'progress_summary',
        content: `Validation: ${verdict.completed ? 'COMPLETE' : 'INCOMPLETE'} (confidence: ${verdict.confidence.toFixed(2)})`,
        metadata: {
          timestamp: new Date(),
          agent: 'validator',
          iteration: this.state.iteration,
          confidence: verdict.confidence,
          tags: verdict.completed ? ['validation-complete'] : ['validation-incomplete']
        },
        context: {
          task,
          toolsUsed: ['validator'],
          successRate: verdict.confidence,
          executionTime: 0
        }
      });

      // Use enhanced memory querying to get proper evidence
      const taskCompletionProof = this.sharedMemory.getTaskCompletionProof();
      
      // Task-specific completion criteria
      const taskType = this.determineTaskType(task);
      const taskSpecificCriteria = this.evaluateTaskSpecificCriteria(taskType, taskCompletionProof, verdict);
      
      // Enhanced completion criteria - TRUST validator as authoritative source
      const hasImplementation = taskCompletionProof.hasImplementation;
      const validatorApproves = verdict.completed && verdict.confidence >= this.config.validator.minConfidence;
      
      // Trust validator decision - it has access to all evidence and context
      const isComplete = validatorApproves;
      
      // Log synthesis detection using enhanced evidence
      if (taskCompletionProof.hasSynthesis) {
        console.log(`[EnhancedBFS-Memory] ✅ Synthesis evidence detected (${taskCompletionProof.synthesisEntries.length} entries)`);
      }
      if (taskCompletionProof.hasFileCreation) {
        console.log(`[EnhancedBFS-Memory] ✅ File creation evidence detected (${taskCompletionProof.fileCreationEntries.length} entries)`);
      }
      if (hasImplementation) {
        console.log(`[EnhancedBFS-Memory] ✅ Implementation evidence detected (files + synthesis)`);
      }
      
      // Log completion decision
      console.log(`[EnhancedBFS-Memory] Completion Analysis:`);
      console.log(`[EnhancedBFS-Memory] - Task type: ${taskType}`);
      console.log(`[EnhancedBFS-Memory] - Task-specific criteria: ${taskSpecificCriteria.meetsRequirements} (${taskSpecificCriteria.reason}) [INFO ONLY]`);
      console.log(`[EnhancedBFS-Memory] - Validator approves: ${validatorApproves} (confidence: ${verdict.confidence}, threshold: ${this.config.validator.minConfidence}) [AUTHORITATIVE]`);
      console.log(`[EnhancedBFS-Memory] - Has implementation: ${hasImplementation}`);
      console.log(`[EnhancedBFS-Memory] - Final decision: ${isComplete ? 'COMPLETE' : 'INCOMPLETE'} (based on validator)`);
      
      // If not complete, provide feedback to guide next actions
      if (!isComplete && verdict.suggested_next_actions) {
        console.log(`[EnhancedBFS-Memory] Validator feedback: ${verdict.suggested_next_actions.join(', ')}`);
        
        // Check if we're stuck in a loop
        const recentHints = this.state.validatorState.hints;
        const isRepeating = verdict.suggested_next_actions.every(action => 
          recentHints.includes(action)
        );
        
      // Store validation history for loop detection
      this.state.validatorState.validationHistory.push({
        completed: verdict.completed,
        confidence: verdict.confidence,
        issues: verdict.issues || [],
        suggested_next_actions: verdict.suggested_next_actions || [],
        evidence_needed: verdict.evidence_needed || [],
        rationale: verdict.rationale || '',
        timestamp: Date.now(),
        iteration: this.state.iteration
      });
        
        // Keep only recent history
        if (this.state.validatorState.validationHistory.length > 10) {
          this.state.validatorState.validationHistory.shift();
        }
        
        if (isRepeating && this.state.iteration > 10) {
          console.log(`[EnhancedBFS-Memory] WARNING: Validator giving repeated feedback, may be stuck in loop`);
          
          // Check if we've actually created files
          const fileCreations = executionHistory.filter((e: any) => 
            e.content.includes('written successfully') || e.content.includes('created')
          );
          
          if (fileCreations.length > 0 && this.state.iteration > 15) {
            console.log(`[EnhancedBFS-Memory] Force completion: Found ${fileCreations.length} file creations despite validator feedback`);
            return true; // Force completion
          }
          
          // If we've tried many iterations but validator keeps saying the same thing, force completion
          if (this.state.iteration > 20) {
            console.log(`[EnhancedBFS-Memory] Force completion: Too many iterations (${this.state.iteration}) with repeated feedback`);
            return true;
          }
        }
      }
      
      return isComplete;
    } catch (error) {
      console.error('[EnhancedBFS-Memory] Goal state detection failed:', error);
      
      // Log validation error in memory bank
      await this.richMemory.logError(
        'Validation failed',
        `Error: ${error}`,
        this.state.iteration,
        ['validator']
      );
      
      return false;
    }
  }


  /**
   * Determine the type of task based on the task description
   */
  private determineTaskType(task: string): string {
    const taskLower = task.toLowerCase();
    
    if (taskLower.includes('leetcode') || taskLower.includes('algorithm') || taskLower.includes('coding')) {
      return 'coding_problem';
    } else if (taskLower.includes('website') || taskLower.includes('webapp') || taskLower.includes('web app')) {
      return 'web_development';
    } else if (taskLower.includes('research') || taskLower.includes('analyze') || taskLower.includes('investigate')) {
      return 'research_analysis';
    } else if (taskLower.includes('install') || taskLower.includes('setup') || taskLower.includes('configure')) {
      return 'system_setup';
    } else if (taskLower.includes('create') && (taskLower.includes('file') || taskLower.includes('document'))) {
      return 'documentation';
    } else {
      return 'general';
    }
  }

  /**
   * Evaluate task-specific completion criteria
   */
  private evaluateTaskSpecificCriteria(
    taskType: string, 
    taskCompletionProof: any, 
    verdict: any
  ): { meetsRequirements: boolean; reason: string } {
    
    switch (taskType) {
      case 'coding_problem':
        return this.evaluateCodingProblemCriteria(taskCompletionProof, verdict);
      
      case 'web_development':
        return this.evaluateWebDevelopmentCriteria(taskCompletionProof, verdict);
      
      case 'research_analysis':
        return this.evaluateResearchAnalysisCriteria(taskCompletionProof, verdict);
      
      case 'system_setup':
        return this.evaluateSystemSetupCriteria(taskCompletionProof, verdict);
      
      case 'documentation':
        return this.evaluateDocumentationCriteria(taskCompletionProof, verdict);
      
      default:
        return this.evaluateGeneralCriteria(taskCompletionProof, verdict);
    }
  }

  /**
   * Coding problem completion criteria
   */
  private evaluateCodingProblemCriteria(taskCompletionProof: any, _verdict: any): { meetsRequirements: boolean; reason: string } {
    const hasCode = taskCompletionProof.hasFileCreation && 
      taskCompletionProof.fileCreationEntries.some((entry: any) => 
        entry.content.includes('.py') || 
        entry.content.includes('.js') || 
        entry.content.includes('.ts') ||
        entry.content.includes('function') ||
        entry.content.includes('def ') ||
        entry.content.includes('leetcode') // Accept LeetCode solution files
      );
    
    const hasSolution = taskCompletionProof.hasSynthesis;
    
    // For LeetCode problems, accept solution documentation as valid completion
    if (hasSolution && taskCompletionProof.hasFileCreation) {
      return { meetsRequirements: true, reason: 'Solution documentation and synthesis present' };
    } else if (hasCode && hasSolution) {
      return { meetsRequirements: true, reason: 'Code implementation and solution synthesis present' };
    } else if (hasCode) {
      return { meetsRequirements: true, reason: 'Code implementation present' };
    } else if (hasSolution) {
      return { meetsRequirements: true, reason: 'Solution synthesis present' };
    } else {
      return { meetsRequirements: false, reason: 'Missing code implementation or solution' };
    }
  }

  /**
   * Web development completion criteria
   */
  private evaluateWebDevelopmentCriteria(taskCompletionProof: any, _verdict: any): { meetsRequirements: boolean; reason: string } {
    const hasWebFiles = taskCompletionProof.hasFileCreation && 
      taskCompletionProof.fileCreationEntries.some((entry: any) => 
        entry.content.includes('.html') || 
        entry.content.includes('.css') || 
        entry.content.includes('.js') ||
        entry.content.includes('server') ||
        entry.content.includes('httpd')
      );
    
    const hasSetup = taskCompletionProof.hasImplementation;
    
    if (hasWebFiles && hasSetup) {
      return { meetsRequirements: true, reason: 'Web files created and server setup complete' };
    } else if (hasSetup) {
      return { meetsRequirements: true, reason: 'Server setup complete' };
    } else {
      return { meetsRequirements: false, reason: 'Missing web development components' };
    }
  }

  /**
   * Research analysis completion criteria
   */
  private evaluateResearchAnalysisCriteria(taskCompletionProof: any, _verdict: any): { meetsRequirements: boolean; reason: string } {
    const hasResearch = taskCompletionProof.hasFileCreation && 
      taskCompletionProof.fileCreationEntries.some((entry: any) => 
        entry.content.includes('search') || 
        entry.content.includes('research') ||
        entry.content.includes('findings')
      );
    
    const hasAnalysis = taskCompletionProof.hasSynthesis;
    
    if (hasResearch && hasAnalysis) {
      return { meetsRequirements: true, reason: 'Research conducted and analysis synthesized' };
    } else if (hasAnalysis) {
      return { meetsRequirements: true, reason: 'Analysis synthesized' };
    } else {
      return { meetsRequirements: false, reason: 'Missing research or analysis' };
    }
  }

  /**
   * System setup completion criteria
   */
  private evaluateSystemSetupCriteria(taskCompletionProof: any, _verdict: any): { meetsRequirements: boolean; reason: string } {
    const hasCommands = taskCompletionProof.hasImplementation;
    const hasDocumentation = taskCompletionProof.hasSynthesis;
    
    if (hasCommands && hasDocumentation) {
      return { meetsRequirements: true, reason: 'System setup commands executed and documented' };
    } else if (hasCommands) {
      return { meetsRequirements: true, reason: 'System setup commands executed' };
    } else {
      return { meetsRequirements: false, reason: 'Missing system setup execution' };
    }
  }

  /**
   * Documentation completion criteria
   */
  private evaluateDocumentationCriteria(taskCompletionProof: any, _verdict: any): { meetsRequirements: boolean; reason: string } {
    const hasDocumentation = taskCompletionProof.hasFileCreation && 
      taskCompletionProof.fileCreationEntries.some((entry: any) => 
        entry.content.includes('.md') || 
        entry.content.includes('.txt') ||
        entry.content.includes('documentation') ||
        entry.content.includes('guide')
      );
    
    if (hasDocumentation) {
      return { meetsRequirements: true, reason: 'Documentation files created' };
    } else {
      return { meetsRequirements: false, reason: 'Missing documentation files' };
    }
  }

  /**
   * General task completion criteria
   */
  private evaluateGeneralCriteria(taskCompletionProof: any, _verdict: any): { meetsRequirements: boolean; reason: string } {
    const hasImplementation = taskCompletionProof.hasImplementation;
    const hasSynthesis = taskCompletionProof.hasSynthesis;
    const hasFileCreation = taskCompletionProof.hasFileCreation;
    
    if (hasImplementation && hasSynthesis) {
      return { meetsRequirements: true, reason: 'Implementation and synthesis present' };
    } else if (hasImplementation) {
      return { meetsRequirements: true, reason: 'Implementation present' };
    } else if (hasFileCreation && hasSynthesis) {
      // For simple tasks, file creation + synthesis is sufficient (matches validator criteria)
      return { meetsRequirements: true, reason: 'File creation and synthesis present' };
    } else {
      return { meetsRequirements: false, reason: 'Missing implementation or synthesis' };
    }
  }

  /**
   * Apply failure awareness to plans by detecting known failure patterns
   * and adapting plans to avoid them
   */
  private applyFailureAwareness(plans: PlanNode[], task: string): PlanNode[] {
    const adaptedPlans: PlanNode[] = [];
    
    for (const plan of plans) {
      const failureRisk = this.assessFailureRisk(plan, task);
      
      if (failureRisk.high) {
        console.log(`[EnhancedBFS-Memory] ⚠️ High failure risk in plan: ${plan.action} - ${failureRisk.reason}`);
        
        // Try to adapt the plan to avoid the failure
        const adaptedPlan = this.adaptPlanToAvoidFailure(plan, failureRisk);
        if (adaptedPlan) {
          console.log(`[EnhancedBFS-Memory] ✅ Adapted plan: ${adaptedPlan.action}`);
          adaptedPlans.push(adaptedPlan);
        } else {
          // If can't adapt, reduce score significantly
          plan.score = (plan.score || 0.5) * 0.1; // Reduce to 10% of original score
          adaptedPlans.push(plan);
        }
      } else {
        adaptedPlans.push(plan);
      }
    }
    
    return adaptedPlans;
  }

  /**
   * Assess failure risk for a plan based on known failure patterns
   */
  private assessFailureRisk(plan: PlanNode, _task: string): { high: boolean; reason: string } {
    const action = plan.action.toLowerCase();
    const tool = plan.tool?.toLowerCase();
    
    // Check for path traversal attempts
    if (tool === 'write_file' && action.includes('var/www/html')) {
      return { 
        high: true, 
        reason: 'Path traversal detected - trying to write to system directory' 
      };
    }
    
    // Check for administrative command attempts
    if (tool === 'execute_command' && action.includes('systemctl')) {
      return { 
        high: true, 
        reason: 'Administrative command detected - systemctl operations not allowed' 
      };
    }
    
    // Check for repeated failed patterns from memory
    const recentFailures = this.getRecentFailurePatterns();
    for (const failure of recentFailures) {
      if (action.includes(failure.pattern) || (tool && tool.includes(failure.tool))) {
        return { 
          high: true, 
          reason: `Known failure pattern: ${failure.reason}` 
        };
      }
    }
    
    return { high: false, reason: 'No known failure patterns detected' };
  }

  /**
   * Adapt a plan to avoid known failure patterns
   */
  private adaptPlanToAvoidFailure(plan: PlanNode, failureRisk: { high: boolean; reason: string }): PlanNode | null {
    
    // Adapt path traversal attempts
    if (failureRisk.reason.includes('Path traversal')) {
      return {
        ...plan,
        action: plan.action.replace('/var/www/html/', 'webapp/'),
        tool: 'write_file',
        reasoning: `${plan.reasoning} (Adapted: Using workspace directory instead of system directory)`,
        score: (plan.score || 0.5) * 0.8 // Slightly reduce score for adaptation
      };
    }
    
    // Adapt administrative command attempts
    if (failureRisk.reason.includes('systemctl')) {
      return {
        ...plan,
        action: plan.action.replace('systemctl start httpd', 'python -m http.server 8000').replace('systemctl enable httpd', 'echo "Server started on port 8000"'),
        tool: 'execute_command',
        reasoning: `${plan.reasoning} (Adapted: Using Python HTTP server instead of systemctl)`,
        score: (plan.score || 0.5) * 0.7 // Reduce score more for major adaptation
      };
    }
    
    // For other failure patterns, try to generate alternative approach
    if (failureRisk.reason.includes('Known failure pattern')) {
      return {
        ...plan,
        action: `Alternative approach: ${plan.action}`,
        reasoning: `${plan.reasoning} (Adapted: Using alternative approach to avoid known failure)`,
        score: (plan.score || 0.5) * 0.6 // Reduce score for alternative approach
      };
    }
    
    return null; // Cannot adapt
  }

  /**
   * Get recent failure patterns from memory
   */
  private getRecentFailurePatterns(): Array<{ pattern: string; tool: string; reason: string }> {
    // This would ideally query the memory system for recent failures
    // For now, return hardcoded patterns based on the logs we saw
    return [
      {
        pattern: 'var/www/html',
        tool: 'write_file',
        reason: 'Path traversal error when attempting to create HTML file'
      },
      {
        pattern: 'systemctl',
        tool: 'execute_command', 
        reason: 'Administrative operations are not allowed'
      }
    ];
  }
}
