// "YYYY-MM-DD" in local time, the format <input type="date"> reads and writes.
export function toDateInputValue(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function daysAgoInputValue(days) {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return toDateInputValue(date);
}

// Local start/end of the picked days, sent as UTC ISO so the backend filters the seller's own calendar days.
export function dayBoundsIso(startValue, endValue) {
  const [sy, sm, sd] = startValue.split("-").map(Number);
  const [ey, em, ed] = endValue.split("-").map(Number);
  return {
    start: new Date(sy, sm - 1, sd, 0, 0, 0, 0).toISOString(),
    end: new Date(ey, em - 1, ed, 23, 59, 59, 999).toISOString(),
  };
}

// A "YYYY-MM-DD" date from the API, parsed as local midnight (not UTC) so labels don't shift a day.
export function parseIsoDate(isoDate) {
  return new Date(`${isoDate}T00:00:00`);
}

export function formatDate(isoDate, options) {
  return new Intl.DateTimeFormat(undefined, options).format(parseIsoDate(isoDate));
}
