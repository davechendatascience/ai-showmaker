import { HTTPMCPClient } from '../mcp/http-mcp-client';
import { SessionManager } from '../core/session-manager';
import { BaseLanguageModel } from '@langchain/core/language_models/base';
import { HumanMessage, SystemMessage } from '@langchain/core/messages';
import { ValidatorAgent } from './validator-agent';

type PlanNode = {
  action: string;           // high-level plan label (e.g., gather_info, extract_constraints, design, implement, verify, summarize)
  reasoning: string;        // why this step
  inputs: any;              // free-form inputs (e.g., { query, filename })
  score?: number;           // value estimate
  depth: number;            // search depth
  tool?: string;            // resolved tool (optional)
};

export class BestFirstSearchAgent {
  private mcpClient: HTTPMCPClient;
  private llm: BaseLanguageModel;
  private sessionManager: SessionManager;
  private validator: ValidatorAgent;

  private maxIterations = Number(process.env['BFS_MAX_ITER'] || 40);
  private beamWidth = Number(process.env['BFS_BEAM_WIDTH'] || 4);
  private minScore = Number(process.env['BFS_MIN_SCORE'] || 0.4);
  private debug = String(process.env['BFS_DEBUG'] || 'false').toLowerCase() === 'true';
  private validatorEvery = Number(process.env['BFS_VALIDATOR_EVERY'] || 1);
  private validatorMinConf = Number(process.env['BFS_VALIDATOR_CONF'] || 0.7);
  private validatorMode = String(process.env['BFS_VALIDATOR_MODE'] || 'action').toLowerCase(); // 'action' | 'periodic' | 'both'
  private valueTrigger = Number(process.env['BFS_VALUE_TRIGGER'] || 0.8); // trigger validation sequence when plan value exceeds
  private validationCooldown = Number(process.env['BFS_VALIDATION_COOLDOWN'] || 2); // min iters between validations
  private hintBoost = Number(process.env['BFS_HINT_BOOST'] || 0.35); // score boost for actions aligned with validator hints
  private specialHintBoost = Number(process.env['BFS_SPECIAL_HINT_BOOST'] || 0.1); // extra bump for test_example & implement_code
  private lastValidatorHints: string[] = [];
  private lastValidatorConfs: number[] = [];
  private autoExplain = String(process.env['BFS_AUTO_EXPLAIN'] || 'true').toLowerCase() === 'true';
  private explainMaxChars = Number(process.env['BFS_EXPLAIN_MAX'] || 400);
  // Max chars to show in console for inline explanations. 0 = no truncation
  private explainLogMax = Number(process.env['BFS_EXPLAIN_LOG_MAX'] || 0);

  constructor(mcpClient: HTTPMCPClient, llm: BaseLanguageModel, sessionManager: SessionManager) {
    this.mcpClient = mcpClient;
    this.llm = llm;
    this.sessionManager = sessionManager;
    this.validator = new ValidatorAgent(this.llm);
  }

  // Detect presence of operational checks/commands in the draft
  private extractOpsChecks(text: string): { snippet: string } | null {
    try {
      const patterns = [
        /\bcurl\s+http/i,
        /\bsystemctl\s+status\b/i,
        /\bss\s+-ltnp\b/i,
        /\bjournalctl\s+-u\b/i,
        /\byum\s+install\b|\bdnf\s+install\b|\bapt\s+install\b/i,
        /\bnginx\s+-t\b|\bapachectl\s+-t\b/i,
        /\bfirewall-cmd\b|\bufw\s+allow\b/i,
        /\bpm2\s+start\b|\bsystemd\b/i,
        /\baws\s+ec2\b|\bsecurity\s+group\b/i
      ];
      for (const re of patterns) {
        const m = text.match(re);
        if (m) {
          const idx = Math.max(0, m.index || 0);
          const snippet = text.slice(Math.max(0, idx - 80), Math.min(text.length, idx + 160));
          return { snippet };
        }
      }
      return null;
    } catch {
      return null;
    }
  }

