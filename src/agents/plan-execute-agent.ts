/**
 * Plan-Execute Agent with Memory
 *
 * Replaces BFS-style frontier search with a plan-first loop:
 * 1) Generate an ordered plan of concrete tool calls.
 * 2) Execute steps sequentially.
 * 3) On failure, replan using completed steps + failure details.
 */
import { HTTPMCPClient } from '../mcp/http-mcp-client';
import { SessionManager } from '../core/session-manager';
import { createRichMemorySystem, RichMemoryManager } from '../core/memory';
import { BaseLanguageModel } from '@langchain/core/language_models/base';
import { HumanMessage, SystemMessage } from '@langchain/core/messages';

type StepStatus = 'pending' | 'running' | 'done' | 'failed';

interface PlannedStep {
  id: string;
  title: string;
  tool?: string;
  inputs: Record<string, any>;
  status: StepStatus;
  attempts: number;
  observation?: string;
}

interface PlanExecuteConfig {
  maxSteps: number;
  maxReplans: number;
  maxAttemptsPerStep: number;
  temperature: number;
}

export class PlanExecuteAgent {
  private mcpClient: HTTPMCPClient;
  private llm: BaseLanguageModel;
  private sessionManager: SessionManager;
  private memory: RichMemoryManager;
  private lastPlan: PlannedStep[] = [];
  private lastTask: string = '';
  private lastReplans = 0;
  private config: PlanExecuteConfig = {
    maxSteps: Number(process.env['PLAN_MAX_STEPS'] || 8),
    maxReplans: Number(process.env['PLAN_MAX_REPLANS'] || 3),
    maxAttemptsPerStep: Number(process.env['PLAN_MAX_ATTEMPTS'] || 2),
    temperature: Number(process.env['PLAN_LLM_TEMPERATURE'] || 0.1)
  };

  constructor(mcpClient: HTTPMCPClient, llm: BaseLanguageModel, sessionManager: SessionManager) {
    this.mcpClient = mcpClient;
    this.llm = llm;
    this.sessionManager = sessionManager;
    this.memory = createRichMemorySystem();
  }

  async executeTask(task: string, sessionId: string): Promise<string> {
    this.sessionManager.addMessage(sessionId, { role: 'user', content: task });
    this.memory.startTaskContext(task);
    const tools = this.mcpClient.getTools().map(t => ({ name: t.name, description: t.description, schema: t.schema }));
    const memoryContext = await this.safeMemoryContext(task);
    this.lastTask = task;

    console.log(`[PlanAgent] Task: ${task}`);
    console.log(`[PlanAgent] Tools available: ${tools.length}`);

    let plan = await this.generatePlan(task, tools, memoryContext);
    let replanCount = 0;
    let cursor = 0;
    this.lastPlan = plan;
    this.lastReplans = 0;

    while (cursor < plan.length) {
      const step = plan[cursor];
      if (!step) break;
      step.status = 'running';
      console.log(`[PlanAgent] Step ${cursor + 1}/${plan.length}: ${step.title}`);

      const execResult = await this.executeStep(step);
      this.recordExecution(step, execResult);

      if (execResult.success) {
        step.status = 'done';
        step.observation = execResult.text;
        cursor += 1;

        const goalReached = await this.isGoalStateReached(task);
        if (goalReached) {
          console.log('[PlanAgent] Goal reached early, stopping execution.');
          break;
        }
      } else {
        // Try automatic fix (e.g., missing parameters)
        const fixed = this.autoFixStep(step, execResult.text);
        if (fixed) {
          console.log(`[PlanAgent] Auto-fixed step "${step.title}" -> retrying with corrected params`);
          step.inputs = fixed.inputs;
          step.title = fixed.title || step.title;
          step.status = 'pending';
          continue;
        }

        step.status = 'failed';
        step.observation = execResult.text;

        if (step.attempts < this.config.maxAttemptsPerStep) {
          console.log(`[PlanAgent] Retry attempt ${step.attempts} for step "${step.title}"`);
          continue;
        }

        if (replanCount >= this.config.maxReplans) {
          console.log('[PlanAgent] Replan limit reached. Stopping.');
          break;
        }

        replanCount += 1;
        this.lastReplans = replanCount;
        const completed = plan.filter(s => s.status === 'done');
        const pending = plan.slice(cursor); // include failed step for context
        const replanned = await this.replan(task, tools, completed, step, pending, memoryContext);
        if (replanned.length === 0 && pending.length > 1) {
          // Fallback: drop failed step, keep the rest so we don’t terminate early
          plan = [...completed, ...pending.slice(1)];
        } else {
          plan = [...completed, ...replanned];
        }
        cursor = completed.length;
        this.lastPlan = plan;
        continue;
      }
    }

    this.memory.completeTask('completed');
    return await this.composeFinalAnswer(task, plan);
  }

