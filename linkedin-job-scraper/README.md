# LinkedIn Job Scraper

A modular Playwright (TypeScript) application that logs into LinkedIn, searches for jobs by keyword, and saves job details to Markdown files.

## Features

- **Automated Login**: Securely logs into LinkedIn with your credentials
- **Keyword Search**: Search for multiple job keywords (e.g., "AI Engineer", "Machine Learning")
- **Sort by Newest**: Automatically sorts results by most recent postings
- **Full Job Details**: Extracts title, company, location, description, requirements, benefits, etc.
- **Markdown Export**: Saves each job to a well-formatted Markdown file
- **Configurable**: All settings can be customized via `.env` file or CLI flags
- **Rate Limiting**: Built-in delays to mimic human behavior

## Project Structure

```
├── src/
│   ├── index.ts              # Main entry point with CLI
│   ├── config/
│   │   └── index.ts          # Configuration loader
│   ├── pages/
│   │   ├── BasePage.ts       # Base page object with common methods
│   │   ├── LoginPage.ts      # LinkedIn login page object
│   │   ├── JobSearchPage.ts  # Job search page object
│   │   └── JobDetailsPage.ts # Job details page object
│   ├── services/
│   │   └── JobScraperService.ts  # Main scraping orchestrator
│   ├── types/
│   │   ├── config.types.ts   # Configuration type definitions
│   │   └── job.types.ts      # Job-related type definitions
│   └── utils/
│       ├── logger.ts         # Logging utility
│       ├── strings.ts        # String manipulation utilities
│       └── markdownWriter.ts # Markdown file writer
├── output/                   # Default output folder for MD files
├── .env                      # Environment configuration (create from .env.example)
├── package.json
└── tsconfig.json
```

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd linkedin-job-scraper
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Install Playwright browsers:
   ```bash
   npx playwright install chromium
   ```

4. Create your `.env` file:
   ```bash
   cp .env.example .env
   ```

5. Edit `.env` with your LinkedIn credentials and preferences.

## Configuration

### Environment Variables (`.env`)

```env
# LinkedIn Credentials
LINKEDIN_EMAIL=your-email@example.com
LINKEDIN_PASSWORD=your-password

# Search Configuration
SEARCH_KEYWORDS=AI Engineer,AI Architect,Machine Learning Engineer

# Job scraping limits
MAX_RESULTS=10

# Output Configuration
OUTPUT_FOLDER=./output

# Browser Settings
HEADLESS=false
SLOW_MO=100
```

### CLI Options

| Flag | Description | Example |
|------|-------------|---------|
| `-m, --max <number>` | Maximum jobs to scrape | `--max 20` |
| `-k, --keywords <keywords>` | Comma-separated keywords | `--keywords "AI,ML"` |
| `-H, --headless` | Run browser in headless mode | `--headless` |
| `-v, --verbose` | Enable verbose logging | `--verbose` |

## Usage

### Basic Usage

```bash
npm run scrape
```

### With CLI Options

```bash
# Scrape 20 jobs with custom keywords
npm run scrape -- --max 20 --keywords "AI Engineer,Data Scientist"

# Run in headless mode with verbose logging
npm run scrape -- --headless --verbose

# Override max results
npm run scrape -- --max 5
```

### Development Mode

```bash
npm run dev
```

## Output

Jobs are saved as Markdown files in the output folder with the naming convention:

```
<Company> - <JobTitle>.md
```

### Example Output

```markdown
# Senior AI Engineer

## Overview

| Field | Value |
|-------|-------|
| **Company** | TechCorp |
| **Location** | San Francisco, CA |
| **Employment Type** | Full-time |
| **Seniority Level** | Senior |

## Links

- [Job Posting](https://www.linkedin.com/jobs/view/123456789)
- [Company Page](https://www.linkedin.com/company/techcorp)

## Description

We are looking for an experienced AI Engineer...

## Requirements

- 5+ years of experience in machine learning
- Strong Python skills
- Experience with TensorFlow/PyTorch

## Benefits

- Competitive salary
- Remote work options
- Health insurance
```

## Important Notice

**Please ensure compliance with LinkedIn's Terms of Service before using this tool.**

This scraper is provided for educational purposes only. Web scraping may violate LinkedIn's Terms of Service. Use responsibly and at your own risk.

## Troubleshooting

### Security Challenge / CAPTCHA

If LinkedIn presents a security challenge, the scraper will pause for 30 seconds to allow manual intervention. Complete the challenge in the browser window.

### Login Issues

- Ensure your credentials are correct in `.env`
- LinkedIn may require email/phone verification for new logins
- Try running in non-headless mode to see what's happening

### Rate Limiting

The scraper includes built-in delays to avoid rate limiting. If you encounter issues:
- Reduce `MAX_RESULTS`
- Increase `SLOW_MO` value
- Add longer pauses between runs

## License

MIT License