  async executeTask(task: string, sessionId: string): Promise<string> {
    try { this.sessionManager.addMessage(sessionId, { role: 'user', content: task }); } catch {}

    const tools = this.mcpClient.getTools().map(t => ({ name: t.name, description: t.description, schema: t.schema }));
    const scratchpad: Array<{ thought: string; step: string; tool?: string; params?: any; observation?: string; success?: boolean; meta?: any; score?: number }> = [];

    // Frontier holds plan nodes (best-first by score)
    let frontier: PlanNode[] = await this.proposePlans(task, tools, scratchpad, this.beamWidth, 0);
    frontier = await this.scorePlans(task, scratchpad, frontier);
    this.sortFrontier(frontier);

    let lastValidationIter = -Infinity;
    let lastEvidenceIter = -Infinity;
    for (let iter = 0; iter < this.maxIterations; iter++) {
      if (frontier.length === 0) break;
      const node = frontier.shift()!; // best
      if (this.debug) console.log(`[BFS] Iter ${iter + 1} pick: action=${node.action} score=${node.score?.toFixed(2)} reason=${node.reasoning.slice(0, 120)}`);

      // Resolve to concrete tool and execute (if resolvable);
      const resolved = this.resolvePlan(task, tools, node, scratchpad);
      // Log chosen action with score for visibility
      const s = typeof node.score === 'number' ? node.score.toFixed(2) : 'n/a';
      console.log(`[BFS] act: action=${node.action}${resolved.tool ? ` -> ${resolved.tool}` : ''} score=${s}`);
      let observation = { success: true, text: 'No-op', completionSignal: false } as { success: boolean; text: string; completionSignal?: boolean };
      if (resolved.tool) {
        observation = await this.execute(resolved.tool, resolved.inputs);
      }

      // Append to trace
      const entry: any = {
        thought: node.reasoning,
        step: node.action,
        params: resolved.inputs,
        observation: observation.text,
        success: observation.success,
        meta: (observation as any).meta,
        score: node.score,
      };
      if (resolved.tool) entry.tool = resolved.tool;
      // Inline explanation (not a separate step): synthesize concise, evidence-grounded text
      if (this.autoExplain && observation.success) {
        try {
          const toolLower = String(resolved.tool || '').toLowerCase();
          if (toolLower.includes('search') || toolLower === 'extract_content') {
            const explanation = await this.explainInline(task, resolved.tool || 'none', entry);
            if (explanation) {
              entry.meta = entry.meta || {};
              entry.meta.explanation = explanation;
              const expl = String(explanation);
              const max = Number.isFinite(this.explainLogMax) ? this.explainLogMax : 0;
              const summary = max > 0 ? `${expl.slice(0, max)}${expl.length > max ? '…' : ''}` : expl;
              console.log(`[BFS] explain: ${summary}`);
            }
          }
        } catch {}
      }
      scratchpad.push(entry);

      // Track evidence-producing steps (used to gate validation injections)
      try {
        const toolLower2 = String(entry.tool || '').toLowerCase();
        const meta2 = entry?.meta || {};
        const hasExtract = toolLower2 === 'extract_content' && Number(meta2.content_length || 0) > 0;
        const hasCalc = toolLower2 === 'calculate' && entry.success === true;
        const hasSearch = toolLower2.includes('search') && Array.isArray(meta2.top_results) && meta2.top_results.length > 0;
        if (hasExtract || hasCalc || hasSearch) lastEvidenceIter = iter;
      } catch {}

      // If this step was an explicit validation action, handle verdict immediately
      if (resolved.tool === 'internal_validate') {
        try {
          const verdict = entry?.meta?.validator || {};
          const conf = Number(verdict.confidence) || 0;
          console.log(`[BFS][validator] completed=${Boolean(verdict.completed)} conf=${conf.toFixed(2)} mode=action`);
          if (verdict.rationale) console.log(`[BFS][validator] rationale: ${String(verdict.rationale).slice(0,160)}${String(verdict.rationale).length>160?'…':''}`);
          if (this.debug) {
            if (verdict.issues && verdict.issues.length) console.log(`[BFS][validator] issues: ${verdict.issues.join('; ')}`);
            if (verdict.suggested_next_actions && verdict.suggested_next_actions.length) console.log(`[BFS][validator] hints: ${verdict.suggested_next_actions.join('; ')}`);
          }
          this.lastValidatorHints = Array.isArray(verdict.suggested_next_actions) ? verdict.suggested_next_actions.slice(0, 3) : [];
          const confNum = Number(verdict.confidence);
          if (Number.isFinite(confNum)) {
            this.lastValidatorConfs.push(confNum);
            if (this.lastValidatorConfs.length > 10) this.lastValidatorConfs.shift();
          }
          lastValidationIter = iter;
          if (Boolean(verdict.completed) && conf >= this.validatorMinConf) {
            return await this.renderAnswer(task, scratchpad);
          }
        } catch {}
      }

      // Optional periodic validator (disabled when mode='action')
      if (this.validatorMode !== 'action' && this.validatorEvery > 0 && (iter + 1) % this.validatorEvery === 0) {
        try {
          const verdict = await this.validator.validate(task, scratchpad);
          console.log(`[BFS][validator] completed=${verdict.completed} conf=${(Number(verdict.confidence) || 0).toFixed(2)}`);
          if (verdict.rationale) console.log(`[BFS][validator] rationale: ${String(verdict.rationale).slice(0,160)}${String(verdict.rationale).length>160?'…':''}`);
          if (this.debug) {
            if (verdict.issues && verdict.issues.length) console.log(`[BFS][validator] issues: ${verdict.issues.join('; ')}`);
            if (verdict.suggested_next_actions && verdict.suggested_next_actions.length) console.log(`[BFS][validator] hints: ${verdict.suggested_next_actions.join('; ')}`);
          }
          this.lastValidatorHints = Array.isArray(verdict.suggested_next_actions) ? verdict.suggested_next_actions.slice(0, 3) : [];
          const confNum = Number(verdict.confidence);
          if (Number.isFinite(confNum)) {
            this.lastValidatorConfs.push(confNum);
            if (this.lastValidatorConfs.length > 10) this.lastValidatorConfs.shift();
          }
          if (verdict.completed && (Number(verdict.confidence) || 0) >= this.validatorMinConf) {
            return await this.renderAnswer(task, scratchpad);
          }
        } catch {}
      }

      // Auto-validate on summarize/completion signal only when mode!='action'
      const lower = node.action.toLowerCase();
      const isSummarize = /summarize|synthesize_answer|finalize|report/.test(lower);
      const shouldAutoValidate = (this.validatorMode !== 'action') && ((observation.success && observation.completionSignal) || isSummarize);
      if (shouldAutoValidate) {
        try {
          const verdict2 = await this.validator.validate(task, scratchpad);
          console.log(`[BFS][validator] recheck completed=${verdict2.completed} conf=${(Number(verdict2.confidence) || 0).toFixed(2)} reason=summary_or_signal`);
          if (verdict2.completed && (Number(verdict2.confidence) || 0) >= this.validatorMinConf) {
            return await this.renderAnswer(task, scratchpad);
          }
        } catch {}
        // Not validated with enough confidence; continue planning
      }

      // Inject a validation sequence when value exceeds trigger
      try {
        const val = typeof node.score === 'number' ? node.score : 0;
        const cooldownOk = (iter - lastValidationIter) >= this.validationCooldown;
        const recentlyValidated = scratchpad.slice(-3).some(e => /validate|verify/i.test(String(e.step || '')));
        const frontierHasValidation = frontier.some(p => /validate|verify/i.test(String(p.action || '')));
        const haveNewEvidenceSinceLastValidation = lastEvidenceIter > lastValidationIter;
        // If validator is asking for tests, require tests to exist before injecting validation
        const needTests = (this.lastValidatorHints || []).some(h => /test/i.test(String(h)));
        const haveTests = scratchpad.slice().reverse().find(e => String(e.tool||'')==='internal_compose_answer')?.meta?.draft_tests_present === true;
        if (this.validatorMode !== 'periodic' && val >= this.valueTrigger && cooldownOk && !recentlyValidated && !frontierHasValidation && haveNewEvidenceSinceLastValidation) {
          const haveDraft = scratchpad.some(e => /synthesize_answer|finalize|summarize/i.test(String(e.step || '')));
          const injected: PlanNode[] = [];
          if (!haveDraft) injected.push({ action: 'synthesize_answer', inputs: {}, reasoning: 'Compose a draft final answer for validation', depth: node.depth + 1, score: 1.0 });
          if (needTests && !haveTests) {
            injected.push({ action: 'test_example', inputs: {}, reasoning: 'Add self-tests to support validation', depth: node.depth + 1, score: 0.995 });
          } else {
            injected.push({ action: 'validate', inputs: {}, reasoning: 'Ask validator to judge completion and confidence', depth: node.depth + 1, score: 0.99 });
          }
          if (injected.length) {
            console.log(`[BFS] schedule: injecting ${injected.map(p=>p.action).join(' + ')} (value=${val.toFixed(2)} >= trigger=${this.valueTrigger.toFixed(2)})`);
            frontier.push(...injected);
            this.sortFrontier(frontier);
          }
        }
      } catch {}

      const children = await this.proposePlans(task, tools, scratchpad, this.beamWidth, node.depth + 1);
      const scored = await this.scorePlans(task, scratchpad, children);
      frontier.push(...scored);
      this.sortFrontier(frontier);
    }

    return await this.renderAnswer(task, scratchpad);
  }

