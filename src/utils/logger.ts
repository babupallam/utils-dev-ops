/**
 * Logger utility for consistent console output
 */

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

let currentLogLevel = LogLevel.INFO;

export function setLogLevel(level: LogLevel): void {
  currentLogLevel = level;
}

function formatTimestamp(): string {
  return new Date().toISOString();
}

export function debug(message: string, ...args: unknown[]): void {
  if (currentLogLevel <= LogLevel.DEBUG) {
    console.log(`[${formatTimestamp()}] [DEBUG] ${message}`, ...args);
  }
}

export function info(message: string, ...args: unknown[]): void {
  if (currentLogLevel <= LogLevel.INFO) {
    console.log(`[${formatTimestamp()}] [INFO] ${message}`, ...args);
  }
}

export function warn(message: string, ...args: unknown[]): void {
  if (currentLogLevel <= LogLevel.WARN) {
    console.warn(`[${formatTimestamp()}] [WARN] ${message}`, ...args);
  }
}

export function error(message: string, ...args: unknown[]): void {
  if (currentLogLevel <= LogLevel.ERROR) {
    console.error(`[${formatTimestamp()}] [ERROR] ${message}`, ...args);
  }
}

export const logger = {
  debug,
  info,
  warn,
  error,
  setLogLevel,
};
