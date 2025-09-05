import { BaseMessage, HumanMessage, AIMessage, SystemMessage } from '@langchain/core/messages';

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: Date;
    metadata?: Record<string, any>;
}

export interface AgentSession {
    id: string;
    name: string;
    createdAt: Date;
    lastActivity: Date;
    messages: ChatMessage[];
    context: Record<string, any>;
    status: 'active' | 'completed' | 'paused' | 'error';
}

export interface SessionConfig {
    maxMessages?: number;
    maxContextLength?: number;
    persistHistory?: boolean;
    sessionTimeout?: number; // in milliseconds
}

export class SessionManager {
    private sessions: Map<string, AgentSession> = new Map();
    private config: SessionConfig;

    constructor(config: SessionConfig = {}) {
        this.config = {
            maxMessages: 100,
            maxContextLength: 4000,
            persistHistory: true,
            sessionTimeout: 30 * 60 * 1000, // 30 minutes
            ...config
        };
    }

    /**
     * Create a new agent session
     */
    createSession(name: string, systemPrompt?: string): AgentSession {
        const sessionId = this.generateSessionId();
        const session: AgentSession = {
            id: sessionId,
            name,
            createdAt: new Date(),
            lastActivity: new Date(),
            messages: [],
            context: {},
            status: 'active'
        };

        // Add system message if provided
        if (systemPrompt) {
            this.addMessage(sessionId, {
                role: 'system',
                content: systemPrompt
            });
        }

        this.sessions.set(sessionId, session);
        console.log(`📝 Created new session: ${sessionId} (${name})`);
        return session;
    }

    /**
     * Get session by ID
     */
    getSession(sessionId: string): AgentSession | undefined {
        const session = this.sessions.get(sessionId);
        if (session) {
            session.lastActivity = new Date();
        }
        return session;
    }

    /**
     * Add a message to a session
     */
    addMessage(sessionId: string, message: Omit<ChatMessage, 'id' | 'timestamp'>): ChatMessage {
        const session = this.sessions.get(sessionId);
        if (!session) {
            throw new Error(`Session ${sessionId} not found`);
        }

        const chatMessage: ChatMessage = {
            id: this.generateMessageId(),
            timestamp: new Date(),
            ...message
        };

        session.messages.push(chatMessage);
        session.lastActivity = new Date();

        // Trim messages if over limit
        if (this.config.maxMessages && session.messages.length > this.config.maxMessages) {
            session.messages = session.messages.slice(-this.config.maxMessages);
        }

        console.log(`💬 Added ${message.role} message to session ${sessionId}`);
        return chatMessage;
    }

    /**
     * Get conversation history for a session
     */
    getConversationHistory(sessionId: string): ChatMessage[] {
        const session = this.sessions.get(sessionId);
        return session ? session.messages : [];
    }

    /**
     * Convert chat messages to LangChain messages
     */
    getLangChainMessages(sessionId: string): BaseMessage[] {
        const messages = this.getConversationHistory(sessionId);
        return messages.map(msg => {
            switch (msg.role) {
                case 'user':
                    return new HumanMessage(msg.content);
                case 'assistant':
                    return new AIMessage(msg.content);
                case 'system':
                    return new SystemMessage(msg.content);
                default:
                    return new HumanMessage(msg.content);
            }
        });
    }

    /**
     * Update session context
     */
    updateContext(sessionId: string, context: Record<string, any>): void {
        const session = this.sessions.get(sessionId);
        if (!session) {
            throw new Error(`Session ${sessionId} not found`);
        }

        session.context = { ...session.context, ...context };
        session.lastActivity = new Date();
    }

    /**
     * Get session context
     */
    getContext(sessionId: string): Record<string, any> {
        const session = this.sessions.get(sessionId);
        return session ? session.context : {};
    }

    /**
     * Update session status
     */
    updateStatus(sessionId: string, status: AgentSession['status']): void {
        const session = this.sessions.get(sessionId);
        if (!session) {
            throw new Error(`Session ${sessionId} not found`);
        }

        session.status = status;
        session.lastActivity = new Date();
        console.log(`📊 Updated session ${sessionId} status to: ${status}`);
    }

    /**
     * List all active sessions
     */
    listSessions(): AgentSession[] {
        return Array.from(this.sessions.values());
    }

    /**
     * List active sessions only
     */
    listActiveSessions(): AgentSession[] {
        return this.listSessions().filter(session => session.status === 'active');
    }

    /**
     * Clean up expired sessions
     */
    cleanupExpiredSessions(): number {
        const now = new Date();
        const expiredSessions: string[] = [];

        for (const [sessionId, session] of this.sessions.entries()) {
            const timeSinceActivity = now.getTime() - session.lastActivity.getTime();
            if (timeSinceActivity > this.config.sessionTimeout!) {
                expiredSessions.push(sessionId);
            }
        }

        expiredSessions.forEach(sessionId => {
            this.sessions.delete(sessionId);
            console.log(`🧹 Cleaned up expired session: ${sessionId}`);
        });

        return expiredSessions.length;
    }

    /**
     * Delete a session
     */
    deleteSession(sessionId: string): boolean {
        const deleted = this.sessions.delete(sessionId);
        if (deleted) {
            console.log(`🗑️ Deleted session: ${sessionId}`);
        }
        return deleted;
    }

    /**
     * Get session statistics
     */
    getSessionStats(sessionId: string): {
        messageCount: number;
        userMessages: number;
        assistantMessages: number;
        systemMessages: number;
        duration: number; // in minutes
        status: string;
    } | null {
        const session = this.sessions.get(sessionId);
        if (!session) return null;

        const messages = session.messages;
        const now = new Date();
        const duration = (now.getTime() - session.createdAt.getTime()) / (1000 * 60); // minutes

        return {
            messageCount: messages.length,
            userMessages: messages.filter(m => m.role === 'user').length,
            assistantMessages: messages.filter(m => m.role === 'assistant').length,
            systemMessages: messages.filter(m => m.role === 'system').length,
            duration: Math.round(duration * 100) / 100,
            status: session.status
        };
    }

    /**
     * Generate unique session ID
     */
    private generateSessionId(): string {
        return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Generate unique message ID
     */
    private generateMessageId(): string {
        return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
}