  // Compatibility shim
  async executeComplexTask(taskQuery: string, sessionId: string): Promise<string> {
    return this.executeTask(taskQuery, sessionId);
  }

  private async proposePlans(task: string, tools: any[], scratchpad: any[], k: number, depth: number): Promise<PlanNode[]> {
    const sys = new SystemMessage(`# Role
You are a planning policy. Propose the next ${k} high-level actions (plan labels) to advance the task.
Each action is abstract (e.g., gather_info, extract_data, analyze, design, implement, verify, summarize).
Do not list concrete tool names; the executor maps actions to tools dynamically.
Prefer non-interactive, verifiable steps. Avoid system/todo/monitoring operations.`);

    const historyFmt = scratchpad.slice(-5).map((e, i) => `${i + 1}. step=${e.step} tool=${e.tool || 'none'} -> ${(e.observation || '').slice(0, 160)}`).join('\n');
    const forbidden = (() => {
      const recent = scratchpad.slice(-2).map(e => String(e.step || '').toLowerCase());
      return Array.from(new Set(recent));
    })();
    const toolNames = tools.map(t => t.name).join(', ');
    const hints = (this.lastValidatorHints || []).map((h, i) => `${i + 1}. ${h}`).join('\n');
    const human = new HumanMessage(`Task: ${task}
Available Tool Names (for executor reference only): ${toolNames}

Recent Trace:
${historyFmt || 'None'}

Avoid proposing these actions immediately again (just tried): ${forbidden.length ? forbidden.join(', ') : 'None'}

Validator Hints (optional):
${hints || 'None'}

Output EXACTLY ${k} proposal blocks with this format:
PROPOSAL:
ACTION: <plan label>
INPUTS: <valid JSON with inputs for the action, e.g., {"query":"..."} or {"filename":"..."}>
REASONING: <why this step is needed next>
`);

    const res = await this.llm.invoke([sys, human]);
    const text = String(res.content || '');
    const blocks = text.split(/PROPOSAL:/i).map(s => s.trim()).filter(Boolean);
    let out: PlanNode[] = [];
    for (const b of blocks.slice(0, k)) {
      const action = this.extractSection(b, 'ACTION') || '';
      const inputsStr = this.extractSection(b, 'INPUTS');
      const reasoning = this.extractSection(b, 'REASONING') || '';
      let inputs: any = {};
      try { inputs = inputsStr ? JSON.parse(inputsStr) : {}; } catch {}
      if (action) out.push({ action, inputs, reasoning, depth });
    }
    // Avoid summarize on the very first step
    if (depth === 0) {
      out = out.filter(p => !/^(summarize|synthesize_answer|finalize|report)$/i.test(p.action || ''));
    }
    // If all proposed plans would map to search tools again, inject a non-search reflective step
    try {
      const predictedTools = out.map(p => this.predictTool(task, tools, p)).filter(Boolean) as string[];
      const allSearch = predictedTools.length > 0 && predictedTools.every(t => t.toLowerCase().includes('search'));
      if (allSearch) {
        out.push({ action: 'analyze', inputs: {}, reasoning: 'Reflect on gathered information and propose next concrete step without performing a new search', depth });
      }
    } catch {}
    // Minimal fallback if none
    if (out.length === 0) out.push({ action: 'gather_info', inputs: { query: task }, reasoning: 'Collect information relevant to the task', depth });
    return out;
  }

