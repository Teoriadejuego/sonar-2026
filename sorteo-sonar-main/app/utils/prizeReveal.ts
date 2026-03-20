export type PrizeIconCategory =
  | "circle"
  | "square"
  | "triangle"
  | "diamond"
  | "hexagon"
  | "star";

export type PrizeRevealTile = {
  index: number;
  category: PrizeIconCategory;
};

type PrizeRevealState = {
  selectedIndex: number;
  winnerIndex: number;
  completedAt: string;
};

const PRIZE_REVEAL_STORAGE_KEY = "sonar_prize_reveal_v1";
const PRIZE_REVEAL_TOTAL_TILES = 100;
const DEMO_SESSION_PREFIX = "demo-session-";
const PRIZE_REVEAL_COUNTS: Array<{
  category: PrizeIconCategory;
  count: number;
}> = [
  { category: "circle", count: 17 },
  { category: "square", count: 17 },
  { category: "triangle", count: 17 },
  { category: "diamond", count: 17 },
  { category: "hexagon", count: 16 },
  { category: "star", count: 16 },
];

function readRevealMap(): Record<string, PrizeRevealState> {
  if (typeof window === "undefined") {
    return {};
  }
  const raw = window.localStorage.getItem(PRIZE_REVEAL_STORAGE_KEY);
  if (!raw) {
    return {};
  }
  try {
    return JSON.parse(raw) as Record<string, PrizeRevealState>;
  } catch {
    return {};
  }
}

function writeRevealMap(value: Record<string, PrizeRevealState>) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(PRIZE_REVEAL_STORAGE_KEY, JSON.stringify(value));
}

function isDemoPrizeRevealSession(sessionId: string) {
  return sessionId.startsWith(DEMO_SESSION_PREFIX);
}

function hashString(value: string) {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function mulberry32(seed: number) {
  return function next() {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function shuffleDeterministically<T>(items: T[], seedKey: string) {
  const rng = mulberry32(hashString(seedKey));
  const next = [...items];
  for (let index = next.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(rng() * (index + 1));
    [next[index], next[swapIndex]] = [next[swapIndex], next[index]];
  }
  return next;
}

export function buildPrizeRevealBoard(sessionId: string): PrizeRevealTile[] {
  const items: PrizeIconCategory[] = [];
  for (const entry of PRIZE_REVEAL_COUNTS) {
    for (let count = 0; count < entry.count; count += 1) {
      items.push(entry.category);
    }
  }
  const shuffled = shuffleDeterministically(items, `board:${sessionId}`);
  return shuffled.slice(0, PRIZE_REVEAL_TOTAL_TILES).map((category, index) => ({
    index,
    category,
  }));
}

export function getStoredPrizeRevealState(sessionId: string) {
  if (isDemoPrizeRevealSession(sessionId)) {
    return null;
  }
  return readRevealMap()[sessionId] ?? null;
}

export function markPrizeRevealCompleted(
  sessionId: string,
  state: PrizeRevealState,
) {
  if (isDemoPrizeRevealSession(sessionId)) {
    return;
  }
  const next = readRevealMap();
  next[sessionId] = state;
  writeRevealMap(next);
}

export function hasCompletedPrizeReveal(sessionId: string) {
  return Boolean(getStoredPrizeRevealState(sessionId));
}

export function getPrizeRevealWinnerIndex(
  sessionId: string,
  selectedIndex: number,
  eligibleForPayment: boolean,
) {
  if (eligibleForPayment) {
    return selectedIndex;
  }
  let nextIndex = hashString(`winner:${sessionId}`) % PRIZE_REVEAL_TOTAL_TILES;
  if (nextIndex === selectedIndex) {
    nextIndex = (nextIndex + 13) % PRIZE_REVEAL_TOTAL_TILES;
  }
  return nextIndex;
}
