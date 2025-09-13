# Enhanced Best-First Search Agent Framework

## Overview

The Enhanced Best-First Search Agent is a sophisticated evolution of the original best-first search agent that incorporates advanced state management, scenario prediction, and validator integration. This framework addresses the limitations of the original hardcoded approach by providing a flexible, extensible system for handling complex task execution scenarios.

## Key Features

### 1. Scenario Prediction System
- **Pre-execution Analysis**: Predicts likely outcomes before tool execution
- **Multiple Scenario Types**: Handles SUCCESS, PARTIAL_SUCCESS, VALIDATION_ERROR, CONNECTION_ERROR, TIMEOUT, and more
- **Probability-based Planning**: Uses scenario probabilities to make informed decisions
- **Learning from Outcomes**: Improves predictions based on actual execution results

### 2. Enhanced State Management
- **Comprehensive State Tracking**: Maintains detailed execution state including metrics, validator feedback, and scenario predictions
- **State History**: Keeps track of state evolution over time for analysis and debugging
- **State Snapshots**: Allows rollback and analysis of previous states
- **Performance Metrics**: Tracks success rates, execution times, and prediction accuracy

### 3. Advanced Validator Integration
- **Dynamic Score Modification**: Adjusts plan scores based on validator feedback
- **Hint Alignment**: Boosts scores for plans that align with validator suggestions
- **Issue Resolution**: Prioritizes plans that address validator-identified issues
- **Confidence Tracking**: Monitors validator confidence trends over time

### 4. Intelligent Search Algorithm
- **Scenario-aware Planning**: Considers predicted scenarios when generating plans
- **Adaptive Scoring**: Adjusts scoring based on scenario predictions and validator feedback
- **Frontier Management**: Enhanced frontier management with scenario considerations
- **Execution Optimization**: Optimizes execution based on predicted outcomes

## Architecture

### Core Components

```
EnhancedBestFirstSearchAgent
├── State Management
│   ├── SearchState
│   ├── PlanNode (Enhanced)
│   ├── ExecutionEntry (Enhanced)
│   └── State History
├── Scenario Prediction
│   ├── ScenarioPrediction
│   ├── ToolScenario
│   ├── Scenario Cache
│   └── Learning System
├── Validator Integration
│   ├── ValidatorState
│   ├── ValidationResult Processing
│   └── Score Modification
└── Search Algorithm
    ├── Enhanced Planning
    ├── Scenario-aware Scoring
    └── Execution Handling
```

### Type System

The framework uses a comprehensive TypeScript type system defined in `src/types/enhanced-state.ts`:

- **SearchState**: Complete agent state including frontier, scratchpad, validator state, and metrics
- **PlanNode**: Enhanced plan representation with scenario predictions and validator integration
- **ToolScenario**: Detailed scenario representation with probabilities, outcomes, and impacts
- **ValidatorIntegration**: Validator feedback integration data
- **SearchMetrics**: Performance and efficiency metrics

## Configuration

### Environment Variables

The enhanced agent can be configured through environment variables:

```bash
# Enable Enhanced Agent
USE_ENHANCED_AGENT=true

# Scenario Prediction Configuration
BFS_SCENARIO_PREDICTION=true
BFS_MAX_SCENARIOS=5
BFS_MIN_PROBABILITY=0.1
BFS_PREDICTION_CONFIDENCE=0.6
BFS_LEARN_FROM_OUTCOMES=true
BFS_CACHE_DURATION=300000

# Enhanced Validator Configuration
BFS_VALIDATOR_EVERY=1
BFS_VALIDATOR_CONF=0.7
BFS_VALIDATOR_MODE=action
BFS_VALUE_TRIGGER=0.8
BFS_VALIDATION_COOLDOWN=2
BFS_HINT_BOOST=0.35
BFS_SPECIAL_HINT_BOOST=0.1
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_ENHANCED_AGENT` | `false` | Enable the enhanced agent |
| `BFS_SCENARIO_PREDICTION` | `true` | Enable scenario prediction |
| `BFS_MAX_SCENARIOS` | `5` | Maximum scenarios per tool |
| `BFS_MIN_PROBABILITY` | `0.1` | Minimum scenario probability threshold |
| `BFS_PREDICTION_CONFIDENCE` | `0.6` | Minimum prediction confidence |
| `BFS_LEARN_FROM_OUTCOMES` | `true` | Enable learning from actual outcomes |
| `BFS_CACHE_DURATION` | `300000` | Scenario cache duration (ms) |

## Usage

### Basic Usage

```typescript
import { EnhancedBestFirstSearchAgent } from './agents/enhanced-best-first-search-agent';

const agent = new EnhancedBestFirstSearchAgent(mcpClient, llm, sessionManager);
const result = await agent.executeTask("Your task here", sessionId);
```