  private async scorePlans(task: string, scratchpad: any[], plans: PlanNode[]): Promise<PlanNode[]> {
    const sys = new SystemMessage(`# Role
You are a value function. Score each proposed high-level action by its expected utility (0-1) towards completing the task.
Favor actions that make verifiable progress (e.g., gather info, extract key details, design steps, verify results, summarize).`);
    const list = plans.map((p, i) => `${i + 1}. ACTION=${p.action} INPUTS=${JSON.stringify(p.inputs)} WHY=${p.reasoning}`).join('\n');
    const recent = scratchpad.slice(-3).map((e, i) => `${i + 1}. ${e.step} -> ${e.success ? 'OK' : 'OBS'}: ${(e.observation || '').slice(0, 80)}`).join('\n');
    const human = new HumanMessage(`Task: ${task}
Recent: ${recent || 'None'}

Proposals:
${list}

Return strictly one line:
SCORES: [s1, s2, ...] (numbers 0-1)`);
    try {
      const resp = await this.llm.invoke([sys, human]);
      const text = String(resp.content || '');
      const m = text.match(/\[\s*([\d\.,\s]+)\s*\]/);
      if (m && m[1]) {
        const nums = m[1].split(/[,\s]+/).filter(Boolean).map(n => {
          const val = Number(n);
          return Number.isFinite(val) ? val : 0;
        });
        const n = Math.min(plans.length, nums.length);
        for (let i = 0; i < n; i++) {
          const vvRaw: any = (Array.isArray(nums) && i >= 0 && i < nums.length) ? nums[i] : 0;
          const vv: number = Number.isFinite(vvRaw) ? (vvRaw as number) : 0;
          const plan = plans[i];
          if (plan) plan.score = Math.max(0, Math.min(1, vv));
        }
      }
    } catch {}
    plans.forEach(p => { if (p.score === undefined) p.score = 0.5; });

    // Boost actions that align with validator hints
    try {
      const hints = Array.isArray(this.lastValidatorHints) ? this.lastValidatorHints.map(h => String(h).toLowerCase()) : [];
      if (hints.length) {
        for (const p of plans) {
          const a = String(p.action || '').toLowerCase();
          if (hints.some(h => a.includes(h) || h.includes(a))) {
            const boost = Number.isFinite(this.hintBoost) ? this.hintBoost : 0.25;
            p.score = Math.min(1, (p.score ?? 0) + boost);
          }
          // Extra bump when validator specifically asks for tests/code
          const extra = Number.isFinite(this.specialHintBoost) ? this.specialHintBoost : 0.1;
          const aNorm = a.replace(/\s+/g, '_');
          const wantsTest = hints.some(h => h.includes('test_example') || h.includes('test'));
          const wantsCode = hints.some(h => h.includes('implement_code') || h.includes('code') || h.includes('implement'));
          if (wantsTest && /test_example/.test(aNorm)) {
            p.score = Math.min(1, (p.score ?? 0) + extra);
          }
          if (wantsCode && /(implement_code|complete_solution|\bimplement\b)/.test(aNorm)) {
            p.score = Math.min(1, (p.score ?? 0) + extra);
          }
        }
      }
    } catch {}

    // Penalize redundant validation when recent validation failed
    try {
      const recent = scratchpad.slice(-3);
      const lastVal = [...recent].reverse().find(e => /validate|verify|revalidate/i.test(String(e.step || '')));
      const lastValFailed = lastVal ? !(lastVal?.meta?.validator?.completed && Number(lastVal?.meta?.validator?.confidence || 0) >= (this.validatorMinConf || 0)) : false;
      if (lastVal && lastValFailed) {
        for (const p of plans) {
          if (/validate|verify|revalidate/i.test(String(p.action || ''))) {
            p.score = Math.max(0, (p.score ?? 0) - 0.3);
          }
        }
      }
    } catch {}

    // Penalize early validation if no draft answer exists yet
    try {
      const hasDraft = scratchpad.some(e => String(e.tool || '') === 'internal_compose_answer' && typeof e?.meta?.draft_answer === 'string' && e.meta.draft_answer.length > 0);
      if (!hasDraft) {
        for (const p of plans) {
          if (/validate|verify|revalidate/i.test(String(p.action || ''))) {
            p.score = Math.max(0, (p.score ?? 0) - 0.4);
          }
        }
      }
    } catch {}

    // If validator asks for tests and we don't have tests yet, downweight validation and upweight test_example
    try {
      const needTests = (this.lastValidatorHints || []).some(h => /test/i.test(String(h)));
      const latestDraft = scratchpad.slice().reverse().find(e => String(e.tool||'')==='internal_compose_answer');
      const hasTests = latestDraft?.meta?.draft_tests_present === true;
      if (needTests && !hasTests) {
        for (const p of plans) {
          const a = String(p.action || '').toLowerCase();
          if (/validate|verify|revalidate/.test(a)) p.score = Math.max(0, (p.score ?? 0) - 0.3);
          if (/test_example|add_tests|verify_examples?/.test(a)) p.score = Math.min(1, (p.score ?? 0) + 0.2);
        }
      }
    } catch {}

    // Novelty/diversity: penalize repeating identical step back-to-back
    const last = scratchpad[scratchpad.length - 1];
    const lastTool = String(last?.tool || '').toLowerCase();
    const secondLastTool = String((scratchpad[scratchpad.length - 2]?.tool) || '').toLowerCase();
    const stagnating = (() => {
      const l = this.lastValidatorConfs;
      if (l.length < 2) return false;
      const d = (l[l.length - 1] as number) - (l[l.length - 2] as number);
      return d < 0.05; // little to no improvement
    })();
    if (last) {
      for (const p of plans) {
        if (String(p.action || '').toLowerCase() === String(last.step || '').toLowerCase()) {
          p.score = Math.max(0, (p.score ?? 0) - 0.2);
        }
        // Predict likely tool for penalty shaping
        try {
          const tool = (this.predictTool(task, this.mcpClient.getTools().map(t => ({ name: t.name })), p) || '').toLowerCase();
          if (tool) {
            if (tool === lastTool) p.score = Math.max(0, (p.score ?? 0) - 0.2);
            if (tool === secondLastTool) p.score = Math.max(0, (p.score ?? 0) - 0.1);
            if (stagnating && tool.includes('search')) p.score = Math.max(0, (p.score ?? 0) - 0.2);
          }
        } catch {}
      }
    }

    // Filter by threshold but keep at least one
    const filtered = plans.filter(p => (p.score ?? 0) >= this.minScore);
    return filtered.length ? filtered : plans;
  }

