/**
 * LinkedIn Login Page Object
 */

import { Page } from 'playwright';
import { BasePage } from './BasePage';
import { LinkedInCredentials } from '../types';
import { logger } from '../utils';

export class LoginPage extends BasePage {
  // Selectors
  private readonly selectors = {
    emailInput: '#username',
    passwordInput: '#password',
    signInButton: 'button[type="submit"]',
    feedContainer: '.feed-shared-update-v2, .scaffold-layout',
    errorMessage: '.form__label--error, #error-for-username, #error-for-password',
    securityCheck: '.challenge-dialog, #captcha-internal',
  };

  private readonly urls = {
    login: 'https://www.linkedin.com/login',
    feed: 'https://www.linkedin.com/feed/',
  };

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to the LinkedIn login page
   */
  async navigateToLogin(): Promise<void> {
    logger.info('Navigating to LinkedIn login page...');
    await this.page.goto(this.urls.login);
    await this.waitForNavigation();
  }

  /**
   * Perform login with credentials
   */
  async login(credentials: LinkedInCredentials): Promise<boolean> {
    try {
      await this.navigateToLogin();

      // Check if already logged in
      if (await this.isLoggedIn()) {
        logger.info('Already logged in to LinkedIn');
        return true;
      }

      logger.info('Entering login credentials...');
      
      // Fill in credentials
      await this.safeFill(this.selectors.emailInput, credentials.email);
      await this.humanDelay(300, 800);
      await this.safeFill(this.selectors.passwordInput, credentials.password);
      await this.humanDelay(300, 800);

      // Click sign in
      await this.safeClick(this.selectors.signInButton);
      
      // Wait for either success or error
      await this.page.waitForTimeout(3000);

      // Check for security challenge
      if (await this.hasSecurityChallenge()) {
        logger.warn('Security challenge detected. Manual intervention may be required.');
        logger.warn('Please complete the challenge in the browser window...');
        // Wait longer for manual intervention
        await this.page.waitForTimeout(30000);
      }

      // Check for login errors
      if (await this.hasLoginError()) {
        const errorText = await this.getTextContent(this.selectors.errorMessage);
        logger.error(`Login failed: ${errorText}`);
        return false;
      }

      // Verify successful login
      if (await this.isLoggedIn()) {
        logger.info('Successfully logged in to LinkedIn');
        return true;
      }

      logger.warn('Login status unclear, proceeding...');
      return true;

    } catch (error) {
      logger.error(`Login error: ${error}`);
      return false;
    }
  }

  /**
   * Check if user is already logged in
   */
  async isLoggedIn(): Promise<boolean> {
    try {
      // Check URL
      const currentUrl = this.page.url();
      if (currentUrl.includes('/feed') || currentUrl.includes('/jobs')) {
        return true;
      }

      // Check for feed elements
      const hasFeed = await this.elementExists(this.selectors.feedContainer);
      return hasFeed;
    } catch {
      return false;
    }
  }

  /**
   * Check for login errors
   */
  private async hasLoginError(): Promise<boolean> {
    return await this.elementExists(this.selectors.errorMessage);
  }

  /**
   * Check for security challenge (CAPTCHA, verification, etc.)
   */
  private async hasSecurityChallenge(): Promise<boolean> {
    const url = this.page.url();
    if (url.includes('checkpoint') || url.includes('challenge')) {
      return true;
    }
    return await this.elementExists(this.selectors.securityCheck);
  }
}
