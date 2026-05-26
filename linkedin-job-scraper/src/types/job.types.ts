/**
 * Job-related types for LinkedIn job scraping
 */

export interface JobListing {
  id: string;
  title: string;
  company: string;
  location: string;
  url: string;
  postedDate?: string;
}

export interface JobDetails extends JobListing {
  description: string;
  employmentType?: string;
  seniorityLevel?: string;
  industry?: string;
  jobFunction?: string;
  requirements?: string[];
  benefits?: string[];
  salary?: string;
  applicants?: string;
  companyUrl?: string;
  companySize?: string;
  scrapedAt: Date;
}
