/**
 * Enhanced State Management Types for Best-First Search Agent
 * 
 * This module defines the comprehensive state management framework that allows
 * the search agent to handle multiple scenarios, predict outcomes, and integrate
 * validator feedback effectively.
 */

// ============================================================================
// CORE STATE TYPES
// ============================================================================

export interface SearchState {
  /** Current iteration number */
  iteration: number;
  
  /** Current task being executed */
  task: string;
  
  /** Session identifier */
  sessionId: string;
  
  /** Current frontier of plan nodes */
  frontier: PlanNode[];
  
  /** Execution history/scratchpad */
  scratchpad: ExecutionEntry[];
  
  /** Current validator state */
  validatorState: ValidatorState;
  
  /** Scenario predictions for next actions */
  scenarioPredictions: ScenarioPrediction[];
  
  /** Performance metrics */
  metrics: SearchMetrics;
  
  /** Configuration parameters */
  config: SearchConfig;
}

export interface PlanNode {
  /** Unique identifier for this plan */
  id: string;
  
  /** High-level action label */
  action: string;
  
  /** Reasoning for this step */
  reasoning: string;
  
  /** Input parameters */
  inputs: Record<string, any>;
  
  /** Expected value/score (0-1) */
  score: number;
  
  /** Search depth */
  depth: number;
  
  /** Resolved tool name (if applicable) */
  tool?: string | undefined;
  
  /** Parent plan node ID */
  parentId?: string;
  
  /** Scenario predictions for this plan */
  scenarios: ToolScenario[];
  
  /** Validator feedback integration */
  validatorIntegration: ValidatorIntegration;
  
  /** Execution metadata */
  metadata: PlanMetadata;
}

export interface ExecutionEntry {
  /** Unique identifier */
  id: string;
  
  /** Plan node that was executed */
  planId: string;
  
  /** Thought/reasoning */
  thought: string;
  
  /** Step description */
  step: string;
  
  /** Tool used (if any) */
  tool?: string;
  
  /** Parameters passed to tool */
  params?: Record<string, any>;
  
  /** Observation/result */
  observation: string;
  
  /** Success status */
  success: boolean;
  
  /** Execution metadata */
  meta?: Record<string, any>;
  
  /** Score at time of execution */
  score?: number;
  
  /** Execution time in milliseconds */
  executionTime?: number;
  
  /** Scenario that actually occurred */
  actualScenario?: ToolScenario | undefined;
}

// ============================================================================
// SCENARIO PREDICTION TYPES
// ============================================================================

export interface ScenarioPrediction {
  /** Plan node this prediction applies to */
  planId: string;
  
  /** Tool that would be executed */
  tool: string;
  
  /** Predicted scenarios with probabilities */
  scenarios: ToolScenario[];
  
  /** Confidence in predictions (0-1) */
  confidence: number;
  
  /** Prediction timestamp */
  timestamp: number;
}

export interface ToolScenario {
  /** Scenario type */
  type: ScenarioType;
  
  /** Probability of this scenario (0-1) */
  probability: number;
  
  /** Expected outcome */
  outcome: ScenarioOutcome;
  
  /** Conditions that lead to this scenario */
  conditions: ScenarioCondition[];
  
  /** Impact on search state */
  impact: ScenarioImpact;
  
  /** Suggested follow-up actions */
  followUpActions: string[];
}

export type ScenarioType = 
  | 'SUCCESS'           // Tool executes successfully
  | 'PARTIAL_SUCCESS'   // Tool partially succeeds
  | 'VALIDATION_ERROR'  // Input validation fails
  | 'SECURITY_ERROR'    // Security restrictions
  | 'CONNECTION_ERROR'  // Network/connection issues
  | 'TIMEOUT'           // Tool execution times out
  | 'TOOL_NOT_FOUND'    // Tool doesn't exist
  | 'UNKNOWN_ERROR'     // Unexpected error
  | 'RATE_LIMITED'      // Rate limiting
  | 'INSUFFICIENT_DATA' // Not enough data to proceed
  | 'CANCELLED';        // Operation cancelled

export interface ScenarioOutcome {
  /** Expected result type */
  resultType: 'SUCCESS' | 'ERROR' | 'PARTIAL';
  
  /** Expected data structure */
  expectedData: any;
  
  /** Expected error message (if applicable) */
  expectedError?: string;
  
  /** Expected execution time range */
  executionTimeRange: [number, number]; // [min, max] in ms
  
  /** Expected metadata */
  expectedMetadata?: Record<string, any>;
}

export interface ScenarioCondition {
  /** Condition type */
  type: 'INPUT_VALIDATION' | 'NETWORK_STATUS' | 'TOOL_AVAILABILITY' | 'RATE_LIMIT' | 'DATA_QUALITY' | 'SYSTEM_STATE';
  
  /** Condition description */
  description: string;
  
  /** Whether this condition is currently met */
  isMet: boolean;
  
  /** Confidence in condition assessment */
  confidence: number;
}

export interface ScenarioImpact {
  /** Impact on search progress (0-1) */
  progressImpact: number;
  
  /** Impact on confidence (0-1) */
  confidenceImpact: number;
  
  /** Impact on time efficiency (0-1) */
  timeImpact: number;
  
  /** Whether this scenario should trigger validation */
  shouldTriggerValidation: boolean;
  
  /** Whether this scenario should update scoring */
  shouldUpdateScoring: boolean;
}

// ============================================================================
// VALIDATOR INTEGRATION TYPES
// ============================================================================

