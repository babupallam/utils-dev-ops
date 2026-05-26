/**
 * LinkedIn Job Details Page Object
 */

import { Page } from 'playwright';
import { BasePage } from './BasePage';
import { JobListing, JobDetails } from '../types';
import { logger, cleanText } from '../utils';

export class JobDetailsPage extends BasePage {
  // Selectors
 private readonly selectors = {
  jobTitle: '.jobs-search__job-details .jobs-unified-top-card__job-title, .job-details-jobs-unified-top-card__job-title, .jobs-unified-top-card__job-title, h1.t-24',
  companyName: '.jobs-search__job-details .jobs-unified-top-card__company-name, .job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name, a[data-tracking-control-name="public_jobs_topcard-org-name"]',
  companyLink: '.jobs-search__job-details .jobs-unified-top-card__company-name a, .job-details-jobs-unified-top-card__company-name a, .jobs-unified-top-card__company-name a',
  location: '.jobs-search__job-details .jobs-unified-top-card__primary-description, .job-details-jobs-unified-top-card__primary-description-container, .jobs-unified-top-card__primary-description, .jobs-unified-top-card__bullet',
  description: '.jobs-search__job-details .jobs-box__html-content, .jobs-search__job-details .jobs-description-content__text, .jobs-description__content, .jobs-description-content__text, #job-details',
  descriptionContainer: '.jobs-search__job-details .jobs-description, .jobs-search__job-details .jobs-box__html-content, .jobs-description, .jobs-box__html-content',
  seeMoreButton: '.jobs-search__job-details button[aria-label*="more"], .jobs-description__footer-button, button[aria-label*="Click to see more description"], button[aria-label*="more"]',
  jobInsights: '.jobs-search__job-details .job-details-jobs-unified-top-card__job-insight, .job-details-jobs-unified-top-card__job-insight, .jobs-unified-top-card__job-insight',
  applicants: '.jobs-search__job-details .jobs-unified-top-card__applicant-count, .jobs-unified-top-card__applicant-count, .num-applicants__caption',
  postedDate: '.jobs-search__job-details .jobs-unified-top-card__posted-date, .jobs-unified-top-card__posted-date, time',
  criteriaList: '.jobs-search__job-details .job-criteria__list, .job-criteria__list, .description__job-criteria-list',
  criteriaItem: '.jobs-search__job-details .job-criteria__item, .job-criteria__item, .description__job-criteria-item',
  criteriaHeader: '.job-criteria__subheader, .description__job-criteria-subheader',
  criteriaText: '.job-criteria__text, .description__job-criteria-text',
  salary: '.jobs-search__job-details .salary-main-rail__salary-range, .salary-main-rail__salary-range, .compensation__salary',
};


  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to a specific job and extract full details
   */
  async getJobDetails(listing: JobListing): Promise<JobDetails> {
  logger.info(`Getting details for: ${listing.title} at ${listing.company}`);

  try {
    // Stay on the search results page and scrape the currently selected job panel.
    await this.humanDelay(800, 1500);

    // Expand description if truncated
    await this.expandDescription();

    // Extract all details from the selected panel
    const details = await this.extractJobDetails(listing);

    return details;

  } catch (error) {
    logger.error(`Error getting job details for ${listing.title}: ${error}`);

    return {
      ...listing,
      description: 'Could not extract job description',
      scrapedAt: new Date(),
    };
  }
}


  /**
   * Expand the job description if there's a "See more" button
   */
  private async expandDescription(): Promise<void> {
    try {
      const seeMoreButton = await this.page.$(this.selectors.seeMoreButton);
      if (seeMoreButton) {
        await seeMoreButton.click();
        await this.humanDelay(300, 600);
      }
    } catch {
      // Button might not exist or already expanded
    }
  }

  /**
   * Extract all job details from the page
   */
  private async extractJobDetails(listing: JobListing): Promise<JobDetails> {
    // Get job title (use listing title as fallback)
    const title = listing.title;

    // Get company info
    const company = await this.extractCompany() || listing.company;
    const companyUrl = await this.extractCompanyUrl();

    // Get location
    const location = await this.extractLocation() || listing.location;

    // Get full description
    const description = await this.extractDescription();

    // Get job criteria
    const criteria = await this.extractJobCriteria();

    // Get other details
    const postedDate = await this.extractPostedDate();
    const applicants = await this.extractApplicants();
    const salary = await this.extractSalary();

    // Extract requirements and benefits from description
    const { requirements, benefits } = this.parseDescriptionSections(description);

    return {
      id: listing.id,
      title,
      company,
      companyUrl,
      location,
      url: listing.url || this.page.url(),
      description,
      employmentType: criteria.employmentType,
      seniorityLevel: criteria.seniorityLevel,
      industry: criteria.industry,
      jobFunction: criteria.jobFunction,
      requirements,
      benefits,
      postedDate,
      applicants,
      salary,
      scrapedAt: new Date(),
    };
  }

