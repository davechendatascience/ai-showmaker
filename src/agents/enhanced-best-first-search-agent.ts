import { HTTPMCPClient } from '../mcp/http-mcp-client';
import { SessionManager } from '../core/session-manager';
import { LongTermMemorySystem } from '../core/agentic-memory';
import { BaseLanguageModel } from '@langchain/core/language_models/base';
import { OpenAILLM } from '../llm/openai-llm';
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

export class EnhancedBestFirstSearchAgent {
  private mcpClient: HTTPMCPClient;
  private llm: BaseLanguageModel;
  private sessionManager: SessionManager;
  private longTermMemory: LongTermMemorySystem;
  private validator: ValidatorAgent;
  
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
      minConfidence: Number(process.env['BFS_VALIDATOR_CONF'] || 0.7),
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
    
    // Create a separate, lighter LLM for memory operations to avoid circular dependency
    // Use the same LLM if no separate API key is available
    const memoryLLM = this.createMemoryLLM();
    
    this.longTermMemory = new LongTermMemorySystem(memoryLLM);
    this.validator = new ValidatorAgent(this.llm);
    
    // Initialize state
    this.state = this.initializeState();
  }

  /**
   * Create a memory LLM, falling back to the main LLM if no separate API key is available
   */
  private createMemoryLLM(): BaseLanguageModel {
    const apiKey = process.env['OPENAI_KEY'] || process.env['OPENAI_API_KEY'];
    
    if (apiKey && apiKey.trim() !== '') {
      try {
        // Create a separate, lighter LLM for memory operations
        return new OpenAILLM({
          apiKey: apiKey,
          model: 'gpt-3.5-turbo', // Lighter model for memory operations
          temperature: 0.1, // Lower temperature for more consistent memory operations
          maxTokens: 1000
        });
      } catch (error) {
        console.warn('Failed to create separate memory LLM, using main LLM:', error);
        return this.llm;
      }
    } else {
      console.warn('No OpenAI API key found for memory LLM, using main LLM');
      return this.llm;
    }
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

  async executeTask(task: string, sessionId: string): Promise<string> {
    try {
      this.sessionManager.addMessage(sessionId, { role: 'user', content: task });
    } catch {}

    // Initialize state for this task
    this.state = this.initializeState();
    this.state.task = task;
    this.state.sessionId = sessionId;

    const tools = this.mcpClient.getTools().map(t => ({ 
      name: t.name, 
      description: t.description, 
      schema: t.schema 
    }));

    // Generate complete plan tree upfront for efficiency
    console.log(`[EnhancedBFS] ===== TASK INITIALIZATION =====`);
    console.log(`[EnhancedBFS] Task: "${task}"`);
    console.log(`[EnhancedBFS] Available Tools: ${tools.length}`);
    console.log(`[EnhancedBFS] Configuration: beamWidth=${this.config.beamWidth}, maxIterations=${this.config.maxIterations}`);
    console.log(`[EnhancedBFS] Validator: cooldown=${this.config.validator.cooldown}, minConfidence=${this.config.validator.minConfidence}`);
    
    console.log(`[EnhancedBFS] Generating initial plans...`);
    const planStartTime = Date.now();
    const initialPlans = await this.proposePlansWithScenarios(task, tools, this.state.scratchpad, this.config.beamWidth, 0);
    const planTime = Date.now() - planStartTime;
    console.log(`[EnhancedBFS] Generated ${initialPlans.length} initial plans in ${planTime}ms`);
    
    const scoreStartTime = Date.now();
    const scoredPlans = await this.scorePlansWithValidatorIntegration(task, this.state.scratchpad, initialPlans);
    const scoreTime = Date.now() - scoreStartTime;
    console.log(`[EnhancedBFS] Scored initial plans with validator integration in ${scoreTime}ms`);
    
    this.sortFrontier(scoredPlans);
    this.state.frontier = scoredPlans;
    
    console.log(`[EnhancedBFS] Initial Plan Ranking:`);
    this.state.frontier.slice(0, 3).forEach((plan, idx) => {
      console.log(`  ${idx + 1}. ${plan.action} (score: ${plan.score?.toFixed(2)}, tool: ${plan.tool || 'none'})`);
    });
    console.log(`[EnhancedBFS] ===== STARTING SEARCH =====\n`);

    let lastEvidenceIter = -Infinity;

    for (let iter = 0; iter < this.config.maxIterations; iter++) {
      this.state.iteration = iter;
      
      if (this.state.frontier.length === 0) break;
      
      const node = this.state.frontier.shift()!;
      console.log(`\n[EnhancedBFS] ===== ITERATION ${iter + 1} =====`);
      console.log(`[EnhancedBFS] Selected Plan: ${node.action}`);
      console.log(`[EnhancedBFS] Plan Score: ${node.score?.toFixed(2)}`);
      console.log(`[EnhancedBFS] Tool: ${node.tool || 'none'}`);
      console.log(`[EnhancedBFS] Predicted Scenarios: ${node.scenarios.length}`);
      console.log(`[EnhancedBFS] Plan Reasoning: ${node.reasoning}`);
      
      // Log plan selection reasoning
      if (!node.tool) {
        console.log(`[EnhancedBFS] ⚠️ Selected no-op plan: ${node.action} (score: ${node.score?.toFixed(2)})`);
      } else {
        console.log(`[EnhancedBFS] ✅ Selected tool plan: ${node.action} (${node.tool}, score: ${node.score?.toFixed(2)})`);
      }
      
      // Show scenario predictions
      if (node.scenarios.length > 0) {
        console.log(`[EnhancedBFS] Scenario Predictions:`);
        node.scenarios.forEach((scenario, idx) => {
          console.log(`  ${idx + 1}. ${scenario.type} (${(scenario.probability * 100).toFixed(1)}%)`);
        });
      }

      // Execute with scenario-aware handling
      console.log(`[EnhancedBFS] Executing plan with scenario-aware handling...`);
      const executionResult = await this.executeWithScenarioHandling(node, task, tools);
      
      // Update state with execution result
      this.updateStateWithExecution(executionResult, node);
      console.log(`[EnhancedBFS] Execution Result:`);
      console.log(`  Success: ${executionResult.success}`);
      console.log(`  Tool: ${executionResult.tool || 'none'}`);
      console.log(`  Result: ${executionResult.observation || 'none'}`);
      console.log(`  Actual Scenario: ${executionResult.actualScenario?.type || 'unknown'}`);
      console.log(`  Execution Time: ${executionResult.executionTime?.toFixed(3)}s`);
      
      // Show scenario outcome analysis
      if (executionResult.actualScenario) {
        const predicted = node.scenarios.find(s => s.type === executionResult.actualScenario?.type);
        if (predicted) {
          console.log(`[EnhancedBFS] Scenario Analysis: Predicted ${(predicted.probability * 100).toFixed(1)}% → Actual ${executionResult.actualScenario.type}`);
        } else {
          console.log(`[EnhancedBFS] Scenario Analysis: Unexpected scenario ${executionResult.actualScenario.type} (not predicted)`);
        }
      }
      
      // Update evidence tracking - track any successful execution
      if (executionResult.success) {
        lastEvidenceIter = iter;
        console.log(`[EnhancedBFS] Evidence updated: lastEvidenceIter=${lastEvidenceIter}`);
      }
      
      // BFS Goal State Detection - check if we've reached the goal
      const isGoalReached = await this.isGoalStateReached(task, this.state.scratchpad);
      
      if (isGoalReached) {
        console.log(`[EnhancedBFS] ✅ GOAL STATE REACHED - Task complete!`);
        return await this.renderAnswer(task, this.state.scratchpad);
      }
      

      // Generate next plans with enhanced scenario prediction
      console.log(`[EnhancedBFS] Plan Generation Phase:`);
      console.log(`  Generating ${this.config.beamWidth} new plans at depth ${node.depth + 1}...`);
      
      const children = await this.proposePlansWithScenarios(task, tools, this.state.scratchpad, this.config.beamWidth, node.depth + 1);
      console.log(`  Generated ${children.length} candidate plans`);
      
      const scored = await this.scorePlansWithValidatorIntegration(task, this.state.scratchpad, children);
      console.log(`  Scored plans with validator integration`);
      
      // Show top plans
      if (scored.length > 0) {
        console.log(`[EnhancedBFS] Top Plans for Next Iteration:`);
        scored.slice(0, 3).forEach((plan, idx) => {
          console.log(`  ${idx + 1}. ${plan.action} (score: ${plan.score?.toFixed(2)}, tool: ${plan.tool || 'none'})`);
        });
      }
      
      this.state.frontier.push(...scored);
      this.sortFrontier(this.state.frontier);
      
      // Update metrics
      this.updateMetrics(executionResult);
      
      // Log current metrics with confidence scores
      const mainAgentConfidence = node.score || 0;
      const validatorConfidence = this.state.validatorState.lastValidation?.confidence || 0;
      const lastValidation = this.state.validatorState.lastValidation;
      console.log(`[EnhancedBFS] Iteration Summary:`);
      console.log(`  Total Iterations: ${this.state.metrics.totalIterations}`);
      console.log(`  Success Rate: ${(this.state.metrics.successRate * 100).toFixed(1)}%`);
      console.log(`  Frontier Size: ${this.state.frontier.length}`);
      console.log(`  Main Agent Confidence: ${mainAgentConfidence.toFixed(2)}`);
      console.log(`  Validator Confidence: ${validatorConfidence.toFixed(2)}`);
      console.log(`  Validator Interactions: ${this.state.metrics.validatorInteractions}`);
      if (lastValidation) {
        console.log(`  Last Validation: ${lastValidation.completed ? 'COMPLETED' : 'INCOMPLETE'} (${lastValidation.confidence.toFixed(2)})`);
        if (lastValidation.issues && lastValidation.issues.length > 0) {
          console.log(`  Outstanding Issues: ${lastValidation.issues.join(', ')}`);
        }
        if (lastValidation.suggested_next_actions && lastValidation.suggested_next_actions.length > 0) {
          console.log(`  Pending Actions: ${lastValidation.suggested_next_actions.join(', ')}`);
        }
      }
      
      // Save state snapshot
      this.saveStateSnapshot();
    }

    // Task completed or timed out
    console.log(`\n[EnhancedBFS] ===== TASK COMPLETION =====`);
    console.log(`[EnhancedBFS] Final Status: ${this.state.frontier.length === 0 ? 'No more plans' : 'Max iterations reached'}`);
    console.log(`[EnhancedBFS] Total Iterations: ${this.state.metrics.totalIterations}`);
    console.log(`[EnhancedBFS] Final Success Rate: ${(this.state.metrics.successRate * 100).toFixed(1)}%`);
    console.log(`[EnhancedBFS] Validator Interactions: ${this.state.metrics.validatorInteractions}`);
    console.log(`[EnhancedBFS] Final Validator Confidence: ${this.state.validatorState.lastValidation?.confidence?.toFixed(2) || 'N/A'}`);
    console.log(`[EnhancedBFS] ================================\n`);
    
    // Learn from this task execution
    const finalOutcome = this.determineTaskOutcome();
    console.log(`[EnhancedBFS] Learning from task with outcome: ${finalOutcome}`);
    await this.longTermMemory.learnFromTask(
      task,
      finalOutcome,
      JSON.stringify(this.state.scratchpad),
      this.detectTaskType(task)
    );

    return await this.renderAnswer(task, this.state.scratchpad);
  }

  private async proposePlansWithScenarios(
    task: string, 
    tools: any[], 
    scratchpad: ExecutionEntry[], 
    k: number, 
    depth: number
  ): Promise<PlanNode[]> {
    // Get memory context for this task
    const taskType = this.detectTaskType(task);
    const recentFailures = this.extractRecentFailures(scratchpad);
    console.log(`[EnhancedBFS] Generating memory context for task type: ${taskType}, recent failures: ${recentFailures.join(', ')}`);
    
    const memoryContext = await this.longTermMemory.generateMemoryContext(
      `Task: ${taskType}, Step: ${scratchpad[scratchpad.length - 1]?.step || 'initial'}, Failures: ${recentFailures.join(', ')}`,
      'task_execution',
      'general',
      ['python', 'leetcode', 'execution', 'debugging', 'workspace']
    );
    
    console.log(`[EnhancedBFS] Memory context received: ${memoryContext.substring(0, 200)}...`);

    const sys = new SystemMessage(`# Role
You are a concrete action planner that proposes specific tool executions to solve the task.
Propose the next ${k} concrete actions using actual available tools.
${memoryContext}

CRITICAL REQUIREMENTS:
- Use ONLY actual tool names from the available tools list
- Each action must specify exact tool parameters
- Focus on actions that directly advance the task
- Avoid abstract labels like "set_variable", "init_workspace", etc.
- Prefer tools that produce verifiable results

IMPORTANT TOOL PARAMETERS:
- write_file: Use "filename" (NOT "file_path" or "path")
- read_file: Use "filename" (NOT "file_path" or "path")
- execute_command: Use "command" parameter
- search_web: Use "query" parameter

CODE GENERATION RULES:
- When writing code files, provide ACTUAL working implementations, not placeholders
- For LeetCode problems, include the complete solution with proper logic
- For Python files, include proper function definitions and return statements
- Avoid writing "pass" or placeholder comments - write real code
- Include test cases or main execution block to produce output when run
- For LeetCode problems, add test cases that print results: "print(function_name(test_input))"

OUTPUT CAPTURE RULES:
- To capture command output, use shell redirection: "command > output.txt"
- To test Python code, use: "python3 script.py > output.txt 2>&1"
- To run with input, use: "echo 'input' | python3 script.py > output.txt"
- Always capture both stdout and stderr for complete results
- After execution, read the output file to verify results
- If output file doesn't exist, the command likely failed - check for errors first
- If Python execution fails with Exit Code 2, there's a syntax error - check the code

WORKSPACE AWARENESS RULES:
- Files are written to the remote workspace directory
- Always use full paths when executing commands: "python3 /home/ec2-user/workspace/solution.py"
- Or change to workspace directory first: "cd /home/ec2-user/workspace && python3 solution.py"
- Check current directory with "pwd" if unsure about file locations

EXECUTION SUCCESS RULES:
- When Python execution returns Exit Code 0, the code ran successfully
- After successful execution, ALWAYS read the output file to show validator evidence
- Don't rewrite files after successful execution - read output instead
- If Exit Code 0 but no output, the code ran but produced no output (check the code)

AGENTIC MEMORY GUIDANCE:
- Use the provided memory context to guide your decisions
- Learn from successful and failed executions
- Apply patterns from similar past experiences
- The memory system will dynamically provide relevant guidance

DEBUGGING RULES:
- If Python code fails to execute, first check for syntax errors
- Use "python3 -m py_compile script.py" to check syntax
- If syntax is OK, run without redirection to see error messages
- Always verify code syntax before attempting execution

ERROR HANDLING RULES:
- If read_file fails with "file not found", the previous command likely failed
- Check command execution results before trying to read output files
- Use "ls" or "cat" commands to verify files exist before reading them
- Always check exit codes: 0 = success, non-zero = failure

Available Tools: ${tools.map(t => t.name).join(', ')}`);

    const historyFmt = scratchpad.slice(-5).map((e, i) => 
      `${i + 1}. step=${e.step} tool=${e.tool || 'none'} success=${e.success} -> ${e.observation.slice(0, 160)}`
    ).join('\n');
    
    const toolNames = tools.map(t => t.name).join(', ');
    const hints = this.state.validatorState.hints.map((h, i) => `${i + 1}. ${h}`).join('\n');
    
    // Get memory warnings to prevent known failure patterns
    const memoryWarnings = await this.getMemoryWarnings(task, tools);
    
    const human = new HumanMessage(`Task: ${task}
Available Tools: ${toolNames}

${memoryWarnings}

IMPORTANT PLANNING GUIDELINES:
- If you need information you don't have (like URLs, names, etc.), use search_web FIRST
- Don't attempt actions that require missing parameters
- Consider what information is needed before what actions to take
- Use tools in logical order: gather info → plan → execute
- Always provide ALL required parameters for tools
- Check if directories/files exist before trying to access them

Recent Trace:
${historyFmt || 'None'}

Validator Hints:
${hints || 'None'}

Output EXACTLY ${k} proposal blocks with this format:
PROPOSAL:
ACTION: <specific action using actual tool name>
TOOL: <exact tool name from available tools>
INPUTS: <valid JSON with tool parameters>
REASONING: <why this specific tool execution is needed next>
SCENARIOS: <comma-separated list of likely scenarios: SUCCESS, PARTIAL_SUCCESS, VALIDATION_ERROR, CONNECTION_ERROR, TIMEOUT, etc.>

EXAMPLE for "what is 2+2?":
PROPOSAL:
ACTION: Calculate 2+2 using the calculate tool
TOOL: calculate
INPUTS: {"expression": "2+2"}
REASONING: This directly solves the arithmetic question
SCENARIOS: SUCCESS,VALIDATION_ERROR,TIMEOUT

EXAMPLE for "write a Python file with test cases":
PROPOSAL:
ACTION: Write Python solution code with test cases to a file
TOOL: write_file
INPUTS: {"filename": "solution.py", "content": "def solve(nums):\n    return sum(nums)\n\n# Test the solution\nif __name__ == '__main__':\n    test_input = [1, 2, 3, 4, 5]\n    result = solve(test_input)\n    print(f'Input: {test_input}')\n    print(f'Output: {result}')"}
REASONING: This creates the actual code file with test cases that produce output
SCENARIOS: SUCCESS,VALIDATION_ERROR,TIMEOUT

EXAMPLE for "test Python code with output capture":
PROPOSAL:
ACTION: Execute Python code and capture output to verify it works
TOOL: execute_command
INPUTS: {"command": "cd /home/ec2-user/workspace && python3 solution.py > output.txt 2>&1"}
REASONING: This runs the code from the workspace directory and captures all output for verification
SCENARIOS: SUCCESS,VALIDATION_ERROR,TIMEOUT

EXAMPLE for "read captured output":
PROPOSAL:
ACTION: Read the captured output to verify the solution works
TOOL: read_file
INPUTS: {"filename": "output.txt"}
REASONING: This verifies the code execution produced the expected results
SCENARIOS: SUCCESS,VALIDATION_ERROR,TIMEOUT

EXAMPLE for "develop a web app" (showing information gathering first):
PROPOSAL:
ACTION: Search for web app templates and repositories to understand what's available
TOOL: search_web
INPUTS: {"query": "Flask web app templates GitHub repositories"}
REASONING: Need to find available web app templates before attempting to clone or create one
SCENARIOS: SUCCESS,CONNECTION_ERROR,TIMEOUT

EXAMPLE for "clone repository" (showing proper parameter usage):
PROPOSAL:
ACTION: Clone the Flask web app template repository found in previous search
TOOL: clone_repository
INPUTS: {"repo_url": "https://github.com/example/flask-template.git", "repo_name": "flask-template"}
REASONING: Now that we have a specific repository URL from the search, we can clone it
SCENARIOS: SUCCESS,VALIDATION_ERROR,TIMEOUT

EXAMPLE for "debug Python syntax error":
PROPOSAL:
ACTION: Check Python code syntax before execution
TOOL: execute_command
INPUTS: {"command": "cd /home/ec2-user/workspace && python3 -m py_compile solution.py"}
REASONING: This checks for syntax errors before attempting to run the code
SCENARIOS: SUCCESS,VALIDATION_ERROR,TIMEOUT

EXAMPLE for "run Python without redirection to see errors":
PROPOSAL:
ACTION: Run Python code without redirection to see error messages
TOOL: execute_command
INPUTS: {"command": "cd /home/ec2-user/workspace && python3 solution.py"}
REASONING: This shows error messages when code fails to execute
SCENARIOS: SUCCESS,VALIDATION_ERROR,TIMEOUT

EXAMPLE for "read output after successful execution":
PROPOSAL:
ACTION: Read the captured output to verify the solution works
TOOL: read_file
INPUTS: {"filename": "output.txt"}
REASONING: After successful execution (Exit Code 0), read output to show validator evidence
SCENARIOS: SUCCESS,VALIDATION_ERROR,TIMEOUT`);

    const llmStartTime = Date.now();
    const res = await this.llm.invoke([sys, human]);
    const llmTime = Date.now() - llmStartTime;
    console.log(`[EnhancedBFS] LLM plan generation took ${llmTime}ms`);
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
      
      if (action) {
        const planId = this.generatePlanId();
        
        // Use the explicitly specified tool, or fall back to prediction
        const tool = toolName || this.predictTool(task, tools, { action, inputs });
        
        const plan: PlanNode = {
          id: planId,
          action,
          inputs,
          reasoning,
          depth,
          score: 0.5, // Will be updated by scoring
          tool: tool || undefined,
          scenarios: await this.predictScenarios(tool || '', inputs, scenariosStr),
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
    
    // Avoid summarize on first step
    if (depth === 0) {
      out = out.filter(p => !/^(summarize|synthesize_answer|finalize|report)$/i.test(p.action));
    }
    
    // Fallback if none
    if (out.length === 0) {
        const fallbackPlan: PlanNode = {
          id: this.generatePlanId(),
          action: 'gather_info',
          inputs: { query: task },
          reasoning: 'Collect information relevant to the task',
          depth,
          score: 0.5,
          tool: undefined,
          scenarios: await this.predictScenarios('search_web', { query: task }, 'SUCCESS,CONNECTION_ERROR,TIMEOUT'),
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
            tags: ['fallback'],
            priority: 'MEDIUM'
          }
        };
      out.push(fallbackPlan);
    }
    
    return out;
  }

  private async predictScenarios(tool: string, _inputs: any, scenariosStr: string): Promise<ToolScenario[]> {
    if (!this.config.scenarioPrediction.enabled || !tool) {
      return [];
    }

    // Check cache first
    const cacheKey = `${tool}:${JSON.stringify(_inputs)}`;
    const cached = this.scenarioCache.get(cacheKey);
    if (cached && (Date.now() - cached.timestamp) < this.config.scenarioPrediction.cacheDuration) {
      return cached.scenarios;
    }

    const scenarios: ToolScenario[] = [];
    const scenarioTypes = scenariosStr.split(',').map(s => s.trim().toUpperCase() as ScenarioType);
    
    // Generate scenarios based on tool type and common patterns
    for (const scenarioType of scenarioTypes) {
      const scenario = await this.generateScenario(tool, _inputs, scenarioType);
      if (scenario) {
        scenarios.push(scenario);
      }
    }

    // Cache the prediction
    const prediction: ScenarioPrediction = {
      planId: '', // Will be set when used
      tool,
      scenarios,
      confidence: this.calculatePredictionConfidence(tool, scenarios),
      timestamp: Date.now()
    };
    
    this.scenarioCache.set(cacheKey, prediction);
    
    return scenarios;
  }

  private async generateScenario(_tool: string, _inputs: any, type: ScenarioType): Promise<ToolScenario | null> {
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
    // This would be enhanced with actual system state checking
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

  // Helper methods for scenario generation
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
    // Simple confidence calculation based on scenario diversity and tool familiarity
    const diversity = new Set(scenarios.map(s => s.type)).size / scenarios.length;
    const avgProbability = scenarios.reduce((sum, s) => sum + s.probability, 0) / scenarios.length;
    return (diversity + avgProbability) / 2;
  }

  // Continue with remaining methods...
  private async executeWithScenarioHandling(node: PlanNode, task: string, tools: any[]): Promise<ExecutionEntry> {
    const startTime = Date.now();
    
    try {
      // Resolve plan to concrete tool
      const resolved = this.resolvePlan(task, tools, node, this.state.scratchpad);
      
      let observation = { success: true, text: 'No-op', completionSignal: false };
      let actualScenario: ToolScenario | undefined;
      
      if (resolved.tool) {
        // Execute tool
        observation = await this.execute(resolved.tool, resolved.inputs);
        
        // Determine which scenario actually occurred
        actualScenario = this.determineActualScenario(observation, node.scenarios);
        
        // Learn from outcome if enabled
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
      
      // Update plan metadata
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

  private determineActualScenario(observation: any, predictedScenarios: ToolScenario[]): ToolScenario | undefined {
    // Determine which predicted scenario best matches the actual outcome
    const success = observation.success;
    const text = observation.text.toLowerCase();
    
    if (success) {
      return predictedScenarios.find(s => s.type === 'SUCCESS') || 
             predictedScenarios.find(s => s.type === 'PARTIAL_SUCCESS');
    }
    
    // Match error scenarios
    if (text.includes('validation')) return predictedScenarios.find(s => s.type === 'VALIDATION_ERROR');
    if (text.includes('connection') || text.includes('network')) return predictedScenarios.find(s => s.type === 'CONNECTION_ERROR');
    if (text.includes('timeout')) return predictedScenarios.find(s => s.type === 'TIMEOUT');
    if (text.includes('not found')) return predictedScenarios.find(s => s.type === 'TOOL_NOT_FOUND');
    if (text.includes('rate limit')) return predictedScenarios.find(s => s.type === 'RATE_LIMITED');
    
    return predictedScenarios.find(s => s.type === 'UNKNOWN_ERROR');
  }

  private learnFromOutcome(node: PlanNode, actualScenario: ToolScenario): void {
    // Update scenario probabilities based on actual outcomes
    // This is a simplified learning mechanism
    const cacheKey = `${node.tool || 'unknown'}:${JSON.stringify(node.inputs)}`;
    const cached = this.scenarioCache.get(cacheKey);
    
    if (cached) {
      // Adjust probabilities based on actual outcome
      cached.scenarios.forEach(scenario => {
        if (scenario.type === actualScenario.type) {
          scenario.probability = Math.min(1, scenario.probability + 0.1);
        } else {
          scenario.probability = Math.max(0, scenario.probability - 0.05);
        }
      });
      
      // Update confidence
      cached.confidence = this.calculatePredictionConfidence(node.tool || '', cached.scenarios);
    }
  }

  // Continue with remaining methods in next part...
  private async scorePlansWithValidatorIntegration(
    task: string, 
    scratchpad: ExecutionEntry[], 
    plans: PlanNode[]
  ): Promise<PlanNode[]> {
    // Base scoring
    const scored = await this.scorePlans(task, scratchpad, plans);
    
    // Apply validator integration
    for (const plan of scored) {
      plan.validatorIntegration = this.calculateValidatorIntegration(plan);
      plan.score = Math.min(1, plan.score + plan.validatorIntegration.scoreModifier);
    }
    
    return scored;
  }

  private calculateValidatorIntegration(plan: PlanNode): any {
    const hints = this.state.validatorState.hints;
    const lastValidation = this.state.validatorState.lastValidation;
    
    let scoreModifier = 0;
    let alignsWithHints = false;
    let confidenceImpact = 0;
    let addressesIssues = false;
    let suggestedImprovements: string[] = [];
    
    // Check alignment with hints
    if (hints.length > 0) {
      const actionLower = plan.action.toLowerCase();
      alignsWithHints = hints.some(hint => 
        actionLower.includes(hint.toLowerCase()) || hint.toLowerCase().includes(actionLower)
      );
      
      if (alignsWithHints) {
        scoreModifier += this.config.validator.hintBoost;
      }
    }
    
    // Check if addresses validator issues
    if (lastValidation?.issues) {
      addressesIssues = lastValidation.issues.some(issue => 
        plan.action.toLowerCase().includes(issue.toLowerCase()) ||
        plan.reasoning.toLowerCase().includes(issue.toLowerCase())
      );
      
      if (addressesIssues) {
        scoreModifier += 0.2;
      }
    }
    
    // Special handling for test_example and implement_code
    const actionLower = plan.action.toLowerCase();
    if (hints.some(h => h.toLowerCase().includes('test')) && actionLower.includes('test')) {
      scoreModifier += this.config.validator.specialHintBoost;
    }
    if (hints.some(h => h.toLowerCase().includes('code')) && actionLower.includes('implement')) {
      scoreModifier += this.config.validator.specialHintBoost;
    }
    
    return {
      scoreModifier,
      alignsWithHints,
      confidenceImpact,
      addressesIssues,
      suggestedImprovements
    };
  }

  // LLM-based intelligent plan scoring with context-aware adjustments
  private async scorePlans(task: string, scratchpad: ExecutionEntry[], plans: PlanNode[]): Promise<PlanNode[]> {
    // Get LLM-based scores with context analysis
    const scoredPlans = await this.getLLMContextualScores(task, scratchpad, plans);
    
    // Log scoring results
    for (const plan of scoredPlans) {
      const toolInfo = plan.tool ? ` (${plan.tool})` : ' (no-op)';
      console.log(`[EnhancedBFS] LLM scored "${plan.action}"${toolInfo} as ${plan.score?.toFixed(3)}`);
    }
    
    return scoredPlans;
  }

  /**
   * Get LLM-based contextual scores that intelligently handle no-op vs tool plans
   */
  private async getLLMContextualScores(
    task: string,
    scratchpad: ExecutionEntry[],
    plans: PlanNode[]
  ): Promise<PlanNode[]> {
    const recentActions = scratchpad.slice(-5).map(e => e.step).join(', ');
    const planDescriptions = plans.map((p, i) => 
      `${i + 1}. ${p.action}${p.tool ? ` (tool: ${p.tool})` : ' (no-op)'} - ${p.reasoning}`
    ).join('\n');

    const prompt = `You are an expert at evaluating action plans for task completion. Analyze each plan's utility in the current context.

TASK: "${task}"

RECENT ACTIONS: ${recentActions || 'None'}

AVAILABLE PLANS:
${planDescriptions}

For each plan, consider:
1. **Direct Task Relevance**: Does this action directly help complete the task?
2. **Information Value**: Does this action provide NEW information not already available?
3. **Context Appropriateness**: Is this action appropriate given recent actions?
4. **No-op vs Tool Analysis**: 
   - No-op actions can be GOOD if they're logical state management (e.g., storing results, cleanup)
   - No-op actions are BAD if they're redundant or don't add value
   - Tool actions are GOOD if they provide new information or directly solve the task
   - Tool actions can be BAD if they're redundant with recent actions

Rate each plan's utility on a scale of 0.0 to 1.0:
- 1.0: Perfectly addresses the task or provides critical new information
- 0.8-0.9: Strongly contributes to task completion
- 0.6-0.7: Moderately useful, provides some value
- 0.4-0.5: Somewhat relevant but may be redundant
- 0.2-0.3: Low utility, likely redundant or unhelpful
- 0.0-0.1: Useless, counterproductive, or highly redundant

Examples of GOOD no-op actions:
- Storing calculation results when task asks for calculation
- Cleanup after task completion
- Organizing data for presentation

Examples of BAD no-op actions:
- Repeatedly checking the same information
- Redundant state management
- Actions that don't advance the task

Respond with ONLY the scores in order, separated by newlines:
0.8
0.3
0.9
...`;

    try {
      const response = await this.llm.invoke(prompt);
      // Handle different response formats from LLM
      const responseText = typeof response === 'string' ? response : response.content || response.text || String(response);
      const scores = responseText.trim().split('\n').map((s: string) => parseFloat(s.trim())).filter((s: number) => !isNaN(s));
      
      // Apply scores to plans
      plans.forEach((plan, i) => {
        if (scores[i] !== undefined) {
          plan.score = Math.max(0.0, Math.min(1.0, scores[i]));
        } else {
          // Fallback scoring if LLM response is malformed
          plan.score = plan.tool ? 0.6 : 0.2;
        }
      });
      
      console.log(`[EnhancedBFS] LLM contextual analysis completed for ${plans.length} plans`);
    } catch (error) {
      console.warn(`[EnhancedBFS] LLM scoring failed, using fallback: ${error}`);
      // Fallback to rule-based scoring
      plans.forEach(plan => {
        if (!plan.tool) {
          plan.score = 0.2; // Moderate penalty for no-op
        } else {
          plan.score = 0.7; // Good score for tool plans
        }
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
    // Simplified tool prediction - would be enhanced
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

  private resolvePlan(_task: string, _tools: any[], plan: PlanNode, _scratchpad: ExecutionEntry[]): { tool?: string | undefined; inputs: any } {
    // Simplified plan resolution - would be enhanced
    return {
      tool: plan.tool,
      inputs: plan.inputs
    };
  }

  private async execute(tool: string, params: any): Promise<{ success: boolean; text: string; completionSignal: boolean; meta?: any }> {
    // Use existing MCP client execution
    try {
      const result = await this.mcpClient.executeTool(tool, params || {});
      const ok = typeof result?.success === 'boolean' ? Boolean(result.success) : true;
      const blob = JSON.stringify(result || '').slice(0, 800);
      return { success: ok, text: blob, completionSignal: false, meta: result };
    } catch (e: any) {
      return { success: false, text: String(e || 'execution error'), completionSignal: false };
    }
  }

  private updateStateWithExecution(execution: ExecutionEntry, _node: PlanNode): void {
    this.state.scratchpad.push(execution);
    this.state.metrics.plansExecuted++;
    
    // Learn from this execution immediately
    this.learnFromExecution(execution);
  }

  /**
   * Learn from individual execution results
   */
  private async learnFromExecution(execution: ExecutionEntry): Promise<void> {
    try {
      // Intelligently analyze the observation content to determine actual outcome
      const actualOutcome = this.analyzeExecutionOutcome(execution);
      const evidence = `Tool: ${execution.tool}, Result: ${execution.observation}, Tool Success: ${execution.success}, Actual Outcome: ${actualOutcome}`;
      
      console.log(`[EnhancedBFS] Learning from execution: ${actualOutcome} - ${execution.tool} (tool success: ${execution.success})`);
      if (actualOutcome !== (execution.success ? 'success' : 'failure')) {
        console.log(`[EnhancedBFS] ⚠️  Outcome mismatch detected! Tool reported success=${execution.success} but actual outcome=${actualOutcome}`);
        console.log(`[EnhancedBFS] Observation: ${execution.observation?.substring(0, 200)}...`);
      }
      
      await this.longTermMemory.learnFromTask(
        `Execute ${execution.tool}`,
        actualOutcome,
        evidence,
        'tool_execution'
      );
    } catch (error) {
      console.warn(`[EnhancedBFS] Failed to learn from execution:`, error);
    }
  }

  /**
   * Intelligently analyze execution observation to determine actual success/failure
   * This addresses the issue where tools report success=true but the underlying task failed
   */
  private analyzeExecutionOutcome(execution: ExecutionEntry): 'success' | 'failure' | 'partial' {
    const observation = execution.observation || '';
    const tool = execution.tool || '';
    
    // If tool execution failed, it's definitely a failure
    if (!execution.success) {
      return 'failure';
    }
    
    // Analyze observation content for failure indicators
    const failureIndicators = [
      'Exit Code: 1',
      'Exit Code: 2', 
      'Exit Code: 3',
      'Exit Code: 4',
      'Exit Code: 5',
      'SyntaxError',
      'NameError',
      'TypeError',
      'ValueError',
      'FileNotFoundError',
      'No such file or directory',
      'can\'t open file',
      'Permission denied',
      'Connection refused',
      'timeout',
      'error:',
      'Error:',
      'ERROR:',
      'failed',
      'Failed',
      'FAILED'
    ];
    
    const successIndicators = [
      'Exit Code: 0',
      'SUCCESS',
      'Success',
      'success',
      'completed',
      'Completed',
      'COMPLETED'
    ];
    
    // Check for explicit failure indicators
    const hasFailureIndicator = failureIndicators.some(indicator => 
      observation.toLowerCase().includes(indicator.toLowerCase())
    );
    
    // Check for explicit success indicators
    const hasSuccessIndicator = successIndicators.some(indicator => 
      observation.toLowerCase().includes(indicator.toLowerCase())
    );
    
    // Special handling for specific tools
    if (tool === 'execute_command') {
      // For execute_command, look for exit codes and error messages
      if (hasFailureIndicator) {
        return 'failure';
      }
      if (hasSuccessIndicator) {
        return 'success';
      }
      // If no clear indicators, check if there's meaningful output
      const hasOutput = observation.trim().length > 0 && 
                       !observation.includes('STDOUT:') && 
                       !observation.includes('STDERR:');
      return hasOutput ? 'success' : 'partial';
    }
    
    if (tool === 'read_file') {
      // For read_file, success means we got file content
      const hasContent = observation.trim().length > 0 && 
                        !observation.includes('File not found') &&
                        !observation.includes('No such file');
      return hasContent ? 'success' : 'failure';
    }
    
    if (tool === 'write_file') {
      // For write_file, success means file was written
      const wasWritten = observation.includes('File written successfully') ||
                        observation.includes('successfully') ||
                        (!observation.includes('error') && !observation.includes('Error'));
      return wasWritten ? 'success' : 'failure';
    }
    
    // Default analysis based on indicators
    if (hasFailureIndicator) {
      return 'failure';
    }
    if (hasSuccessIndicator) {
      return 'success';
    }
    
    // If no clear indicators, consider it partial success
    return 'partial';
  }

  /**
   * Generate memory warnings to prevent known failure patterns
   */
  private async getMemoryWarnings(task: string, tools: any[]): Promise<string> {
    try {
      const toolNames = tools.map(t => t.name).join(', ');
      const warnings = await this.longTermMemory.generateMemoryContext(
        `Task: ${task}, Available Tools: ${toolNames}`,
        'planning',
        'general',
        ['failure', 'debugging', 'parameter', 'validation']
      );
      
      if (warnings && warnings !== 'No relevant memories found....') {
        return `MEMORY WARNINGS (learned from past failures):
${warnings}

CRITICAL: Use these warnings to avoid repeating known failure patterns!`;
      }
      
      return '';
    } catch (error) {
      console.warn('[EnhancedBFS] Failed to generate memory warnings:', error);
      return '';
    }
  }

  /**
   * BFS Goal State Detection using validator
   * This replaces hardcoded validation triggering with proper BFS goal detection
   */
  private async isGoalStateReached(task: string, scratchpad: ExecutionEntry[]): Promise<boolean> {
    try {
      console.log(`[EnhancedBFS] Checking goal state for task: ${task}`);
      const verdict = await this.validator.validate(task, scratchpad);
      
      // Goal reached when validator says task is complete with sufficient confidence
      const isComplete = verdict.completed && verdict.confidence >= this.config.validator.minConfidence;
      
      console.log(`[EnhancedBFS] Goal state check: completed=${verdict.completed}, confidence=${verdict.confidence.toFixed(2)}, goal_reached=${isComplete}`);
      
      if (isComplete) {
        console.log(`[EnhancedBFS] ✅ GOAL STATE REACHED - Task complete with confidence ${verdict.confidence.toFixed(2)}`);
      }
      
      return isComplete;
    } catch (error) {
      console.error('[EnhancedBFS] Goal state detection failed:', error);
      return false;
    }
  }




  private updateMetrics(_execution: ExecutionEntry): void {
    this.state.metrics.totalIterations++;
    if (_execution.executionTime) {
      const total = this.state.metrics.averageExecutionTime * (this.state.metrics.plansExecuted - 1) + _execution.executionTime;
      this.state.metrics.averageExecutionTime = total / this.state.metrics.plansExecuted;
    }
    
    const successful = this.state.scratchpad.filter(e => e.success).length;
    this.state.metrics.successRate = successful / this.state.scratchpad.length;
  }

  private saveStateSnapshot(): void {
    this.stateHistory.push(JSON.parse(JSON.stringify(this.state)));
  }


  private async renderAnswer(task: string, scratchpad: ExecutionEntry[]): Promise<string> {
    // Enhanced answer rendering with state information
    const sys = new SystemMessage(`# Role
You are the final answer composer with access to enhanced execution state.
Provide a comprehensive answer based on the execution trace and state information.`);

    const trace = scratchpad.map((e, i) => 
      `${i + 1}. step=${e.step} tool=${e.tool || 'none'} success=${e.success} scenario=${e.actualScenario?.type || 'unknown'} -> ${e.observation.slice(0, 200)}`
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
      return `Task: ${task}\n\nExecution completed with ${scratchpad.length} steps.`;
    }
  }

  // Utility methods
  private extractSection(text: string, key: string): string | null {
    const re = new RegExp(`${key}\\s*:\\s*([\\s\\S]*?)(?:\\n[A-Z_]+\\s*:|$)`, 'i');
    const m = text.match(re);
    return m && m[1] ? m[1].trim() : null;
  }

  private generatePlanId(): string {
    return `plan_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateExecutionId(): string {
    return `exec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // Compatibility method
  async executeComplexTask(taskQuery: string, sessionId: string): Promise<string> {
    return this.executeTask(taskQuery, sessionId);
  }

  // State access methods for debugging and monitoring
  getState(): SearchState {
    return this.state;
  }

  getStateHistory(): SearchState[] {
    return this.stateHistory;
  }

  getScenarioCache(): Map<string, ScenarioPrediction> {
    return this.scenarioCache;
  }

  /**
   * Detect task type for memory context
   */
  private detectTaskType(task: string): string {
    const lowerTask = task.toLowerCase();
    if (lowerTask.includes('leetcode') || lowerTask.includes('algorithm') || lowerTask.includes('coding')) {
      return 'leetcode';
    }
    if (lowerTask.includes('calculate') || lowerTask.includes('math') || lowerTask.includes('arithmetic')) {
      return 'calculation';
    }
    if (lowerTask.includes('search') || lowerTask.includes('find') || lowerTask.includes('look up')) {
      return 'web_search';
    }
    if (lowerTask.includes('write') || lowerTask.includes('create') || lowerTask.includes('build')) {
      return 'development';
    }
    return 'general';
  }

  /**
   * Extract recent failures from scratchpad
   */
  private extractRecentFailures(scratchpad: ExecutionEntry[]): string[] {
    return scratchpad
      .slice(-5) // Last 5 entries
      .filter(entry => !entry.success)
      .map(entry => entry.observation || '')
      .filter(obs => obs.length > 0);
  }

  /**
   * Determine final task outcome
   */
  private determineTaskOutcome(): 'success' | 'failure' | 'partial' {
    const recentEntries = this.state.scratchpad.slice(-3);
    const hasSuccess = recentEntries.some(entry => entry.success);
    const hasFailure = recentEntries.some(entry => !entry.success);
    
    if (hasSuccess && !hasFailure) return 'success';
    if (hasFailure && !hasSuccess) return 'failure';
    return 'partial';
  }
}