  // --- planning ---
  private async generatePlan(task: string, tools: any[], memoryContext: string): Promise<PlannedStep[]> {
    const sys = new SystemMessage(`# Planner
You create a short, ordered plan of concrete tool calls to complete the task.
Return only JSON: [{ "title": "...", "tool": "tool_name", "inputs": { ... } }]
- Use at most ${this.config.maxSteps} steps.
- Every step must specify tool + valid inputs.
- Prefer minimal steps that produce the deliverable quickly.
Memory context and prior work may be referenced but not duplicated.`);

    const human = new HumanMessage(`Task: ${task}
Available tools: ${tools.map(t => t.name).join(', ')}
Memory context (truncated): ${memoryContext.slice(0, 2000)}
Provide the plan now.`); 

    const planJson = await this.invokeForJson(sys, human);
    return this.normalizePlan(planJson);
  }

  private async replan(
    task: string,
    tools: any[],
    completed: PlannedStep[],
    failedStep: PlannedStep,
    pending: PlannedStep[],
    memoryContext: string
  ): Promise<PlannedStep[]> {
    const sys = new SystemMessage(`# Replanner
You update the remaining plan after a failure.
Keep completed steps intact; propose only the remaining steps needed to finish.
Return JSON array of steps as in planning phase.`);

    const summaryCompleted = completed.map(s => `- ${s.title} (ok): ${s.observation || 'done'}`).join('\n') || 'none';
    const summaryPending = pending.map(s => `- ${s.title}`).join('\n') || 'none';

    const human = new HumanMessage(`Task: ${task}
Completed steps:
${summaryCompleted}

Failed step:
- ${failedStep.title}
Reason: ${failedStep.observation || 'no observation'}

Previous remaining steps:
${summaryPending}

Available tools: ${tools.map(t => t.name).join(', ')}
Memory context (truncated): ${memoryContext.slice(0, 2000)}
Return only the new remaining steps (do not repeat completed ones).`);

    const planJson = await this.invokeForJson(sys, human);
    return this.normalizePlan(planJson, completed.length);
  }

  private normalizePlan(raw: any, depthOffset = 0): PlannedStep[] {
    if (!Array.isArray(raw)) return [];
    return raw.slice(0, this.config.maxSteps).map((step, idx) => {
      const inputs = typeof step.inputs === 'object' && step.inputs !== null ? { ...step.inputs } : {};
      // Normalize common parameter mismatches
      if (step.tool === 'clone_repository') {
        if (inputs['repository_url'] && !inputs['repo_url']) {
          inputs['repo_url'] = inputs['repository_url'];
          delete (inputs as any)['repository_url'];
        }
        if (inputs['repo_url'] && !inputs['repo_name']) {
          inputs['repo_name'] = this.deriveRepoName(inputs['repo_url']);
        }
      }
      return {
        id: this.generateId('step'),
        title: String(step.title || step.action || `Step ${idx + 1}`),
        tool: step.tool || step.Tool || step.actionTool,
        inputs,
        status: 'pending' as StepStatus,
        attempts: 0
      };
    }).map((s, i) => ({ ...s, title: `${depthOffset + i + 1}. ${s.title}` }));
  }

