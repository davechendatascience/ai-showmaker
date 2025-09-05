/**
 * Core types for the AI-Showmaker TypeScript agent
 */

export interface Config {
  inferenceNetKey: string;
  inferenceNetBaseUrl: string;
  inferenceNetModel: string;
  awsHost: string;
  awsUser: string;
  awsKeyPath: string;
}

export interface MCPTool {
  name: string;
  description: string;
  parameters: Record<string, any>;
  category: string;
  version: string;
  timeout: number;
  requiresAuth: boolean;
}

export interface MCPToolExecution {
  toolName: string;
  parameters: Record<string, any>;
  result: any;
  executionTime: number;
  success: boolean;
  error?: string;
}

export interface AgentResponse {
  content: string;
  toolCalls?: MCPToolExecution[];
  metadata: {
    model: string;
    tokensUsed: number;
    executionTime: number;
  };
}

export interface ConversationMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  metadata?: Record<string, any>;
}

export interface AgentState {
  sessionId: string;
  conversationHistory: ConversationMessage[];
  availableTools: MCPTool[];
  currentTask?: string;
  metadata: Record<string, any>;
}

export interface MCPServer {
  name: string;
  version: string;
  description: string;
  tools: MCPTool[];
  isConnected: boolean;
  lastHeartbeat: Date;
}

export interface AgentCapabilities {
  toolExecution: boolean;
  conversationMemory: boolean;
  taskPlanning: boolean;
  webSearch: boolean;
  fileOperations: boolean;
  gitOperations: boolean;
  remoteExecution: boolean;
}
