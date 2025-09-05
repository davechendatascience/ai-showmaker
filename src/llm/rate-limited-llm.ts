import { InferenceNetLLM } from './inference-net-llm';
import { BaseMessage } from '@langchain/core/messages';

export interface RateLimitedLLMConfig {
    apiKey: string;
    model: string;
    temperature?: number;
    maxTokens?: number;
    requestsPerMinute?: number;
    maxRetries?: number;
    retryDelayMs?: number;
}

export class RateLimitedLLM extends InferenceNetLLM {
    private requestTimes: number[] = [];
    private requestsPerMinute: number;
    private maxRetries: number;
    private retryDelayMs: number;

    constructor(config: RateLimitedLLMConfig) {
        super({
            apiKey: config.apiKey,
            model: config.model,
            temperature: config.temperature || 0.1,
            maxTokens: config.maxTokens || 1000
        });
        
        this.requestsPerMinute = config.requestsPerMinute || 10; // Conservative default
        this.maxRetries = config.maxRetries || 3;
        this.retryDelayMs = config.retryDelayMs || 2000; // 2 seconds
    }

    override async invoke(messages: string | BaseMessage[]): Promise<any> {
        return this.executeWithRateLimit(async () => {
            return super.invoke(messages);
        });
    }

    private async executeWithRateLimit<T>(operation: () => Promise<T>): Promise<T> {
        let lastError: Error | null = null;
        
        for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
            try {
                // Check rate limit
                await this.enforceRateLimit();
                
                // Execute the operation
                const result = await operation();
                
                // Record successful request
                this.recordRequest();
                
                return result;
                
            } catch (error: any) {
                lastError = error;
                
                // Check if it's a rate limit error
                if (error.message?.includes('429') || error.message?.includes('Rate limit')) {
                    console.log(`   ⏳ Rate limited (attempt ${attempt + 1}/${this.maxRetries + 1}), waiting ${this.retryDelayMs}ms...`);
                    
                    if (attempt < this.maxRetries) {
                        await this.delay(this.retryDelayMs * (attempt + 1)); // Exponential backoff
                        continue;
                    }
                }
                
                // If not a rate limit error, or max retries reached, throw
                throw error;
            }
        }
        
        throw lastError;
    }

    private async enforceRateLimit(): Promise<void> {
        const now = Date.now();
        const oneMinuteAgo = now - 60000;
        
        // Remove old requests
        this.requestTimes = this.requestTimes.filter(time => time > oneMinuteAgo);
        
        // Check if we're at the limit
        if (this.requestTimes.length >= this.requestsPerMinute) {
            const oldestRequest = Math.min(...this.requestTimes);
            const waitTime = 60000 - (now - oldestRequest) + 1000; // Add 1 second buffer
            
            console.log(`   ⏳ Rate limit reached, waiting ${Math.ceil(waitTime / 1000)} seconds...`);
            await this.delay(waitTime);
        }
    }

    private recordRequest(): void {
        this.requestTimes.push(Date.now());
    }

    private delay(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    getRequestStats(): { requestsInLastMinute: number; requestsPerMinute: number } {
        const now = Date.now();
        const oneMinuteAgo = now - 60000;
        const recentRequests = this.requestTimes.filter(time => time > oneMinuteAgo);
        
        return {
            requestsInLastMinute: recentRequests.length,
            requestsPerMinute: this.requestsPerMinute
        };
    }
}