export interface ValidatorState {
  /** Last validation result */
  lastValidation?: ValidationResult;
  
  /** Validation history */
  validationHistory: ValidationResult[];
  
  /** Current validator hints */
  hints: string[];
  
  /** Confidence trend */
  confidenceTrend: number[];
  
  /** Last validation iteration */
  lastValidationIteration: number;
  
  /** Validation cooldown remaining */
  cooldownRemaining: number;
}

export interface ValidatorIntegration {
  /** How validator feedback affects this plan's score */
  scoreModifier: number;
  
  /** Whether this plan aligns with validator hints */
  alignsWithHints: boolean;
  
  /** Validator confidence impact */
  confidenceImpact: number;
  
  /** Whether this plan addresses validator issues */
  addressesIssues: boolean;
  
  /** Suggested improvements from validator */
  suggestedImprovements: string[];
}

export interface ValidationResult {
  /** Whether task is completed */
  completed: boolean;
  
  /** Confidence level (0-1) */
  confidence: number;
  
  /** Issues identified */
  issues?: string[];
  
  /** Suggested next actions */
  suggested_next_actions?: string[];
  
  /** Evidence needed */
  evidence_needed?: string[];
  
  /** Rationale for validation */
  rationale?: string;
  
  /** Validation timestamp */
  timestamp: number;
  
  /** Validation iteration */
  iteration: number;
}

// ============================================================================
// METADATA AND CONFIGURATION TYPES
// ============================================================================

export interface PlanMetadata {
  /** When this plan was created */
  createdAt: number;
  
  /** Last updated timestamp */
  updatedAt: number;
  
  /** Number of times this plan has been considered */
  considerationCount: number;
  
  /** Whether this plan has been executed */
  executed: boolean;
  
  /** Execution attempts */
  executionAttempts: number;
  
  /** Tags for categorization */
  tags: string[];
  
  /** Priority level */
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

export interface SearchMetrics {
  /** Total iterations */
  totalIterations: number;
  
  /** Plans generated */
  plansGenerated: number;
  
  /** Plans executed */
  plansExecuted: number;
  
  /** Average execution time */
  averageExecutionTime: number;
  
  /** Success rate */
  successRate: number;
  
  /** Validator interactions */
  validatorInteractions: number;
  
  /** Scenario prediction accuracy */
  predictionAccuracy: number;
  
  /** Search efficiency score */
  efficiencyScore: number;
}

export interface SearchConfig {
  /** Maximum iterations */
  maxIterations: number;
  
  /** Beam width for frontier */
  beamWidth: number;
  
  /** Minimum score threshold */
  minScore: number;
  
  /** Validator configuration */
  validator: ValidatorConfig;
  
  /** Scenario prediction configuration */
  scenarioPrediction: ScenarioPredictionConfig;
  
  /** Debug mode */
  debug: boolean;
}

export interface ValidatorConfig {
  /** Validation frequency */
  every: number;
  
  /** Minimum confidence threshold */
  minConfidence: number;
  
  /** Validation mode */
  mode: 'action' | 'periodic' | 'both';
  
  /** Value trigger for validation */
  valueTrigger: number;
  
  /** Validation cooldown */
  cooldown: number;
  
  /** Hint boost factor */
  hintBoost: number;
  
  /** Special hint boost */
  specialHintBoost: number;
}

export interface ScenarioPredictionConfig {
  /** Whether to enable scenario prediction */
  enabled: boolean;
  
  /** Maximum scenarios per tool */
  maxScenariosPerTool: number;
  
  /** Minimum probability threshold */
  minProbabilityThreshold: number;
  
  /** Prediction confidence threshold */
  confidenceThreshold: number;
  
  /** Whether to learn from actual outcomes */
  learnFromOutcomes: boolean;
  
  /** Prediction cache duration */
  cacheDuration: number;
}

// ============================================================================
// UTILITY TYPES
// ============================================================================

export interface SearchStateUpdate {
  /** Type of update */
  type: 'FRONTIER_UPDATE' | 'SCRATCHPAD_UPDATE' | 'VALIDATOR_UPDATE' | 'METRICS_UPDATE' | 'SCENARIO_UPDATE';
  
  /** Update data */
  data: any;
  
  /** Update timestamp */
  timestamp: number;
  
  /** Update reason */
  reason: string;
}

export interface SearchStateSnapshot {
  /** Snapshot timestamp */
  timestamp: number;
  
  /** Complete state at this point */
  state: SearchState;
  
  /** Snapshot metadata */
  metadata: {
    iteration: number;
    frontierSize: number;
    scratchpadSize: number;
    validatorConfidence: number;
  };
}

// ============================================================================
// ERROR TYPES
// ============================================================================

export class StateManagementError extends Error {
  constructor(message: string, public code: string, public context?: any) {
    super(message);
    this.name = 'StateManagementError';
  }
}

export class ScenarioPredictionError extends StateManagementError {
  public tool: string;
  
  constructor(message: string, tool: string, context?: any) {
    super(message, 'SCENARIO_PREDICTION_ERROR', context);
    this.name = 'ScenarioPredictionError';
    this.tool = tool;
  }
}

export class ValidatorIntegrationError extends StateManagementError {
  public validationResult: ValidationResult;
  
  constructor(message: string, validationResult: ValidationResult, context?: any) {
    super(message, 'VALIDATOR_INTEGRATION_ERROR', context);
    this.name = 'ValidatorIntegrationError';
    this.validationResult = validationResult;
  }
}
