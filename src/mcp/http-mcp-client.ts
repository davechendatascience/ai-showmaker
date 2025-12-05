/**
 * HTTP-based MCP Client for communicating with Python MCP servers
 */

import { MCPTool } from '../types';

export interface MCPToolWrapper {
  name: string;
  description: string;
  schema: Record<string, any>;
  execute: (params: Record<string, any>) => Promise<any>;
}

export interface HTTPMCPServer {
  name: string;
  url: string;
  tools: any[];
  isConnected: boolean;
}

export class HTTPMCPClient {
  private servers: Map<string, HTTPMCPServer> = new Map();
  private tools: MCPToolWrapper[] = [];
  private baseUrl: string;
  // Serialize requests to avoid keep-alive/connection reuse edge cases with the simple bridge
  private inflight: Promise<any> | null = null;

  constructor(baseUrl?: string) {
    const envBase = (process.env['MCP_HTTP_BASE'] || '').trim();
    const effective = (baseUrl && baseUrl.trim()) || envBase || 'http://localhost:8000';
    // Normalize: drop trailing slashes
    this.baseUrl = effective.replace(/\/+$/, '');
  }

  /**
   * Initialize the MCP client and discover tools
   */
  async initialize(): Promise<void> {
    console.log('🔍 Initializing HTTP MCP client...');
    
    try {
      await this.discoverTools();
      console.log(`✅ HTTP MCP client initialized with ${this.tools.length} tools`);
    } catch (error) {
      console.error('❌ Failed to initialize HTTP MCP client:', error);
      throw error;
    }
  }

  /**
   * Discover available tools from the HTTP server
   */
  private async discoverTools(): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/tools`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const tools = await response.json() as any[];
      
      // Create server wrapper
      const server: HTTPMCPServer = {
        name: 'http_mcp_server',
        url: this.baseUrl,
        tools: tools,
        isConnected: true,
      };
      
      this.servers.set('http_mcp_server', server);
      
      // Create tool wrappers
      for (const tool of tools) {
        const toolWrapper = this.createToolWrapper(tool);
        this.tools.push(toolWrapper);
      }
      
      console.log(`✅ Discovered ${tools.length} tools from HTTP MCP server`);
      
    } catch (error) {
      console.error('❌ Failed to discover tools:', error);
      throw error;
    }
  }

  /**
   * Create a tool wrapper that can be executed
   */
  private createToolWrapper(tool: MCPTool): MCPToolWrapper {
    return {
      name: tool.name,
      description: tool.description,
      schema: tool.parameters,
      execute: async (params: Record<string, any>): Promise<any> => {
        try {
          console.log(`🛠️ Executing tool ${tool.name} via HTTP with params:`, params);
          
          const body = JSON.stringify({
            tool_name: tool.name,
            // Ensure params is at least an empty object
            params: params ?? {},
          });

          const doFetch = async () => fetch(`${this.baseUrl}/execute`, {
            method: 'POST',
            // Hint the simple Python server not to reuse the socket
            headers: {
              'Content-Type': 'application/json',
              'Connection': 'close',
            },
            body,
          });

          // Retry strategy: handle thrown socket errors and certain 5xx up to 3 attempts
          let response: Response;
          for (let attempt = 1; ; attempt++) {
            try {
              response = await doFetch();
              if (!response.ok && (response.status === 502 || response.status === 503 || response.status === 504)) {
                if (attempt >= 3) break;
                await new Promise(r => setTimeout(r, 150 * attempt));
                continue;
              }
              break;
            } catch (err: any) {
              const code = err?.cause?.code || err?.code;
              const msg = String(err?.message || err);
              const isSocketClose = code === 'UND_ERR_SOCKET' || msg.includes('fetch failed') || msg.includes('other side closed');
              if (attempt >= 3 || !isSocketClose) {
                throw err;
              }
              await new Promise(r => setTimeout(r, 150 * attempt));
              continue;
            }
          }
          
          if (!response.ok) {
            // Surface clear error; do not fall back to GET to avoid double-execution noise
            const text = await response.text().catch(() => '');
            throw new Error(`HTTP ${response.status} ${response.statusText} for ${tool.name}: ${text.slice(0,200)}`);
          }
          
          const result = await response.json();
          console.log(`✅ Tool ${tool.name} executed successfully:`, result);
          return result;
          
        } catch (error) {
          console.error(`❌ Error executing tool ${tool.name}:`, error);
          return { error: `Error executing tool ${tool.name}: ${error}`, success: false };
        }
      },
    };
  }

  /**
   * Get all available tools
   */
  getTools(): MCPToolWrapper[] {
    return [...this.tools];
  }

  /**
   * Get tools by category
   */
  getToolsByCategory(category: string): MCPToolWrapper[] {
    return this.tools.filter(tool => {
      const server = this.servers.get('http_mcp_server');
      return server?.tools.some(t => t.category === category && t.name === tool.name);
    });
  }

  /**
   * Get tools by server
   */
  getToolsByServer(serverName: string): MCPToolWrapper[] {
    return this.tools.filter(tool => {
      const server = this.servers.get('http_mcp_server');
      return server?.tools.some((t: any) => t.server === serverName && t.name === tool.name);
    });
  }

  /**
   * Get all tools grouped by server
   */
  async getAllToolsByServer(): Promise<Record<string, MCPToolWrapper[]>> {
    const toolsByServer: Record<string, MCPToolWrapper[]> = {};
    
    for (const tool of this.tools) {
      // Find which server this tool belongs to
      const server = this.servers.get('http_mcp_server');
      const serverTool = server?.tools.find((t: any) => t.name === tool.name);
      const serverName = serverTool?.server || 'unknown';
      
      if (!toolsByServer[serverName]) {
        toolsByServer[serverName] = [];
      }
      toolsByServer[serverName].push(tool);
    }
    
    return toolsByServer;
  }

  /**
   * Get all servers
   */
  getServers(): HTTPMCPServer[] {
    return Array.from(this.servers.values());
  }

  /**
   * Get server by name
   */
  getServer(name: string): HTTPMCPServer | undefined {
    return this.servers.get(name);
  }

  /**
   * Execute a specific tool
   */
  async executeTool(toolName: string, params: Record<string, any>): Promise<any> {
    const tool = this.tools.find(t => t.name === toolName);
    if (!tool) {
      throw new Error(`Tool ${toolName} not found`);
    }
    // Serialize to avoid socket reuse edge-cases with the minimal Python bridge
    while (this.inflight) {
      try { await this.inflight; } catch { break; }
    }
    const p = tool.execute(params).finally(() => { this.inflight = null; });
    this.inflight = p;
    return await p;
  }

  /**
   * Get tool count
   */
  getToolCount(): number {
    return this.tools.length;
  }

  /**
   * Get server count
   */
  getServerCount(): number {
    return this.servers.size;
  }

  /**
   * Check server health
   */
  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      if (!response.ok) {
        return false;
      }
      const health = await response.json() as any;
      return health.status === 'healthy';
    } catch (error) {
      console.error('❌ Health check failed:', error);
      return false;
    }
  }

  /**
   * Shutdown the client
   */
  async shutdown(): Promise<void> {
    console.log('🛑 Shutting down HTTP MCP client...');
    this.servers.clear();
    this.tools = [];
    console.log('✅ HTTP MCP client stopped');
  }
}
