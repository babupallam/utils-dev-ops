/**
 * String utilities for file naming and text processing
 */

/**
 * Sanitize a string to be used as a filename
 * Removes or replaces characters that are invalid in filenames
 */
export function sanitizeFilename(input: string): string {
  return input
    .replace(/[<>:"/\\|?*]/g, '-') // Replace invalid filename chars
    .replace(/\s+/g, ' ')          // Normalize whitespace
    .replace(/-+/g, '-')           // Remove consecutive dashes
    .replace(/^-|-$/g, '')         // Remove leading/trailing dashes
    .trim()
    .substring(0, 200);            // Limit length
}

/**
 * Generate a markdown filename from company and job title
 */
export function generateJobFilename(company: string, jobTitle: string): string {
  const sanitizedCompany = sanitizeFilename(company);
  const sanitizedTitle = sanitizeFilename(jobTitle);
  return `${sanitizedCompany} - ${sanitizedTitle}.md`;
}

/**
 * Extract text content, handling null/undefined
 */
export function cleanText(text: string | null | undefined): string {
  if (!text) return '';
  return text
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Generate a unique ID from a URL or string
 */
export function generateId(input: string): string {
  // Extract job ID from LinkedIn URL if possible
  const jobIdMatch = input.match(/\/jobs\/view\/(\d+)/);
  if (jobIdMatch) {
    return jobIdMatch[1];
  }
  
  // Otherwise, create a simple hash
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    const char = input.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash).toString(36);
}
