/**
 * Main entry point for AI-Showmaker TypeScript Agent
 */

import { ConfigManager } from './core/config';
import { AIAgent } from './core/agent';

async function main() {
  console.log('🚀 Starting AI-Showmaker TypeScript Agent...');
  console.log('='.repeat(60));
  
  try {
    // Initialize configuration
    console.log('📋 Initializing configuration...');
    const config = new ConfigManager();
    console.log('✅ Configuration loaded');
    
    // Show configuration summary
    const configSummary = config.getSummary();
    console.log('📊 Configuration summary:', configSummary);
    
    // Initialize AI Agent
    console.log('\n🤖 Initializing AI Agent...');
    const agent = new AIAgent(config);
    await agent.initialize();
    
    // Show agent capabilities
    const capabilities = agent.getCapabilities();
    console.log('🔧 Agent capabilities:', capabilities);
    
    // Show available tools
    const tools = agent.getAvailableTools();
    console.log(`🛠️ Available tools (${tools.length}):`, tools.map(t => t.name));
    
    // Test the agent with a simple query
    console.log('\n🧪 Testing agent with simple query...');
    const response = await agent.query('What tools do you have available?');
    console.log('🤖 Agent response:', response.content);
    
    // Test tool execution
    console.log('\n🧪 Testing tool execution...');
    if (tools.length > 0) {
      const firstTool = tools[0];
      if (firstTool) {
        console.log(`🛠️ Executing tool: ${firstTool.name}`);
        const toolResult = await agent.executeTool(firstTool.name, { test: 'parameter' });
        console.log('✅ Tool result:', toolResult);
      }
    }
    
    // Show conversation history
    console.log('\n📚 Conversation history:');
    const history = agent.getConversationHistory();
    history.forEach((msg, index) => {
      console.log(`${index + 1}. [${msg.role.toUpperCase()}] ${msg.content}`);
    });
    
    // Show agent state
    console.log('\n📊 Agent state:');
    const state = agent.getState();
    console.log('Session ID:', state.sessionId);
    console.log('Version:', state.metadata['version']);
    console.log('Start time:', state.metadata['startTime']);
    
    // Cleanup
    console.log('\n🧹 Cleaning up...');
    await agent.cleanup();
    
    console.log('\n✅ AI-Showmaker TypeScript Agent demo completed successfully!');
    
  } catch (error) {
    console.error('❌ Error in main:', error);
    process.exit(1);
  }
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n🛑 Received SIGINT, shutting down gracefully...');
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\n🛑 Received SIGTERM, shutting down gracefully...');
  process.exit(0);
});

// Run the main function
if (require.main === module) {
  main().catch(error => {
    console.error('❌ Unhandled error:', error);
    process.exit(1);
  });
}
