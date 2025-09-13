import { BaseLanguageModel } from '@langchain/core/language_models/base';
import { HumanMessage, SystemMessage } from '@langchain/core/messages';
import { RichMemoryManager, createRichMemorySystem } from '../core/memory';

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
  private richMemory: RichMemoryManager;
  private sharedMemory: RichMemoryManager; // Alias for compatibility
  
  constructor(llm: BaseLanguageModel, sharedMemory?: RichMemoryManager) { 
    this.llm = llm;
    // Use provided shared memory or create new one
    this.richMemory = sharedMemory || createRichMemorySystem();
    this.sharedMemory = this.richMemory; // Alias for compatibility
  }

  async validate(task: string, _scratchpad: Array<any>): Promise<ValidationResult> {
    const sys = new SystemMessage(`# Role
You are a validator agent for an LLM-based tool-using agent. Judge whether the task is complete using the execution trace from shared memory, and guide the next step when it is not.

Signals in trace meta to consider:
- extract_len/snippet/error for content extraction quality.
- draft/ draft_has_code/ draft_code_lang/ draft_code_snippet for synthesized answers.
- draft_tests_present/ draft_tests_cases_count/ draft_tests_json_snippet for self-tests presence.
 - draft_ops_checks_present/ draft_ops_snippet for operational checks (Dev/Ops tasks).

ENHANCED MEMORY QUERIES (AUTHORITATIVE SOURCE):
- You will receive taskCompletionProof data that contains the definitive evidence
- If taskCompletionProof.hasImplementation = true, the task is COMPLETE (confidence 0.8+)
- If taskCompletionProof.hasFileCreation = true AND taskCompletionProof.hasSynthesis = true, the task is COMPLETE (confidence 0.7+)
- Trust the enhanced memory queries over execution history
- Files with names like "recommendations.md", "final-answer.md", "summary.md" ARE synthesis evidence
- File creation success messages: "written successfully", "created" ARE implementation evidence

Output a strict JSON object with fields:
- completed: boolean
- confidence: number (0-1)
- issues: string[]                     // concrete blockers (e.g., "no code provided", "no problem statement", "extraction 403")
- suggested_next_actions: string[]      // 1-3 specific, high-signal actions, e.g., "extract_data", "design", "implement_code", "test_example", "synthesize_answer", "validate"
- evidence_needed: string[]             // brief artifacts needed (e.g., "problem constraints", "time/space analysis", "working code")
- rationale: string                     // brief reason behind your score

Principles:
- PRIMARY: Use taskCompletionProof data as the authoritative source of truth
- If taskCompletionProof.hasImplementation = true, mark completed=true with confidence 0.8+
- If taskCompletionProof.hasFileCreation = true AND taskCompletionProof.hasSynthesis = true, mark completed=true with confidence 0.7+
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
    
    // Get execution history from shared memory with enhanced querying
    const executionHistory = this.sharedMemory.queryMemories({
      types: ['execution', 'validation', 'error'],
      maxResults: 20
    });

    // Get task completion proof using enhanced indexing
    const taskCompletionProof = this.sharedMemory.getTaskCompletionProof();

    // Build trace from shared memory with enhanced metadata
    const trace = executionHistory.map((entry: any, i: number) => {
      let extra = '';
      try {
        // Parse the content to extract metadata if available
        const content = entry.content;
        if (content.includes('tool=')) {
          const toolMatch = content.match(/tool=([^ ]+)/);
          if (toolMatch) extra += ` (tool: ${toolMatch[1]})`;
        }
        if (content.includes('Success:')) {
          const successMatch = content.match(/Success: (true|false)/);
          if (successMatch) extra += ` (success: ${successMatch[1]})`;
        }
        if (entry.metadata.tool) {
          extra += ` (tool: ${entry.metadata.tool})`;
        }
        if (entry.metadata.success !== undefined) {
          extra += ` (success: ${entry.metadata.success})`;
        }
      } catch {}
      return `${i + 1}. ${entry.content}${extra}`;
    }).join('\n');
    
    const human = new HumanMessage(`Task: ${task}

TASK COMPLETION PROOF ANALYSIS (PRIMARY EVIDENCE):
${JSON.stringify(taskCompletionProof, null, 2)}

EXECUTION HISTORY (SECONDARY REFERENCE):
${trace || 'No execution history found'}

CRITICAL ANALYSIS - USE ENHANCED MEMORY QUERIES:
1. PRIMARY: Check taskCompletionProof?.hasImplementation - if true, task is COMPLETE
2. PRIMARY: Check taskCompletionProof?.hasFileCreation AND taskCompletionProof?.hasSynthesis - if both true, task is COMPLETE
3. SECONDARY: Look at execution history for additional context
4. The enhanced memory queries are the AUTHORITATIVE source of truth

EVIDENCE DETECTION (Enhanced):
- File creation: ${taskCompletionProof?.hasFileCreation ? '✅ DETECTED' : '❌ NOT FOUND'} (${taskCompletionProof?.fileCreationEntries?.length || 0} entries)
- Synthesis evidence: ${taskCompletionProof?.hasSynthesis ? '✅ DETECTED' : '❌ NOT FOUND'} (${taskCompletionProof?.synthesisEntries?.length || 0} entries)
- Implementation evidence: ${taskCompletionProof?.hasImplementation ? '✅ DETECTED' : '❌ NOT FOUND'}
- Completion evidence: ${taskCompletionProof?.completionEntries?.length || 0} completion entries found

COMPLETION CRITERIA (ENHANCED MEMORY ANALYSIS):
- If taskCompletionProof?.hasImplementation = true, the task is COMPLETE (high confidence 0.8+)
- If taskCompletionProof?.hasFileCreation = true AND taskCompletionProof?.hasSynthesis = true, the task is COMPLETE (high confidence 0.4+)
- Files like "recommendations.md", "final-answer.md", "task_summary.md" ARE synthesis evidence
- The presence of these files with content IS actionable recommendations
- The enhanced memory queries provide PROOF OF WORK - trust the evidence they provide

Current Issues to Check:
- If you see only planning steps without execution, the task is incomplete
- If no code files are mentioned as created, mark as incomplete
- If no final answer is synthesized, mark as incomplete
- If the same suggestions repeat, the agent is stuck in a loop
- If files are created but no synthesis document exists, suggest synthesis

CRITICAL: The taskCompletionProof data above is the AUTHORITATIVE source of truth. 
- If hasImplementation=true, mark completed=true with confidence 0.8+
- If hasFileCreation=true AND hasSynthesis=true, mark completed=true with confidence 0.7+
- IGNORE the execution history if it conflicts with the enhanced memory queries

Output JSON only. Example:
{"completed": true, "confidence": 0.8, "issues": [], "suggested_next_actions": [], "evidence_needed": [], "rationale": "Task complete - implementation evidence detected via enhanced memory queries"}`);
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
