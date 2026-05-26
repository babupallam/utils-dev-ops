/**
 * LinkedIn Job Scraper - Main Entry Point
 * 
 * A modular Playwright TypeScript app that logs into LinkedIn,
 * searches jobs by keyword, and saves details to Markdown files.
 * 
 * Usage:
 *   npm run scrape
 *   npm run scrape -- --max 20
 *   npm run scrape -- --keywords "AI Engineer,ML Engineer" --max 15
 */

import { Command } from 'commander';
import { loadConfig, mergeCliArgs } from './config';
import { JobScraperService } from './services';
import { logger, LogLevel } from './utils';

// CLI Setup
const program = new Command();

program
  .name('linkedin-job-scraper')
  .description('Scrape LinkedIn job listings and save to Markdown files')
  .version('1.0.0')
  .option('-m, --max <number>', 'Maximum number of jobs to scrape', parseInt)
  .option('-k, --keywords <keywords>', 'Comma-separated search keywords')
  .option('-H, --headless', 'Run browser in headless mode')
  .option('-v, --verbose', 'Enable verbose logging')
  .parse(process.argv);

const options = program.opts();

/**
 * Main function
 */
async function main(): Promise<void> {
  // Set log level
  if (options.verbose) {
    logger.setLogLevel(LogLevel.DEBUG);
  }

  console.log(`
╔═══════════════════════════════════════════════════════════════╗
║                   LinkedIn Job Scraper                         ║
║        Save job listings to Markdown automatically             ║
╚═══════════════════════════════════════════════════════════════╝
`);

  try {
    // Load configuration from .env
    logger.info('Loading configuration...');
    let config = loadConfig();

    // Parse CLI keywords if provided
    const cliKeywords = options.keywords
      ? options.keywords.split(',').map((k: string) => k.trim())
      : undefined;

    // Merge CLI arguments with config
    config = mergeCliArgs(config, {
      maxResults: options.max,
      keywords: cliKeywords,
      headless: options.headless,
    });

    // Log configuration summary
    logger.info('Configuration:');
    logger.info(`  - Keywords: ${config.search.keywords.join(', ')}`);
    logger.info(`  - Max Results: ${config.search.maxResults}`);
    logger.info(`  - Output Folder: ${config.output.folder}`);
    logger.info(`  - Headless: ${config.browser.headless}`);

    // Important notice
    console.log(`
╔═══════════════════════════════════════════════════════════════╗
║  IMPORTANT: Please ensure you comply with LinkedIn's           ║
║  Terms of Service before running this scraper.                 ║
║  This tool is for educational purposes.                        ║
╚═══════════════════════════════════════════════════════════════╝
`);

    // Create and run scraper
    const scraper = new JobScraperService(config);
    const jobs = await scraper.run();

    // Summary
    console.log(`
╔═══════════════════════════════════════════════════════════════╗
║                      Scraping Complete                         ║
╠═══════════════════════════════════════════════════════════════╣
║  Total Jobs Saved: ${String(jobs.length).padEnd(43)}║
║  Output Folder: ${config.output.folder.padEnd(46)}║
╚═══════════════════════════════════════════════════════════════╝
`);

    // List saved jobs
    if (jobs.length > 0) {
      console.log('\nSaved Jobs:');
      jobs.forEach((job, index) => {
        console.log(`  ${index + 1}. ${job.company} - ${job.title}`);
      });
    }

  } catch (error) {
    logger.error(`Fatal error: ${error}`);
    process.exit(1);
  }
}

// Run main function
main().catch((error) => {
  console.error('Unhandled error:', error);
  process.exit(1);
});