  private async invokeForJson(sys: SystemMessage, human: HumanMessage): Promise<any> {
    const res = await this.llm.invoke([sys, human], {
      temperature: this.config.temperature
    } as any);
    const content = typeof res === 'string' ? res : (res as any).content || (res as any).text || '';
    const jsonText = this.extractJson(String(content));
    try {
      return JSON.parse(jsonText);
    } catch {
      return [];
    }
  }

  private extractJson(text: string): string {
    const match = text.match(/```(?:json)?\\s*([\\s\\S]*?)```/i);
    if (match && match[1]) return match[1];
    return text.trim();
  }

  // --- execution ---
  private async executeStep(step: PlannedStep): Promise<{ success: boolean; text: string; meta?: any }> {
    step.attempts += 1;
    if (!step.tool) {
      return { success: true, text: 'No-op step (no tool provided)' };
    }
    const fixedInputs = this.fixParams(step.tool, step.inputs);
    try {
      const result = await this.mcpClient.executeTool(step.tool, fixedInputs);
      const interpreted = this.interpretResult(step.tool, result);
      return interpreted;
    } catch (error: any) {
      return { success: false, text: String(error) };
    }
  }

  private fixParams(tool: string, params: Record<string, any>): Record<string, any> {
    if (tool === 'write_file' && params['file_name'] && !params['filename']) {
      const copy = { ...params, filename: params['file_name'] };
      delete (copy as any)['file_name'];
      return copy;
    }
    if (tool === 'clone_repository' && params['repository_url'] && !params['repo_url']) {
      const copy = { ...params, repo_url: params['repository_url'] };
      delete (copy as any)['repository_url'];
      return copy;
    }
    if (tool === 'clone_repository' && params['repo_url'] && !params['repo_name']) {
      const copy = { ...params, repo_name: this.deriveRepoName(params['repo_url']) };
      return copy;
    }
    return params;
  }

  private recordExecution(step: PlannedStep, result: { success: boolean; text: string; meta?: any }): void {
    const content = `${result.success ? '✅' : '❌'} ${step.title} via ${step.tool || 'none'} -> ${result.text}`;
    this.memory.addEntry({
      type: 'execution',
      content,
      metadata: {
        success: result.success,
        tool: step.tool || 'none',
        attempts: step.attempts,
        confidence: result.success ? 0.9 : 0.3
      }
    });

    if (result.meta && step.tool === 'write_file') {
      const filename = step.inputs['filename'] || step.inputs['file_name'];
      if (filename && typeof result.meta === 'object') {
        this.memory.logSuccessPattern(
          `File created: ${filename}`,
          [step.tool],
          1.0,
          0,
          { filename, content: step.inputs['content'], filePath: filename }
        ).catch(() => {});
      }
    }
  }

  private async isGoalStateReached(task: string): Promise<boolean> {
    try {
      const proof = this.memory.getTaskCompletionProof();
      if (!proof) return false;
      if (proof.hasImplementation && proof.hasSynthesis) return true;
      if (proof.hasFileCreation && proof.hasSynthesis) return true;
      if (task.toLowerCase().includes('answer') && proof.hasSynthesis) return true;
      return false;
    } catch (e) {
      console.log('[PlanAgent] Goal check failed:', e);
      return false;
    }
  }

  private async composeFinalAnswer(task: string, plan: PlannedStep[]): Promise<string> {
    const history = this.memory.queryMemories({ types: ['execution'], maxResults: 50, currentTaskOnly: true });
    const trace = history.map((h: any, idx: number) => `${idx + 1}. ${h.content}`).join('\n');
    const sys = new SystemMessage('You summarize the agent execution into a final answer.');
    const human = new HumanMessage(`Task: ${task}

Execution trace:
${trace}

Plan status:
${plan.map(s => `${s.title} [${s.status}]`).join('\n')}

Provide the final answer or explanation of what was completed.`);

    try {
      const res = await this.llm.invoke([sys, human], { temperature: 0 } as any);
      const answer = typeof res === 'string' ? res : (res as any).content || '';
      return `Task: ${task}\n\n${answer}`;
    } catch {
      return `Task: ${task}\n\nCompleted steps:\n${plan.map(s => `${s.title} - ${s.status}`).join('\n')}`;
    }
  }

