Build a simple, modular Playwright (TypeScript) app that, when permitted by the target site’s terms, logs into LinkedIn, searches jobs by keyword (e.g., “AI Engineer”, “AI Architect”), sorts results by newest/descending (if available), visits each job, and saves full details (title, company, location, description, requirements, etc.) to a Markdown file named “<Company> - <JobTitle>.md”. 
Config (login credentials, search keywords, maxResults toggle, output folder) must be read from a .config file (e.g., .env or config.json). 
Include a CLI flag or config value for maxResults (e.g., 10 => save 10 jobs). 
Use a modern project structure: src/, config/, services/, pages/, utils/, types/, and a clear entry file. 
Keep code readable and modular (page objects, scraping service, markdown writer). 
