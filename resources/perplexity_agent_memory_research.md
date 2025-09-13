A robust shared memory for agentic workflows should be composed of several distinct contextual information types that support rich retrieval, reasoning, and synchronized state between cooperating agents (main/validator). The central store should be modular and hold both short-term and long-term contexts, blending structured fields with semantic records for versatility.

Components of Shared Memory
Short-Term Context Buffer

Last N interactions/messages (window buffer)

Active tool calls, running subtasks, and latest results

Current user/system instructions or task objectives

Long-Term Memory Store

Persistent project state (files, specs, configs)

Key facts, domain knowledge, background docs

Chronological action/event log (successes, failures, decisions)

Indexed validation outcomes with timestamps and feedback

Auxiliary Context Elements

Entity state registry (e.g., function definitions, dataset locations, variable states)

Knowledge graph nodes (relationships between tasks, inputs, outputs, agents)

Semantic embeddings for natural language/contextual search

Reflection/summarization records written by agents for faster recall, adaptation, and troubleshooting

Rich Contextual Information Types for Retrieval
Information Type	Role in Memory	Retrieval Use Case
Intent/objective buffer	Keeps agents goal-aligned	Task expansion, validation rationale
Task state + active steps	Provides ‘now’ context	Resumability, agent sync, error tracing
Interaction history	Conversational coherence	Prompt construction, context recovery
Validation log	Feedback/bias for scoring	Retry logic, branch pruning
Knowledge graph (entities)	Relational, multi-hop reasoning	Complex query answering, code synthesis
Semantic search embeddings	Natural lang. retrieval	Fuzzy/contextual queries, non-exact match
External resource links	Data and code lookup	Document/code-based workflows, compliance
Reflection/summarization	Adaptive learning	Rapid state sync, meta-reasoning
Memory Structure Outline
text
Central Store (Shared Memory)
├─ Short-Term Buffer:   {recent messages, current action, input/output, task meta}
├─ Long-Term Records:   {validation log, structured state, knowledge snapshots, file registry}
├─ Knowledge Graph:     {entities, relationships, process dependencies}
├─ Semantic Index:      {document/interaction embeddings, context vectors}
├─ Reflection/Summary:  {agent-authored meta, lessons, workflow adaptation notes}
Best Practices
Store validation results with context, state, and reasoning links so both main and validator agents share not just outcomes, but the why and how for later retrieval and branch selection.

Use graph-based structures for high-complexity, multi-agent workflows and vector/key-value stores to speed up semantic and exact queries.

Periodically update summaries and reflection notes to maintain a coherent and adaptive memory state.

This multifaceted context design ensures that all agents can align on goals, adaptively recover state, validate efficiently, and operate with deep shared context and observability.

