/**
 * Configuration loader - reads from .env file
 */

import * as dotenv from 'dotenv';
import * as path from 'path';
import { AppConfig } from '../types';

// Load environment variables
dotenv.config();

/**
 * Load and validate configuration from environment variables
 */
export function loadConfig(): AppConfig {
  const email = process.env.LINKEDIN_EMAIL;
  const password = process.env.LINKEDIN_PASSWORD;

  if (!email || !password) {
    throw new Error(
      'Missing LinkedIn credentials. Please set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env file'
    );
  }

  const keywordsRaw = process.env.SEARCH_KEYWORDS || 'AI Engineer';
  const keywords = keywordsRaw.split(',').map((k) => k.trim()).filter(Boolean);

  if (keywords.length === 0) {
    throw new Error('At least one search keyword is required');
  }

  return {
    linkedin: {
      email,
      password,
    },
    search: {
      keywords,
      maxResults: parseInt(process.env.MAX_RESULTS || '10', 10),
    },
    output: {
      folder: process.env.OUTPUT_FOLDER || './output',
    },
    browser: {
      headless: process.env.HEADLESS === 'true',
      slowMo: parseInt(process.env.SLOW_MO || '100', 10),
    },
  };
}

/**
 * Override config with CLI arguments
 */
export function mergeCliArgs(
  config: AppConfig,
  cliArgs: Partial<{ maxResults?: number; keywords?: string[]; headless?: boolean }>
): AppConfig {
  return {
    ...config,
    search: {
      ...config.search,
      maxResults: cliArgs.maxResults ?? config.search.maxResults,
      keywords: cliArgs.keywords ?? config.search.keywords,
    },
    browser: {
      ...config.browser,
      headless: cliArgs.headless ?? config.browser.headless,
    },
  };
}