  private sortFrontier(frontier: PlanNode[]) {
    frontier.sort((a, b) => (b.score || 0) - (a.score || 0));
    if (frontier.length > this.beamWidth) frontier.splice(this.beamWidth);
  }

  // Predicts which tool a plan would likely map to (used only for scoring penalties; does not execute)
  private predictTool(task: string, tools: any[], plan: PlanNode): string | undefined {
    const name = (plan.action || '').toLowerCase();
    const toolNames = new Set((tools || []).map((t: any) => String(t.name)));
    const allow = (t: string) => toolNames.has(t);
    const mode = this.detectMode(task);
    if (/gather|search|discover|info/.test(name)) {
      if (mode === 'info') {
        if (allow('search_and_extract')) return 'search_and_extract';
        if (allow('search_web')) return 'search_web';
      }
      return undefined;
    }
    if (/extract|parse|scrape|content/.test(name)) {
      if (allow('extract_content')) return 'extract_content';
      if (allow('search_and_extract')) return 'search_and_extract';
    }
    if (/calculate|compute|math/.test(name)) {
      if (allow('calculate')) return 'calculate';
    }
    if (/list|explore\s*files|directory|ls\b/.test(name)) {
      if (allow('list_directory')) return 'list_directory';
    }
    if (/read\s*file|open\s*file/.test(name)) {
      if (allow('read_file')) return 'read_file';
    }
    if (/write\s*file|create\s*file|save/.test(name)) {
      if (allow('write_file')) return 'write_file';
    }
    if (/execute|run\s*commands?/.test(name)) {
      if (allow('execute_commands_session')) return 'execute_commands_session';
    }
    if (toolNames.has(plan.action)) return plan.action;
    return undefined;
  }

