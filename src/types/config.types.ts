/**
 * Configuration types for the LinkedIn job scraper
 */

export interface AppConfig {
  linkedin: LinkedInCredentials;
  search: SearchConfig;
  output: OutputConfig;
  browser: BrowserConfig;
}

export interface LinkedInCredentials {
  email: string;
  password: string;
}

export interface SearchConfig {
  keywords: string[];
  maxResults: number;
}

export interface OutputConfig {
  folder: string;
}

export interface BrowserConfig {
  headless: boolean;
  slowMo: number;
}
