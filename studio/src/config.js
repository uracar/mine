// Studio settings. Change these to make the studio cheaper, faster or more thorough.

export const MODEL = "claude-opus-5-5";

// How hard each AI thinks: "low" | "medium" | "high" | "xhigh" | "max".
// Higher = better work, but slower and more expensive.
export const EFFORT = {
  director: "high",
  design: "high",
  engineering: "xhigh", // writing the game code is the hardest job
  art: "high",
  audio: "medium",
  qa: "high",
};

export const LIMITS = {
  maxDepartmentTurns: 40,   // tool-call rounds one department may take per assignment
  maxDirectorTurns: 60,     // rounds the director may take in a whole run
  maxTokens: 64000,         // per response (streaming, so big files are fine)
  maxFileBytes: 400_000,    // largest single file a department may write
  defaultBudgetUsd: 20,     // the run stops handing out work after this much spend
};

// Claude Opus 5.5 list prices, USD per million tokens (used for the spend counter only).
export const PRICE_PER_MTOK = { input: 4, output: 20, cacheWrite: 5, cacheRead: 0.2 };