  // Lightweight mode detection to bias gather->search mapping only to info-like tasks
  private detectMode(task: string): 'info' | 'calc' | 'dev' | 'other' {
    const t = (task || '').toLowerCase();
    if (/(\d+\s*[+\-*\/]\s*\d+|calculate|math|sum|product|difference|quotient)/.test(t)) return 'calc';
    if (/(develop|build|create|deploy|web\s*app|frontend|backend|server|docker|kubernetes|react|node|express|flask|fastapi|django)/.test(t)) return 'dev';
    if (/(search|find|lookup|what\s+is|information|explain|docs?)/.test(t)) return 'info';
    return 'other';
  }
  private resolvePlan(task: string, tools: any[], plan: PlanNode, scratchpad: any[]) {
    const name = (plan.action || '').toLowerCase();
    const inputs = plan.inputs || {};
    const toolNames = new Set((tools || []).map((t: any) => String(t.name)));
    const allow = (t: string) => toolNames.has(t);
    // Map generic actions to candidate tools (executor resolves dynamically)
    if (/gather|search|discover|info/.test(name)) {
      // Avoid immediately repeating search if the last tool was a search tool
      try {
        const last = scratchpad[scratchpad.length - 1];
        const lastTool = String(last?.tool || '').toLowerCase();
        if (lastTool.includes('search')) return { tool: undefined, inputs };
      } catch {}
      const q = inputs.query || task;
      if (allow('search_and_extract')) return { tool: 'search_and_extract', inputs: { query: q } };
      if (allow('search_web')) return { tool: 'search_web', inputs: { query: q } };
    }
    if (/extract|parse|scrape|content/.test(name)) {
      let target: string = String(inputs.url || '').trim();
      if (!/^https?:\/\//i.test(target)) {
        const fromHistory = this.pickLastSearchUrl(scratchpad);
        if (fromHistory) target = fromHistory;
      }
      if (allow('extract_content') && /^https?:\/\//i.test(target)) return { tool: 'extract_content', inputs: { url: target } };
      if (allow('search_and_extract')) return { tool: 'search_and_extract', inputs: { query: inputs.query || task } };
    }
    if (/calculate|compute|math/.test(name)) {
      const exprFromTask = (() => {
        const t = String(task || '');
        // naive math expression detection for simple queries like "2+2"
        return /\d+\s*[+\-*\/]\s*\d+/.test(t) ? t : undefined;
      })();
      if (allow('calculate')) {
        if (inputs.expression) return { tool: 'calculate', inputs: { expression: inputs.expression } };
        if (exprFromTask) return { tool: 'calculate', inputs: { expression: exprFromTask } };
      }
    }
    if (/list|explore\s*files|directory|ls\b/.test(name)) {
      if (allow('list_directory')) return { tool: 'list_directory', inputs: { path: inputs.path || '.' } };
    }
    if (/read\s*file|open\s*file/.test(name)) {
      if (allow('read_file') && inputs.filename) return { tool: 'read_file', inputs: { filename: inputs.filename } };
    }
    if (/write\s*file|create\s*file|save/.test(name)) {
      if (allow('write_file') && inputs.filename && typeof inputs.content === 'string') return { tool: 'write_file', inputs: { filename: inputs.filename, content: inputs.content } };
    }
    if (/execute|run\s*commands?/.test(name)) {
      if (allow('execute_commands_session') && Array.isArray(inputs.commands) && inputs.commands.length) return { tool: 'execute_commands_session', inputs };
    }
    if (/summarize|synthesize|finalize|report/.test(name)) {
      // Compose draft answer as an internal step so validator can evaluate it
      const hintsJoined = (this.lastValidatorHints || []).join(' ').toLowerCase();
      const preferCode = /code|implement|solution/.test(hintsJoined) || /leetcode|code|implement|algorithm|problem/i.test(task);
      const preferSelfTests = /test|example/.test(hintsJoined);
      const preferOpsChecks = /develop|deploy|server|web\s*app|amazon\s*linux|aws|nginx|apache|systemd|pm2/.test(hintsJoined) || this.detectMode(task) === 'dev';
      return { tool: 'internal_compose_answer', inputs: { task, scratchpad, preferCode, preferSelfTests, preferOpsChecks } };
    }
    if (/implement_code|write\s*code|provide\s*code|complete_solution|implement\b/.test(name)) {
      const preferCode = true;
      const preferSelfTests = true;
      const preferOpsChecks = this.detectMode(task) === 'dev';
      return { tool: 'internal_compose_answer', inputs: { task, scratchpad, preferCode, preferSelfTests, preferOpsChecks } };
    }
    if (/test_example|add_tests|verify_examples?/.test(name)) {
      const preferCode = true;
      const preferSelfTests = true;
      const preferOpsChecks = this.detectMode(task) === 'dev';
      return { tool: 'internal_compose_answer', inputs: { task, scratchpad, preferCode, preferSelfTests, preferOpsChecks } };
    }
    if (/validate|verify|check\s*answer|ask\s*validation/.test(name)) {
      // Only run validation if we have a draft or some concrete evidence
      const hasDraft = scratchpad.some(e => String(e.tool || '') === 'internal_compose_answer' && typeof e?.meta?.draft_answer === 'string' && e.meta.draft_answer.length > 0);
      const needTests = (this.lastValidatorHints || []).some(h => /test/i.test(String(h)));
      const latestDraft = scratchpad.slice().reverse().find(e => String(e.tool||'')==='internal_compose_answer');
      const hasTests = latestDraft?.meta?.draft_tests_present === true;
      const hasEvidence = (() => {
        for (let i = scratchpad.length - 1; i >= 0; i--) {
          const it = scratchpad[i];
          const t = String(it?.tool || '').toLowerCase();
          if (t === 'extract_content' && Number(it?.meta?.content_length || 0) > 0) return true;
          if (t.includes('search') && Array.isArray(it?.meta?.top_results) && it.meta.top_results.length > 0) return true;
          if (t === 'calculate' && it?.success === true) return true;
        }
        return false;
      })();
      if (!(hasDraft || hasEvidence)) return { tool: undefined, inputs };
      if (needTests && !hasTests) return { tool: undefined, inputs };
      return { tool: 'internal_validate', inputs: { task, scratchpad } };
    }
    // If action directly names a tool and it's available, use it
    if (toolNames.has(plan.action)) return { tool: plan.action, inputs };
    // Otherwise, leave as a reasoning/no-op step
    return { tool: undefined, inputs };
  }

  private async execute(tool: string, params: any): Promise<{ success: boolean; text: string; completionSignal?: boolean; meta?: any }> {
    try {
      // Internal tools (not via MCP)
      if (tool === 'internal_compose_answer') {
        let answer = await this.composeAnswer(
          String(params?.task || ''),
          Array.isArray(params?.scratchpad) ? params.scratchpad : [],
          Boolean(params?.preferCode),
          Boolean(params?.preferSelfTests),
          Boolean(params?.preferOpsChecks)
        );
        // Ensure self-tests exist when requested
        let testsMeta = this.extractSelfTests(answer);
        try {
          if (Boolean(params?.preferSelfTests) && !testsMeta) {
            let testsBlock = await this.composeSelfTests(String(params?.task || ''), answer);
            testsBlock = String(testsBlock || '').trim();
            if (testsBlock.length) {
              if (!/```/.test(testsBlock)) {
                testsBlock = "\n\n```json\n" + testsBlock + "\n```\n";
              } else {
                testsBlock = "\n\n" + testsBlock + "\n";
              }
              answer = `${answer}\n\nSelf-Tests\n${testsBlock}`;
              testsMeta = this.extractSelfTests(answer);
            }
          }
        } catch {}
        const codeMeta = this.extractFirstCodeBlock(answer);
        const opsMeta = this.extractOpsChecks(answer);

        const meta: any = { draft_answer: answer };
        if (codeMeta) {
          meta.draft_has_code = true;
          meta.draft_code_lang = codeMeta.language || undefined;
          meta.draft_code_snippet = codeMeta.code.slice(0, 400);
        } else {
          meta.draft_has_code = false;
        }
        if (testsMeta) {
          meta.draft_tests_present = true;
          meta.draft_tests_cases_count = testsMeta.casesCount;
          meta.draft_tests_json_snippet = testsMeta.json.slice(0, 400);
        } else {
          meta.draft_tests_present = false;
        }
        if (opsMeta) {
          meta.draft_ops_checks_present = true;
          meta.draft_ops_snippet = opsMeta.snippet.slice(0, 200);
        } else {
          meta.draft_ops_checks_present = false;
        }
        try {
          const tcases = Number(meta.draft_tests_cases_count || 0);
          const tsnip = String(meta.draft_tests_json_snippet || '').replace(/\s+/g, ' ').slice(0, 200);
          const osnip = String(meta.draft_ops_snippet || '').replace(/\s+/g, ' ').slice(0, 160);
          const clog = `[BFS] draft: code=${meta.draft_has_code}${meta.draft_code_lang ? `, lang=${meta.draft_code_lang}` : ''} tests=${meta.draft_tests_present}${meta.draft_tests_present ? `, cases=${tcases}` : ''}${tsnip ? `, tests_snip=${tsnip}` : ''}${meta.draft_ops_checks_present ? `, ops_checks=true` : ''}${osnip ? `, ops_snip=${osnip}` : ''}`;
          console.log(clog);
        } catch {}
        return { success: true, text: `DRAFT_ANSWER(len=${answer.length})`, completionSignal: false, meta };
      }
      if (tool === 'internal_validate') {
        const taskStr = String(params?.task || '');
        const spad = Array.isArray(params?.scratchpad) ? params.scratchpad : [];
        const verdict = await this.validator.validate(taskStr, spad);
        const conf = Number(verdict.confidence) || 0;
        const passed = Boolean(verdict.completed) && conf >= this.validatorMinConf;
        const text = `VALIDATION completed=${Boolean(verdict.completed)} conf=${conf.toFixed(2)}${passed ? ' PASS' : ' FAIL'}`;
        return { success: true, text, completionSignal: passed, meta: { validator: verdict } };
      }
      const result = await this.mcpClient.executeTool(tool, params || {});
      const ok = typeof result?.success === 'boolean' ? Boolean(result.success) : true;
      const blob = JSON.stringify(result || '').slice(0, 800);
      let meta: any = undefined;
      // Summarize search results for visibility and validator context
      try {
        const isSearch = /search/.test(String(tool).toLowerCase());
        const r = (result as any) || {};
        if (isSearch) {
          const body = r.result || r || {};
          const total = body.total_results ?? (Array.isArray(body.results) ? body.results.length : undefined);
          const top = Array.isArray(body.results) ? body.results.slice(0, 3).map((x: any) => ({
            title: String(x?.title || '').slice(0, 140),
            url: String(x?.url || '').slice(0, 200)
          })) : [];
          meta = { total_results: total, top_results: top };
          if (total !== undefined) {
            const firstTitle = top?.[0]?.title ? `, first="${top[0].title}"` : '';
            console.log(`[BFS] obs: tool=${tool} ok=${ok} results=${total}${firstTitle}`);
          }
        } else if (String(tool).toLowerCase() === 'extract_content') {
          const body = r.result || r || {};
          const content = typeof body === 'string' ? body : (body.content || body.text || '');
          const err = body.error || r.error;
          const length = typeof content === 'string' ? content.length : 0;
          const snippet = typeof content === 'string' ? String(content).slice(0, 200) : undefined;
          meta = { content_length: length, error: err ? String(err) : undefined, snippet };
          console.log(`[BFS] obs: tool=${tool} ok=${ok} content_length=${length}${err ? `, error=${String(err).slice(0,80)}` : ''}`);
        }
      } catch {}
      const done = /health|200\s+ok|verified|success/i.test(blob);
      return { success: ok, text: blob, completionSignal: done, meta };
    } catch (e: any) {
      return { success: false, text: String(e || 'execution error') };
    }
  }

  private async renderAnswer(task: string, scratchpad: any[]): Promise<string> {
    // Always produce a final summary based on scratchpad
    const sys = new SystemMessage(`# Role
You are the final answer composer. Provide a concise, structured answer to the task based on the execution trace.
- Summarize key findings/deductions.
- If code/algorithmic: explain approach and complexity.
- If operational: list what was done and results.
- If insufficient info: state what is missing and next steps.
- For coding problems, include the final solution code (choose a reasonable language) if possible.`);
    const trace = scratchpad.map((e: any, i: number) => `${i + 1}. step=${e.step} tool=${e.tool || 'none'} success=${e.success ? 'true' : 'false'} -> ${(e.observation || '').slice(0, 200)}`).join('\n');
    const human = new HumanMessage(`Task: ${task}
Trace:
${trace || 'None'}

Write the final answer now.`);
    try {
      const resp = await this.llm.invoke([sys, human]);
      const answer = String(resp.content || '').trim();
      const lines = scratchpad.map((e: any, i: number) => `${i + 1}. ${e.step} ${e.tool ? '-> ' + e.tool : ''} : ${(e.observation || '').slice(0, 160)}`);
      return `Task: ${task}\n\nProgress:\n${lines.join('\n')}\n\nAnswer:\n${answer}`;
    } catch {
      const lines = scratchpad.map((e: any, i: number) => `${i + 1}. ${e.step} ${e.tool ? '-> ' + e.tool : ''} : ${(e.observation || '').slice(0, 160)}`);
      return `Task: ${task}\n\nProgress:\n${lines.join('\n')}`;
    }
  }

  private extractSection(text: string, key: string): string | null {
    const re = new RegExp(`${key}\s*:\\s*([\\s\\S]*?)(?:\\n[A-Z_]+\s*:|$)`, 'i');
    const m = text.match(re);
    if (!m || !m[1]) return null;
    return m[1].trim();
  }

  // Produce a concise, evidence-grounded explanation string for validator and user visibility
  private async explainInline(task: string, tool: string, entry: any): Promise<string> {
    try {
      const sys = new SystemMessage(`# Role
You write short, evidence-grounded explanations based on the agent's latest step.
Keep it 1-3 sentences. Use content from search results or extracted text.
Be specific and cite titles/URLs if relevant.`);
      const meta = entry?.meta || {};
      const top = Array.isArray(meta.top_results) ? meta.top_results : [];
      const tops = top.slice(0,2).map((r:any)=>`- ${r.title} (${r.url})`).join('\n');
      const snippet = meta.snippet ? String(meta.snippet) : '';
      const human = new HumanMessage(`Task: ${task}
Tool: ${tool}
Params: ${JSON.stringify(entry?.params || {})}
Observation: ${String(entry?.observation || '').slice(0, 400)}
Top Results:\n${tops || 'None'}
Extract Snippet:\n${snippet || 'None'}

Explain briefly what we learned and what it implies.`);
      const resp = await this.llm.invoke([sys, human]);
      const text = String(resp.content || '').trim();
      return text.slice(0, this.explainMaxChars);
    } catch {
      return '';
    }
  }

  // Extract first fenced code block from a text
  private extractFirstCodeBlock(text: string): { language: string | null; code: string } | null {
    try {
      const m = text.match(/```([a-zA-Z0-9_+-]*)\n([\s\S]*?)```/);
      if (!m) return null;
      const language = m[1] ? m[1].trim() : null;
      const code = m[2] || '';
      return { language, code };
    } catch {
      return null;
    }
  }

  // Extract a fenced JSON block that contains test cases
  private extractSelfTests(text: string): { json: string; casesCount: number } | null {
    try {
      const blocks = [...text.matchAll(/```([a-zA-Z0-9_+\-\.]*)?\n([\s\S]*?)```/g)];
      for (const m of blocks) {
        const lang = (m[1] || '').toLowerCase();
        const body = m[2] || '';
        // Heuristic: must mention cases or tests
        if (!/(\bcases\b|\btests\b)/i.test(body)) {
          // If language declares json, still consider
          if (!/json/.test(lang)) continue;
        }
        // Try to parse JSON (tolerate trailing commas poorly)
        let obj: any = null;
        try {
          obj = JSON.parse(body);
        } catch {
          // Attempt to strip comments and retry (very basic)
          const withoutComments = body.replace(/\/\/.*$/mg, '').replace(/\,\s*\}/g, '}').replace(/\,\s*\]/g, ']');
          try { obj = JSON.parse(withoutComments); } catch { obj = null; }
        }
        if (obj && (Array.isArray(obj.cases) || Array.isArray(obj.tests))) {
          const casesArr = Array.isArray(obj.cases) ? obj.cases : obj.tests;
          const count = casesArr.length || 0;
          return { json: body, casesCount: count };
        }
        // If not parseable, still return snippet as signal
        return { json: body, casesCount: 0 };
      }
      // Fallback: search for inline JSON containing "cases" without fences
      const inline = text.match(/\{[\s\S]{0,2000}?\bcases\b[\s\S]*?\}/);
      if (inline) {
        const body = inline[0];
        return { json: body, casesCount: 0 };
      }
      return null;
    } catch {
      return null;
    }
  }

  // Compose a minimal self-tests JSON block and short walkthrough
  private async composeSelfTests(task: string, currentDraft: string): Promise<string> {
    const sys = new SystemMessage(`# Role
You generate minimal self-tests for the provided solution. Output only a fenced JSON block with a top-level key "cases" and 2-3 items. Each item should include inputs and expected output. Keep inputs small. After the JSON, add a short 2-3 line walkthrough for one case.`);
    const human = new HumanMessage(`Task: ${task}
Current Draft (may include code):
${String(currentDraft).slice(0, 1500)}

Produce tests now. Format:
\`\`\`json
{"cases": [{"in": ..., "out": ...}, ...]}
\`\`\`
Walkthrough:
- ...
- ...`);
    try {
      const resp = await this.llm.invoke([sys, human]);
      const txt = String(resp.content || '').trim();
      return txt;
    } catch {
      return '';
    }
  }

  // Compose a draft answer string based on the current scratchpad (same prompt style as renderAnswer but returns only the answer text)
  private async composeAnswer(task: string, scratchpad: any[], preferCode: boolean = false, preferSelfTests: boolean = false, preferOpsChecks: boolean = false): Promise<string> {
    const sys = new SystemMessage(`# Role
You are the final answer composer. Provide a concise, structured answer to the task based on the execution trace.
- Summarize key findings/deductions.
- If code/algorithmic: explain approach and complexity.
- If operational: list what was done and results.
- If insufficient info: state what is missing and next steps.
${preferCode ? '- If this is a coding problem, include a correct, runnable reference implementation (e.g., Python) with brief explanation.' : ''}
${(preferCode || preferSelfTests) ? `- Include a Self-Tests section:
  - Provide 2-3 small test cases and expected outputs in a single fenced JSON block (language hint: json) with a top-level key named "cases" or "tests".
  - After the JSON, add a brief walkthrough for at least one case, showing key state updates.
  - Keep tests minimal and focused; avoid external dependencies.` : ''}
 ${preferOpsChecks ? `- For Dev/Ops tasks (e.g., remote server, deployment, Amazon Linux), include an Operational Checks section with:
   - Concrete shell commands to prepare environment, install packages, configure services (systemd), and open firewall/security groups.
   - Verification commands with expected outputs (e.g., curl http://localhost:80 shows HTML or 200; systemctl status SERVICE is active (running); ss -ltnp shows :80 bound).
   - A short rollback note (how to stop/disable service and revert config).` : ''}`);
    const trace = scratchpad.map((e: any, i: number) => `${i + 1}. step=${e.step} tool=${e.tool || 'none'} success=${e.success ? 'true' : 'false'} -> ${(e.observation || '').slice(0, 200)}`).join('\n');
    const human = new HumanMessage(`Task: ${task}
Trace:
${trace || 'None'}

Write the final answer now.`);
    try {
      const resp = await this.llm.invoke([sys, human]);
      return String(resp.content || '').trim();
    } catch {
      return '';
    }
  }

  // Helper: pick a recent URL from prior search steps
  private pickLastSearchUrl(scratchpad: any[]): string | undefined {
    for (let i = scratchpad.length - 1; i >= 0; i--) {
      const it = scratchpad[i];
      const t = String(it?.tool || '').toLowerCase();
      if (t.includes('search')) {
        const top = it?.meta?.top_results;
        if (Array.isArray(top) && top.length && typeof top[0]?.url === 'string') {
          return top[0].url as string;
        }
      }
    }
    return undefined;
  }
}
