/**
 * Centralized Date and Time formatting utility for Sovereign Health Twin.
 * Guarantees consistent Indian Standard Time (IST), timezone 'Asia/Kolkata', UTC+05:30
 * across all modules and prevents calendar day-shifting on date-only values.
 *
 * Target Format: 28 Oct 2026, 11:07 PM IST
 */

const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

/**
 * Safely parses any ISO datetime string or Date object into a UTC-anchored Date.
 * If the string lacks 'Z' or timezone offset (e.g. from SQLite naive datetime strings),
 * explicitly treats it as UTC rather than falling back to browser local time.
 */
export function parseUtcDate(val: string | Date | null | undefined): Date | null {
  if (!val) return null;
  if (val instanceof Date) return isNaN(val.getTime()) ? null : val;

  let str = String(val).trim();
  if (!str) return null;

  // If date-only format (YYYY-MM-DD), handle separately to avoid timezone shifting
  if (/^\d{4}-\d{2}-\d{2}$/.test(str)) {
    const [y, m, d] = str.split('-').map(Number);
    // Construct local midnight date or return direct
    return new Date(Date.UTC(y, m - 1, d, 0, 0, 0));
  }

  // If it's an ISO timestamp without timezone info (e.g. '2026-10-28T17:37:00' or '2026-10-28 17:37:00')
  if (!str.endsWith('Z') && !str.includes('+') && !/-\d{2}:\d{2}$/.test(str)) {
    str = str.replace(' ', 'T') + 'Z';
  }

  const d = new Date(str);
  return isNaN(d.getTime()) ? null : d;
}

export interface FormatISTOptions {
  includeSeconds?: boolean;
  omitLabel?: boolean;
}

/**
 * Formats a timestamp into canonical Indian Standard Time (IST).
 * Output example: "28 Oct 2026, 11:07 PM IST"
 */
export function formatIST(
  val: string | Date | null | undefined,
  options?: FormatISTOptions
): string {
  if (!val) return '--';

  // If string is strictly date-only (YYYY-MM-DD), format as date without shifting
  if (typeof val === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(val.trim())) {
    return formatISTDateOnly(val);
  }

  const d = parseUtcDate(val);
  if (!d) return typeof val === 'string' ? val : '--';

  try {
    const parts = new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      second: options?.includeSeconds ? '2-digit' : undefined,
      hour12: true,
    }).formatToParts(d);

    const m: Record<string, string> = {};
    for (const p of parts) {
      m[p.type] = p.value;
    }

    const day = m.day || '';
    const month = m.month || '';
    const year = m.year || '';
    const hour = m.hour || '';
    const minute = m.minute || '';
    const sec = options?.includeSeconds && m.second ? `:${m.second}` : '';
    const period = (m.dayPeriod || '').toUpperCase();
    const label = options?.omitLabel ? '' : ' IST';

    return `${day} ${month} ${year}, ${hour}:${minute}${sec} ${period}${label}`;
  } catch {
    // Fallback if Intl is unavailable
    return d.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });
  }
}

/**
 * Formats time-only in Indian Standard Time (IST).
 * Examples: "11:07 PM IST" or "11:07 PM" (for charts)
 */
export function formatISTTimeOnly(
  val: string | Date | null | undefined,
  includeLabel = false
): string {
  if (!val) return '--';
  const d = parseUtcDate(val);
  if (!d) return '--';

  try {
    const parts = new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }).formatToParts(d);

    const m: Record<string, string> = {};
    for (const p of parts) {
      m[p.type] = p.value;
    }

    const hour = m.hour || '';
    const minute = m.minute || '';
    const period = (m.dayPeriod || '').toUpperCase();
    const label = includeLabel ? ' IST' : '';

    return `${hour}:${minute} ${period}${label}`;
  } catch {
    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  }
}

/**
 * Formats date-only values (e.g. report dates, menstrual cycle dates, birth dates).
 * Completely preserves the intended calendar day without timezone day-shifting.
 * Output example: "28 Oct 2026"
 */
export function formatISTDateOnly(val: string | Date | null | undefined): string {
  if (!val) return '--';

  if (typeof val === 'string') {
    const trimmed = val.trim();
    // Direct match for YYYY-MM-DD
    const match = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (match) {
      const year = match[1];
      const monthIdx = parseInt(match[2], 10) - 1;
      const day = parseInt(match[3], 10);
      const monthName = MONTH_NAMES[monthIdx] || match[2];
      return `${day} ${monthName} ${year}`;
    }
  }

  const d = parseUtcDate(val);
  if (!d) return typeof val === 'string' ? val : '--';

  try {
    const parts = new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    }).formatToParts(d);

    const m: Record<string, string> = {};
    for (const p of parts) {
      m[p.type] = p.value;
    }
    return `${m.day || ''} ${m.month || ''} ${m.year || ''}`.trim();
  } catch {
    return d.toLocaleDateString();
  }
}

/**
 * Returns plain-English friendly format in IST, e.g.:
 * "Today, 11:07 PM IST" or "Yesterday, 11:07 PM IST" or "28 Oct 2026, 11:07 PM IST"
 */
export function formatFriendlyIST(val: string | Date | null | undefined): string {
  if (!val) return 'Recent';
  const d = parseUtcDate(val);
  if (!d) return '--';

  try {
    // Get date strings in Asia/Kolkata timezone
    const nowParts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(new Date());

    const obsParts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(d);

    const timeStr = formatISTTimeOnly(d, true);

    if (nowParts === obsParts) {
      return `Today at ${timeStr}`;
    }

    // Check yesterday in IST
    const yesterday = new Date(Date.now() - 86400000);
    const yesterdayParts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(yesterday);

    if (obsParts === yesterdayParts) {
      return `Yesterday at ${timeStr}`;
    }

    return formatIST(d);
  } catch {
    return formatIST(d);
  }
}