  private async safeMemoryContext(task: string): Promise<string> {
    try {
      return await this.memory.getBFSContext(task, 10);
    } catch {
      return '';
    }
  }

  private generateId(prefix: string): string {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  }

  // Lightweight state accessors for UI
  getState(): { task: string; steps: number; completed: number; failed: number; pending: number; replans: number; plan: PlannedStep[] } {
    const completed = this.lastPlan.filter(s => s.status === 'done').length;
    const failed = this.lastPlan.filter(s => s.status === 'failed').length;
    const pending = this.lastPlan.filter(s => s.status === 'pending' || s.status === 'running').length;
    return {
      task: this.lastTask,
      steps: this.lastPlan.length,
      completed,
      failed,
      pending,
      replans: this.lastReplans,
      plan: this.lastPlan
    };
  }

  getScenarioCache(): Map<string, never> {
    return new Map<string, never>();
  }

  // --- helpers ---
  private autoFixStep(step: PlannedStep, errorText: string): { inputs: Record<string, any>; title?: string } | null {
    const lower = (errorText || '').toLowerCase();
    // Handle missing repo_url for clone_repository
    if (step.tool === 'clone_repository' && lower.includes("required parameter 'repo_url' missing")) {
      const inputs = { ...step.inputs };
      const url = inputs['repository_url'] || inputs['repo_url'];
      if (url) {
        return { inputs: { ...inputs, repo_url: url, repository_url: undefined }, title: `${step.title} (fixed repo_url)` };
      }
    }
    if (step.tool === 'clone_repository' && lower.includes("required parameter 'repo_name' missing")) {
      const inputs = { ...step.inputs };
      const url = inputs['repo_url'] || inputs['repository_url'];
      const derived = url ? this.deriveRepoName(url) : null;
      if (derived) {
        return { inputs: { ...inputs, repo_name: derived }, title: `${step.title} (fixed repo_name)` };
      }
    }
    return null;
  }

  private interpretResult(_tool: string, result: any): { success: boolean; text: string; meta?: any } {
    let success = typeof result?.success === 'boolean' ? Boolean(result.success) : true;
    let text = JSON.stringify(result).slice(0, 800);

    const exitCode = this.extractExitCode(result);
    const stderr = this.extractStderr(result);
    const commandNotFound = /command not found/i.test(text);

    if (exitCode !== null && exitCode !== 0) {
      success = false;
      text = `Exit code ${exitCode} ${stderr ? `| STDERR: ${stderr}` : ''}`.trim();
    } else if (stderr) {
      // treat non-empty stderr as warning; keep success unless clearly an error
      if (/not found|error|failed/i.test(stderr)) {
        success = false;
      }
      text = `${text} | STDERR: ${stderr}`;
    }

    if (commandNotFound) {
      success = false;
      text = `${text} | error: command not found`;
    }

    return { success, text, meta: result };
  }

  private extractExitCode(result: any): number | null {
    const raw = (result?.result || result?.message || '').toString();
    const match = raw.match(/Exit Code:\s*(-?\d+)/i);
    if (match) {
      return parseInt(match[1], 10);
    }
    return null;
  }

  private extractStderr(result: any): string | null {
    const raw = (result?.result || '').toString();
    const split = raw.split('STDERR:');
    if (split.length > 1) {
      const stderr = split[1].trim();
      if (stderr) return stderr.slice(0, 400);
    }
    return null;
  }

  private deriveRepoName(url: string): string {
    try {
      const clean = url.replace(/\/+$/, '');
      const last = clean.split('/').pop() || '';
      return last.replace(/\.git$/i, '') || 'repo';
    } catch {
      return 'repo';
    }
  }
}
