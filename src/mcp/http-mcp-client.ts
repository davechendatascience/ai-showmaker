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

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
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
          
          const response = await fetch(`${this.baseUrl}/execute`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              tool_name: tool.name,
              params: params,
            }),
          });
          
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
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

    return await tool.execute(params);
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
