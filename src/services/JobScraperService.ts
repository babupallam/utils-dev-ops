/**
 * Main scraping service that orchestrates the job scraping workflow
 */

import { chromium, Browser, BrowserContext, Page } from 'playwright';
import { AppConfig, JobListing, JobDetails } from '../types';
import { LoginPage, JobSearchPage, JobDetailsPage } from '../pages';
import { logger, saveJobToMarkdown } from '../utils';

export class JobScraperService {
  private config: AppConfig;
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private page: Page | null = null;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /**
   * Initialize the browser and context
   */
  async initialize(): Promise<void> {
    logger.info('Initializing browser...');

    this.browser = await chromium.launch({
      headless: this.config.browser.headless,
      slowMo: this.config.browser.slowMo,
    });

    this.context = await this.browser.newContext({
      viewport: { width: 1280, height: 800 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    });

    this.page = await this.context.newPage();
    
    logger.info('Browser initialized successfully');
  }

  /**
   * Clean up browser resources
   */
  async cleanup(): Promise<void> {
    logger.info('Cleaning up browser...');
    
    if (this.context) {
      await this.context.close();
    }
    if (this.browser) {
      await this.browser.close();
    }

    this.page = null;
    this.context = null;
    this.browser = null;

    logger.info('Browser cleanup complete');
  }

  /**
   * Perform login to LinkedIn
   */
  async login(): Promise<boolean> {
    if (!this.page) {
      throw new Error('Browser not initialized. Call initialize() first.');
    }

    const loginPage = new LoginPage(this.page);
    return await loginPage.login(this.config.linkedin);
  }

  /**
   * Search and scrape jobs for all configured keywords
   */
  async scrapeJobs(): Promise<JobDetails[]> {
    if (!this.page) {
      throw new Error('Browser not initialized. Call initialize() first.');
    }

    const allJobs: JobDetails[] = [];
    const { keywords, maxResults } = this.config.search;

    // Calculate jobs per keyword (distribute maxResults among keywords)
    const jobsPerKeyword = Math.ceil(maxResults / keywords.length);

    for (const keyword of keywords) {
      logger.info(`\n========================================`);
      logger.info(`Searching for: "${keyword}"`);
      logger.info(`========================================\n`);

      try {
        const jobs = await this.scrapeJobsForKeyword(keyword, jobsPerKeyword);
        allJobs.push(...jobs);

        // Check if we've reached the total limit
        if (allJobs.length >= maxResults) {
          logger.info(`Reached maximum results limit (${maxResults})`);
          break;
        }

        // Small delay between keywords
        await this.page.waitForTimeout(2000);

      } catch (error) {
        logger.error(`Error scraping jobs for "${keyword}": ${error}`);
      }
    }

    // Trim to exact max results
    return allJobs.slice(0, maxResults);
  }

  /**
   * Search and scrape jobs for a single keyword
   */
  private async scrapeJobsForKeyword(keyword: string, maxJobs: number): Promise<JobDetails[]> {
    if (!this.page) {
      throw new Error('Browser not initialized');
    }

    const jobSearchPage = new JobSearchPage(this.page);
    const jobDetailsPage = new JobDetailsPage(this.page);
    const jobs: JobDetails[] = [];

    // Search for jobs
    await jobSearchPage.searchJobs(keyword);

    // Check for no results
    if (await jobSearchPage.hasNoResults()) {
      logger.warn(`No jobs found for "${keyword}"`);
      return jobs;
    }

    // Sort by most recent
    await jobSearchPage.sortByMostRecent();

    // Get job listings
    const listings = await jobSearchPage.getJobListings(maxJobs);
    logger.info(`Found ${listings.length} job listings for "${keyword}"`);

    // Get details for each job
    for (let i = 0; i < listings.length; i++) {
      const listing = listings[i];
      
      try {
        logger.info(`\n[${i + 1}/${listings.length}] Processing: ${listing.title} at ${listing.company}`);

        // Get full job details
        const details = await jobDetailsPage.getJobDetails(listing);

        // Save to markdown immediately
        saveJobToMarkdown(details, this.config.output.folder);

        jobs.push(details);

        // Small delay between job pages
        await this.page.waitForTimeout(1000 + Math.random() * 1000);

      } catch (error) {
        logger.error(`Error processing job at ${listing.company}: ${error}`);
      }
    }

    return jobs;
  }

  /**
   * Run the complete scraping workflow
   */
  async run(): Promise<JobDetails[]> {
    try {
      // Initialize browser
      await this.initialize();

      // Login to LinkedIn
      const loginSuccess = await this.login();
      if (!loginSuccess) {
        throw new Error('Failed to login to LinkedIn');
      }

      // Scrape jobs
      const jobs = await this.scrapeJobs();

      logger.info(`\n========================================`);
      logger.info(`Scraping complete! Total jobs saved: ${jobs.length}`);
      logger.info(`Output folder: ${this.config.output.folder}`);
      logger.info(`========================================\n`);

      return jobs;

    } finally {
      // Always cleanup
      await this.cleanup();
    }
  }
}