### State Access

```typescript
// Get current state
const state = agent.getState();

// Get state history
const history = agent.getStateHistory();

// Get scenario cache
const cache = agent.getScenarioCache();
```

### Interactive Commands

When using the interactive app, additional commands are available:

- `state` - Show enhanced agent state and metrics
- `scenarios` - Display scenario prediction cache
- `help` - Show all available commands including enhanced features

## Scenario Types

The framework supports the following scenario types:

| Scenario Type | Description | Typical Probability |
|---------------|-------------|-------------------|
| `SUCCESS` | Tool executes successfully | 0.7 |
| `PARTIAL_SUCCESS` | Tool partially succeeds | 0.15 |
| `VALIDATION_ERROR` | Input validation fails | 0.05 |
| `SECURITY_ERROR` | Security restrictions | 0.02 |
| `CONNECTION_ERROR` | Network/connection issues | 0.03 |
| `TIMEOUT` | Tool execution times out | 0.02 |
| `TOOL_NOT_FOUND` | Tool doesn't exist | 0.01 |
| `UNKNOWN_ERROR` | Unexpected error | 0.01 |
| `RATE_LIMITED` | Rate limiting | 0.01 |
| `INSUFFICIENT_DATA` | Not enough data | 0.02 |
| `CANCELLED` | Operation cancelled | 0.01 |

## Validator Integration

The enhanced agent provides sophisticated validator integration:

### Score Modification
- Plans aligned with validator hints receive score boosts
- Plans addressing validator issues get priority
- Special handling for test_example and implement_code actions

### Confidence Tracking
- Monitors validator confidence trends
- Adjusts behavior based on confidence levels
- Implements validation cooldowns to prevent over-validation

### Hint Processing
- Processes validator suggestions for next actions
- Aligns plan generation with validator guidance
- Tracks hint effectiveness over time

## Performance Metrics

The framework tracks comprehensive performance metrics:

- **Total Iterations**: Number of search iterations
- **Plans Generated**: Total plans created
- **Plans Executed**: Total plans executed
- **Average Execution Time**: Mean execution time per plan
- **Success Rate**: Percentage of successful executions
- **Validator Interactions**: Number of validator calls
- **Prediction Accuracy**: Accuracy of scenario predictions
- **Efficiency Score**: Overall search efficiency

## Learning System

The enhanced agent includes a learning system that:

1. **Tracks Actual Outcomes**: Records which scenarios actually occur
2. **Updates Probabilities**: Adjusts scenario probabilities based on outcomes
3. **Improves Predictions**: Enhances future predictions based on historical data
4. **Caches Results**: Maintains prediction cache for performance

## Error Handling

The framework includes comprehensive error handling:

- **StateManagementError**: General state management errors
- **ScenarioPredictionError**: Scenario prediction specific errors
- **ValidatorIntegrationError**: Validator integration errors

## Integration with MCP Servers

The enhanced agent works seamlessly with existing MCP servers:

- **Response Code Handling**: Processes MCP server response codes and error types
- **Metadata Extraction**: Extracts and utilizes server metadata
- **Tool-specific Scenarios**: Generates scenarios based on tool capabilities
- **Performance Monitoring**: Tracks tool execution performance

## Future Enhancements

Potential areas for future development:

1. **Machine Learning Integration**: Use ML models for scenario prediction
2. **Advanced Caching**: Implement more sophisticated caching strategies
3. **Multi-agent Coordination**: Support for multiple agent coordination
4. **Real-time Adaptation**: Dynamic parameter adjustment based on performance
5. **Visualization**: Tools for visualizing agent state and decision trees

## Troubleshooting

### Common Issues

1. **High Memory Usage**: Reduce `BFS_CACHE_DURATION` or disable scenario prediction
2. **Slow Performance**: Adjust `BFS_MAX_SCENARIOS` or `BFS_BEAM_WIDTH`
3. **Poor Predictions**: Enable `BFS_LEARN_FROM_OUTCOMES` and run more iterations
4. **Validator Conflicts**: Adjust validator configuration parameters

### Debug Mode

Enable debug mode for detailed logging:

```bash
BFS_DEBUG=true
```

This will provide detailed information about:
- Plan selection and scoring
- Scenario predictions
- Validator interactions
- State transitions

## Conclusion

The Enhanced Best-First Search Agent framework provides a robust, extensible foundation for complex task execution with advanced state management, scenario prediction, and validator integration. It addresses the limitations of hardcoded approaches while maintaining compatibility with existing MCP infrastructure.

The framework is designed to be:
- **Extensible**: Easy to add new scenario types and features
- **Configurable**: Highly tunable through environment variables
- **Observable**: Comprehensive state tracking and metrics
- **Learnable**: Improves performance over time
- **Compatible**: Works with existing MCP servers and tools
