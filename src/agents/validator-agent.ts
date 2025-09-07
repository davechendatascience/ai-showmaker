import { BaseLanguageModel } from '@langchain/core/language_models/base';
import { HumanMessage, SystemMessage } from '@langchain/core/messages';

export type ValidationResult = {
  completed: boolean;
  confidence: number;
  issues?: string[];
  suggested_next_actions?: string[];
  evidence_needed?: string[];
  rationale?: string; // brief reasoning from validator
};

export class ValidatorAgent {
  private llm: BaseLanguageModel;
  constructor(llm: BaseLanguageModel) { this.llm = llm; }

  async validate(task: string, scratchpad: Array<any>): Promise<ValidationResult> {
    const sys = new SystemMessage(`# Role
You are a validator agent for an LLM-based tool-using agent. Judge whether the task is complete using the execution trace, and guide the next step when it is not.

Signals in trace meta to consider:
- extract_len/snippet/error for content extraction quality.
- draft/ draft_has_code/ draft_code_lang/ draft_code_snippet for synthesized answers.
- draft_tests_present/ draft_tests_cases_count/ draft_tests_json_snippet for self-tests presence.
 - draft_ops_checks_present/ draft_ops_snippet for operational checks (Dev/Ops tasks).

Output a strict JSON object with fields:
- completed: boolean
- confidence: number (0-1)
- issues: string[]                     // concrete blockers (e.g., "no code provided", "no problem statement", "extraction 403")
- suggested_next_actions: string[]      // 1-3 specific, high-signal actions, e.g., "extract_data", "design", "implement_code", "test_example", "synthesize_answer", "validate"
- evidence_needed: string[]             // brief artifacts needed (e.g., "problem constraints", "time/space analysis", "working code")
- rationale: string                     // brief reason behind your score

Principles:
- Be conservative: completed=true only if sufficient evidence exists (verified calculation; extracted constraints/examples; synthesized answer grounded in sources; and for coding tasks, runnable code or at least a correct algorithmic solution).
- The suggested_next_actions must be actionable labels (kebab_case or snake_case) that map to agent behaviors: extract_data, analyze, design, implement_code, synthesize_answer, validate, test_example, summarize.
- If no code detected (no draft_has_code and no obvious code in draft), suggest: ["implement_code", "synthesize_answer"].
- If code exists but no testing evidence, suggest adding: ["test_example", "validate"].
- If code and self-tests are present (JSON cases + brief walkthrough), you may accept as complete even without real execution, provided the solution and tests are coherent with the problem statement.
 - For Dev/Ops tasks (deployments, remote servers, Amazon Linux), do NOT accept high-level summaries alone. Require:
   - Concrete shell commands for install/configure/start (e.g., yum/dnf/apt, systemctl, firewall-cmd/ufw).
   - Verification steps with expected outputs (e.g., curl localhost -> 200/HTML snippet; systemctl status -> active (running); port listening via ss -ltnp).
   - If these are missing, mark completed=false and suggest: ["implement_code", "test_example", "synthesize_answer"], where test_example means adding operational checks.
`);
    const trace = scratchpad.map((e: any, i: number) => {
      let extra = '';
      try {
        if (e?.meta?.top_results && Array.isArray(e.meta.top_results) && e.meta.top_results.length) {
          const tops = e.meta.top_results.slice(0, 2).map((r: any) => String(r?.title || '').slice(0, 80)).join(' | ');
          extra += tops ? ` (top: ${tops})` : '';
        }
        if (e?.meta?.content_length) {
          extra += ` (extract_len: ${e.meta.content_length})`;
        }
        if (e?.meta?.snippet) {
          const sn = String(e.meta.snippet);
          extra += ` (snippet: ${sn.slice(0,160)}${sn.length>160?'…':''})`;
        }
        if (e?.meta?.error) {
          const er = String(e.meta.error);
          extra += ` (error: ${er.slice(0,80)}${er.length>80?'…':''})`;
        }
        if (e?.meta?.explanation) {
          const ex = String(e.meta.explanation);
          extra += ` (expl: ${ex.slice(0,120)}${ex.length>120?'…':''})`;
        }
        if (e?.meta?.draft_answer) {
          const da = String(e.meta.draft_answer);
          extra += ` (draft: ${da.slice(0,120)}${da.length>120?'…':''})`;
        }
        if (e?.meta?.draft_has_code) {
          extra += ` (draft_has_code: ${e.meta.draft_has_code ? 'true' : 'false'})`;
        }
        if (e?.meta?.draft_code_lang) {
          extra += ` (code_lang: ${String(e.meta.draft_code_lang).slice(0,20)})`;
        }
        if (e?.meta?.draft_code_snippet) {
          const cs = String(e.meta.draft_code_snippet);
          extra += ` (code: ${cs.slice(0,160)}${cs.length>160?'…':''})`;
        }
        if (e?.meta?.draft_tests_present) {
          extra += ` (tests: ${Number(e.meta.draft_tests_cases_count||0)} cases)`;
          if (e?.meta?.draft_tests_json_snippet) {
            const ts = String(e.meta.draft_tests_json_snippet);
            extra += ` (tests_json: ${ts.slice(0,120)}${ts.length>120?'…':''})`;
          }
        }
        if (e?.meta?.draft_ops_checks_present) {
          extra += ` (ops_checks: yes)`;
          if (e?.meta?.draft_ops_snippet) {
            const os = String(e.meta.draft_ops_snippet);
            extra += ` (ops_snip: ${os.slice(0,120)}${os.length>120?'…':''})`;
          }
        }
      } catch {}
      return `${i + 1}. step=${e.step} tool=${e.tool || 'none'} success=${e.success ? 'true' : 'false'} -> ${(e.observation || '').slice(0, 200)}${extra}`;
    }).join('\n');
    const human = new HumanMessage(`Task: ${task}
Trace:
${trace || 'None'}

Output JSON only. Example:
{"completed": false, "confidence": 0.42, "issues": ["no code provided"], "suggested_next_actions": ["design", "implement_code", "synthesize_answer"], "evidence_needed": ["algorithm outline", "reference solution snippet"]}`);
    try {
      const resp = await this.llm.invoke([sys, human]);
      const txt = String(resp.content || '').trim();
      const jsonStart = txt.indexOf('{');
      const jsonEnd = txt.lastIndexOf('}');
      if (jsonStart >= 0 && jsonEnd > jsonStart) {
        const parsed = JSON.parse(txt.slice(jsonStart, jsonEnd + 1));
        return {
          completed: Boolean(parsed.completed),
          confidence: Number(parsed.confidence) || 0,
          issues: Array.isArray(parsed.issues) ? parsed.issues : [],
          suggested_next_actions: Array.isArray(parsed.suggested_next_actions) ? parsed.suggested_next_actions : [],
          evidence_needed: Array.isArray(parsed.evidence_needed) ? parsed.evidence_needed : [],
          rationale: typeof parsed.rationale === 'string' ? parsed.rationale : undefined,
        };
      }
    } catch {}
    return { completed: false, confidence: 0.0, issues: ['validator_parse_failed'], suggested_next_actions: [], evidence_needed: [] };
  }
}
