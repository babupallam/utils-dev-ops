/**
 * LinkedIn Job Search Page Object
 */

import { Page } from 'playwright';
import { BasePage } from './BasePage';
import { JobListing } from '../types';
import { logger, generateId, cleanText } from '../utils';

export class JobSearchPage extends BasePage {
  // Selectors
  private readonly selectors = {
    searchKeywordsInput: 'input[aria-label="Search by title, skill, or company"]',
    searchButton: 'button[type="submit"]',
    jobCards: '.jobs-search-results__list-item, .job-card-container, .jobs-search-results-list li',
    jobTitle: '.job-card-list__title, .job-card-container__link, a[data-control-name="job_card_title"]',
    jobCompany: '.job-card-container__primary-description, .job-card-container__company-name, .artdeco-entity-lockup__subtitle',
    jobLocation: '.job-card-container__metadata-item, .artdeco-entity-lockup__caption',
    sortDropdown: '.jobs-search-dropdown, button[aria-label*="Sort"]',
    sortByRecent: 'button[aria-label*="Date posted"], li[data-value="DD"]',
    noResultsMessage: '.jobs-search-no-results-banner',
    resultsContainer: '.jobs-search-results-list',
    paginationNext: 'button[aria-label="Next"]',
    totalResults: '.jobs-search-results-list__subtitle, .jobs-search-results-list__title-heading',
  };

  private readonly urls = {
    jobsSearch: 'https://www.linkedin.com/jobs/search/',
  };

  constructor(page: Page) {
    super(page);
  }

  /**
   * Search for jobs with a keyword
   */
  async searchJobs(keyword: string): Promise<void> {
  logger.info(`Searching for jobs: "${keyword}"`);

  const searchUrl = `${this.urls.jobsSearch}?keywords=${encodeURIComponent(keyword)}&sortBy=DD`;
  await this.page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await this.humanDelay(1000, 2000);

  await Promise.race([
    this.page.waitForSelector(this.selectors.jobCards, { timeout: 15000 }),
    this.page.waitForSelector(this.selectors.noResultsMessage, { timeout: 15000 }),
  ]).catch(() => {
    logger.warn('Jobs results did not fully stabilize, continuing with available page state');
  });
}

  /**
   * Try to sort results by most recent
   */
  async sortByMostRecent(): Promise<void> {
    try {
      logger.info('Attempting to sort by most recent...');
      
      // LinkedIn often has sortBy=DD in URL which sorts by date
      const currentUrl = this.page.url();
      if (!currentUrl.includes('sortBy=DD')) {
        const newUrl = currentUrl.includes('?') 
          ? `${currentUrl}&sortBy=DD`
          : `${currentUrl}?sortBy=DD`;
        await this.page.goto(newUrl);
        await this.waitForNavigation();
        await this.humanDelay(500, 1000);
      }
      
      logger.info('Sorted by most recent');
    } catch (error) {
      logger.warn(`Could not sort by recent: ${error}`);
    }
  }

  /**
   * Get all visible job listings on the current page
   */
  async getJobListings(maxResults: number): Promise<JobListing[]> {
    const jobs: JobListing[] = [];
    
    try {
      // Wait for job cards
      await this.page.waitForSelector(this.selectors.jobCards, { timeout: 10000 });
      
      // Scroll to load more jobs
      await this.scrollToLoadJobs(maxResults);
      
      // Get all job card elements
      const jobCards = await this.page.$$(this.selectors.jobCards);
      
      logger.info(`Found ${jobCards.length} job cards`);

      for (let i = 0; i < Math.min(jobCards.length, maxResults); i++) {
        try {
          const card = jobCards[i];
          
          // Click on the card to ensure it's selected
          await card.click();
          await this.humanDelay(700, 1200);

          await this.page.waitForSelector(
            '.jobs-search__job-details, .jobs-details, .scaffold-layout__detail',
            { timeout: 10000 }
          ).catch(() => {
            logger.warn('Details panel did not fully load, continuing with available content');
          });


          // Extract job info from the card
          const titleElement = await card.$('a[href*="/jobs/view/"]');
          const companyElement = await card.$('.job-card-container__primary-description, .artdeco-entity-lockup__subtitle span');
          const locationElement = await card.$('.job-card-container__metadata-item, .artdeco-entity-lockup__caption span');

          const title = titleElement ? cleanText(await titleElement.textContent()) : 'Unknown Title';
          const company = companyElement ? cleanText(await companyElement.textContent()) : 'Unknown Company';
          const location = locationElement ? cleanText(await locationElement.textContent()) : 'Unknown Location';
          
          // Get job URL
          let url = '';
          if (titleElement) {
            url = await titleElement.getAttribute('href') || '';
            if (url && !url.startsWith('http')) {
              url = `https://www.linkedin.com${url}`;
            }
          }

          // Generate ID from URL
          const id = generateId(url || `${company}-${title}-${i}`);

          jobs.push({
            id,
            title,
            company,
            location,
            url,
          });

          logger.debug(`Found job: ${title} at ${company}`);

        } catch (error) {
          logger.warn(`Error extracting job card ${i}: ${error}`);
        }
      }

    } catch (error) {
      logger.error(`Error getting job listings: ${error}`);
    }

    return jobs;
  }

  /**
   * Scroll through the job list to load more items
   */
  private async scrollToLoadJobs(targetCount: number): Promise<void> {
    let previousCount = 0;
    let scrollAttempts = 0;
    const maxScrollAttempts = 10;

    while (scrollAttempts < maxScrollAttempts) {
      const jobCards = await this.page.$$(this.selectors.jobCards);
      const currentCount = jobCards.length;

      if (currentCount >= targetCount || currentCount === previousCount) {
        break;
      }

      // Scroll the job list container
      await this.page.evaluate(() => {
        const container = document.querySelector('.jobs-search-results-list');
        if (container) {
          container.scrollTop += 500;
        }
        window.scrollBy(0, 300);
      });

      await this.humanDelay(500, 1000);
      previousCount = currentCount;
      scrollAttempts++;
    }
  }

  /**
   * Check if there are no search results
   */
  async hasNoResults(): Promise<boolean> {
    return await this.elementExists(this.selectors.noResultsMessage);
  }
}
