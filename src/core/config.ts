/**
 * Configuration manager for the AI-Showmaker agent
 */

import { Config } from '../types';
import * as dotenv from 'dotenv';
import * as path from 'path';

export class ConfigManager {
  private config!: Config;
  private envPath: string;

  constructor(envPath?: string) {
    this.envPath = envPath || path.join(process.cwd(), '.env');
    this.loadConfig();
  }

  private loadConfig(): void {
    // Load environment variables
    dotenv.config({ path: this.envPath });

    // Validate and set configuration
    this.config = {
      inferenceNetKey: this.getRequiredEnvVar('INFERENCE_NET_KEY'),
      inferenceNetBaseUrl: this.getEnvVar('INFERENCE_NET_BASE_URL', 'https://api.inference.net/v1'),
      inferenceNetModel: this.getEnvVar('INFERENCE_NET_MODEL', 'meta-llama/llama-3.2-3b-instruct/fp-16'),
      awsHost: this.getRequiredEnvVar('AWS_HOST'),
      awsUser: this.getRequiredEnvVar('AWS_USER'),
      awsKeyPath: this.getRequiredEnvVar('AWS_KEY_PATH'),
    };

    this.validateConfig();
  }

  private getRequiredEnvVar(key: string): string {
    const value = process.env[key];
    if (!value) {
      throw new Error(`Required environment variable ${key} is not set`);
    }
    return value;
  }

  private getEnvVar(key: string, defaultValue: string): string {
    return process.env[key] || defaultValue;
  }

  private validateConfig(): void {
    if (!this.config.inferenceNetKey) {
      throw new Error('INFERENCE_NET_KEY is required');
    }

    if (!this.config.awsHost) {
      throw new Error('AWS_HOST is required');
    }

    if (!this.config.awsUser) {
      throw new Error('AWS_USER is required');
    }

    if (!this.config.awsKeyPath) {
      throw new Error('AWS_KEY_PATH is required');
    }
  }

  /**
   * Get the entire configuration object
   */
  getConfig(): Config {
    return { ...this.config };
  }

  /**
   * Get a specific configuration value
   */
  get<K extends keyof Config>(key: K): Config[K] {
    return this.config[key];
  }

  /**
   * Check if a configuration key exists
   */
  has(key: keyof Config): boolean {
    return key in this.config;
  }

  /**
   * Get all configuration keys
   */
  getKeys(): (keyof Config)[] {
    return Object.keys(this.config) as (keyof Config)[];
  }

  /**
   * Reload configuration from environment
   */
  reload(): void {
    this.loadConfig();
  }

  /**
   * Get configuration summary (without sensitive data)
   */
  getSummary(): Omit<Config, 'inferenceNetKey'> & { inferenceNetKey: string } {
    return {
      ...this.config,
      inferenceNetKey: this.config.inferenceNetKey ? '***' : 'Not set',
    };
  }
}