  private async extractTitle(): Promise<string> {
    const titleText = await this.getTextContent(this.selectors.jobTitle);
    return cleanText(titleText);
  }

  private async extractCompany(): Promise<string> {
    const companyText = await this.getTextContent(this.selectors.companyName);
    return cleanText(companyText);
  }

  private async extractCompanyUrl(): Promise<string | undefined> {
    try {
      const link = await this.page.$(this.selectors.companyLink);
      if (link) {
        const href = await link.getAttribute('href');
        if (href) {
          return href.startsWith('http') ? href : `https://www.linkedin.com${href}`;
        }
      }
    } catch {
      // Company link might not exist
    }
    return undefined;
  }

  private async extractLocation(): Promise<string> {
    const locationText = await this.getTextContent(this.selectors.location);
    return cleanText(locationText);
  }

 private async extractDescription(): Promise<string> {
  try {
    const selectors = [
      this.selectors.description,
      this.selectors.descriptionContainer,
      '#job-details',
      '.jobs-description',
    ];

    for (const selector of selectors) {
      const element = await this.page.$(selector);
      if (element) {
        const text = await element.innerText();
        if (text && text.trim().length > 50) {
          return text.trim();
        }
      }
    }
  } catch (error) {
    logger.debug(`Error extracting description: ${error}`);
  }

  return '';
}


  private async extractJobCriteria(): Promise<{
    employmentType?: string;
    seniorityLevel?: string;
    industry?: string;
    jobFunction?: string;
  }> {
    const criteria: {
      employmentType?: string;
      seniorityLevel?: string;
      industry?: string;
      jobFunction?: string;
    } = {};

    try {
      const criteriaItems = await this.page.$$(this.selectors.criteriaItem);

      for (const item of criteriaItems) {
        const headerElement = await item.$(this.selectors.criteriaHeader);
        const textElement = await item.$(this.selectors.criteriaText);

        if (headerElement && textElement) {
          const header = cleanText(await headerElement.textContent()).toLowerCase();
          const text = cleanText(await textElement.textContent());

          if (header.includes('seniority')) {
            criteria.seniorityLevel = text;
          } else if (header.includes('employment') || header.includes('type')) {
            criteria.employmentType = text;
          } else if (header.includes('industry') || header.includes('industries')) {
            criteria.industry = text;
          } else if (header.includes('function')) {
            criteria.jobFunction = text;
          }
        }
      }

      // Also try to extract from job insights
      const insights = await this.page.$$(this.selectors.jobInsights);
      for (const insight of insights) {
        const text = cleanText(await insight.textContent());
        if (text.includes('Full-time') || text.includes('Part-time') || text.includes('Contract')) {
          criteria.employmentType = criteria.employmentType || text;
        }
      }

    } catch (error) {
      logger.debug(`Error extracting job criteria: ${error}`);
    }

    return criteria;
  }

  private async extractPostedDate(): Promise<string | undefined> {
    try {
      const dateText = await this.getTextContent(this.selectors.postedDate);
      return cleanText(dateText) || undefined;
    } catch {
      return undefined;
    }
  }

  private async extractApplicants(): Promise<string | undefined> {
    try {
      const applicantsText = await this.getTextContent(this.selectors.applicants);
      return cleanText(applicantsText) || undefined;
    } catch {
      return undefined;
    }
  }

  private async extractSalary(): Promise<string | undefined> {
    try {
      const salaryText = await this.getTextContent(this.selectors.salary);
      return cleanText(salaryText) || undefined;
    } catch {
      return undefined;
    }
  }

  /**
   * Parse description to extract requirements and benefits sections
   */
  private parseDescriptionSections(description: string): {
    requirements: string[];
    benefits: string[];
  } {
    const requirements: string[] = [];
    const benefits: string[] = [];

    // Simple parsing - look for common section headers
    const lines = description.split('\n');
    let currentSection: 'none' | 'requirements' | 'benefits' = 'none';

    for (const line of lines) {
      const lowerLine = line.toLowerCase().trim();

      // Detect section headers
      if (lowerLine.includes('requirement') || lowerLine.includes('qualification') || 
          lowerLine.includes('what you need') || lowerLine.includes('must have')) {
        currentSection = 'requirements';
        continue;
      }

      if (lowerLine.includes('benefit') || lowerLine.includes('perk') || 
          lowerLine.includes('what we offer') || lowerLine.includes('why join')) {
        currentSection = 'benefits';
        continue;
      }

      // Add bullet points to current section
      const cleanLine = line.trim();
      if (cleanLine.startsWith('•') || cleanLine.startsWith('-') || cleanLine.startsWith('*')) {
        const item = cleanLine.replace(/^[•\-*]\s*/, '').trim();
        if (item.length > 5) {
          if (currentSection === 'requirements') {
            requirements.push(item);
          } else if (currentSection === 'benefits') {
            benefits.push(item);
          }
        }
      }
    }

    return { requirements, benefits };
  }
}
