export function utcWallClockToLocalPreview(hourUtc, minuteUtc) {
  const safeHour = Number.isFinite(hourUtc) ? hourUtc : 0;
  const safeMinute = Number.isFinite(minuteUtc) ? minuteUtc : 0;
  const fixedUtc = new Date(Date.UTC(2030, 0, 1, safeHour, safeMinute, 0));
  return fixedUtc.toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

export function formatUtcIsoAsLocal(isoValue) {
  if (!isoValue) return "—";
  const date = new Date(isoValue);
  if (Number.isNaN(date.getTime())) return isoValue;
  return date.toLocaleString([], {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    timeZoneName: "short",
  });
}

export function formatSchedulerStamp(isoValue) {
  if (!isoValue) return "—";
  const value = new Date(isoValue);
  if (Number.isNaN(value.getTime())) return isoValue;
  return value.toLocaleString([], {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    month: "2-digit",
    day: "2-digit",
    timeZoneName: "short",
  });
}

export function formatCurrencyFromCents(cents) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format((Number(cents) || 0) / 100);
}
