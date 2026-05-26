/**
 * Markdown writer utility for saving job details
 */

import * as fs from 'fs';
import * as path from 'path';
import { JobDetails } from '../types';
import { generateJobFilename } from './strings';
import { logger } from './logger';

/**
 * Ensure the output directory exists
 */
export function ensureOutputDir(outputFolder: string): void {
  if (!fs.existsSync(outputFolder)) {
    fs.mkdirSync(outputFolder, { recursive: true });
    logger.info(`Created output directory: ${outputFolder}`);
  }
}

/**
 * Convert job details to Markdown format
 */
export function jobToMarkdown(job: JobDetails): string {
  const sections: string[] = [];

  // Header
  sections.push(`# ${job.title}`);
  sections.push('');

  // Basic Info Table
  sections.push('## Overview');
  sections.push('');
  sections.push('| Field | Value |');
  sections.push('|-------|-------|');
  sections.push(`| **Company** | ${job.company} |`);
  sections.push(`| **Location** | ${job.location} |`);
  
  if (job.employmentType) {
    sections.push(`| **Employment Type** | ${job.employmentType} |`);
  }
  if (job.seniorityLevel) {
    sections.push(`| **Seniority Level** | ${job.seniorityLevel} |`);
  }
  if (job.salary) {
    sections.push(`| **Salary** | ${job.salary} |`);
  }
  if (job.postedDate) {
    sections.push(`| **Posted** | ${job.postedDate} |`);
  }
  if (job.applicants) {
    sections.push(`| **Applicants** | ${job.applicants} |`);
  }
  if (job.industry) {
    sections.push(`| **Industry** | ${job.industry} |`);
  }
  if (job.jobFunction) {
    sections.push(`| **Job Function** | ${job.jobFunction} |`);
  }
  if (job.companySize) {
    sections.push(`| **Company Size** | ${job.companySize} |`);
  }
  
  sections.push('');

  // Links
  sections.push('## Links');
  sections.push('');
  sections.push(`- [Job Posting](${job.url})`);
  if (job.companyUrl) {
    sections.push(`- [Company Page](${job.companyUrl})`);
  }
  sections.push('');

  // Description
  sections.push('## Description');
  sections.push('');
  sections.push(job.description || '*No description available*');
  sections.push('');

  // Requirements
  if (job.requirements && job.requirements.length > 0) {
    sections.push('## Requirements');
    sections.push('');
    job.requirements.forEach((req) => {
      sections.push(`- ${req}`);
    });
    sections.push('');
  }

  // Benefits
  if (job.benefits && job.benefits.length > 0) {
    sections.push('## Benefits');
    sections.push('');
    job.benefits.forEach((benefit) => {
      sections.push(`- ${benefit}`);
    });
    sections.push('');
  }

  // Metadata
  sections.push('---');
  sections.push('');
  sections.push(`*Scraped at: ${job.scrapedAt.toISOString()}*`);
  sections.push(`*Job ID: ${job.id}*`);

  return sections.join('\n');
}

/**
 * Save job details to a Markdown file
 */
export function saveJobToMarkdown(job: JobDetails, outputFolder: string): string {
  ensureOutputDir(outputFolder);

  const filename = generateJobFilename(job.company, job.title);
  const filepath = path.join(outputFolder, filename);
  const content = jobToMarkdown(job);

  fs.writeFileSync(filepath, content, 'utf-8');
  logger.info(`Saved: ${filename}`);

  return filepath;
}

/**
 * Save multiple jobs to Markdown files
 */
export function saveJobsToMarkdown(jobs: JobDetails[], outputFolder: string): string[] {
  return jobs.map((job) => saveJobToMarkdown(job, outputFolder));
}
