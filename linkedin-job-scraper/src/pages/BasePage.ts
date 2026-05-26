/**
 * Base page object with common functionality
 */

import { Page } from 'playwright';
import { logger } from '../utils';

export abstract class BasePage {
  protected page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  /**
   * Wait for navigation to complete
   */
  protected async waitForNavigation(timeout = 30000): Promise<void> {
    await this.page.waitForLoadState('domcontentloaded', { timeout });
  }


  /**
   * Wait for an element to be visible
   */
  protected async waitForElement(selector: string, timeout = 10000): Promise<void> {
    await this.page.waitForSelector(selector, { state: 'visible', timeout });
  }

  /**
   * Safe click - waits for element and clicks
   */
  protected async safeClick(selector: string, timeout = 10000): Promise<void> {
    await this.waitForElement(selector, timeout);
    await this.page.click(selector);
  }

  /**
   * Safe fill - waits for element and fills
   */
  protected async safeFill(selector: string, value: string, timeout = 10000): Promise<void> {
    await this.waitForElement(selector, timeout);
    await this.page.fill(selector, value);
  }

  /**
   * Get text content safely
   */
  protected async getTextContent(selector: string): Promise<string | null> {
    try {
      const element = await this.page.$(selector);
      if (element) {
        return await element.textContent();
      }
    } catch (e) {
      logger.debug(`Could not get text content for ${selector}`);
    }
    return null;
  }

  /**
   * Check if element exists
   */
  protected async elementExists(selector: string): Promise<boolean> {
    try {
      const element = await this.page.$(selector);
      return element !== null;
    } catch {
      return false;
    }
  }

  /**
   * Take a screenshot for debugging
   */
  protected async screenshot(name: string): Promise<void> {
    await this.page.screenshot({ path: `debug-${name}-${Date.now()}.png` });
  }

  /**
   * Random delay to mimic human behavior
   */
  protected async humanDelay(min = 500, max = 2000): Promise<void> {
    const delay = Math.floor(Math.random() * (max - min + 1)) + min;
    await this.page.waitForTimeout(delay);
  }
}
