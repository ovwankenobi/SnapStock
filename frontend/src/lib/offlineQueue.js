import { quickSellProduct } from "../api/products";

const STORAGE_KEY = "snapstock.offlineQueue.quickSell";

export function isNetworkError(err) {
  return Boolean(err?.request) && !err?.response;
}

function readQueue() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function writeQueue(queue) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(queue));
}

export function getQueuedQuickSells() {
  return readQueue();
}

export function queueLength() {
  return readQueue().length;
}

export function enqueueQuickSell({ id, payload }) {
  const queue = readQueue();
  queue.push({ id, payload, queuedAt: new Date().toISOString() });
  writeQueue(queue);
  return queue.length;
}

// Replays queued quick-sells against the server. Stops at the first entry
// that still fails with a network error (we're probably still offline) but
// drops entries the server actively rejects (e.g. stock ran out in the
// meantime) since replaying those again would never succeed.
export async function flushQuickSellQueue() {
  const queue = readQueue();
  if (queue.length === 0) return { flushed: 0, remaining: 0 };

  let flushed = 0;
  const remaining = [];

  for (let i = 0; i < queue.length; i++) {
    const entry = queue[i];
    try {
      await quickSellProduct(entry.id, entry.payload);
      flushed++;
    } catch (err) {
      if (isNetworkError(err)) {
        remaining.push(entry, ...queue.slice(i + 1));
        break;
      }
      // Server rejected it outright — drop it, nothing more we can do.
    }
  }

  writeQueue(remaining);
  return { flushed, remaining: remaining.length };
}
