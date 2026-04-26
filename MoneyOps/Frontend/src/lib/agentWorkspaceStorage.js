const CHAT_PREFIX = "moneyops:agent-chat";
const VOICE_PREFIX = "moneyops:voice-history";
const PREFS_PREFIX = "moneyops:agent-prefs";

function getStorageKey(prefix, scope) {
  return `${prefix}:${scope || "global"}`;
}

function readJson(key, fallback) {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key, value) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // ignore quota/storage issues for now
  }
}

export function listVoiceSessions(scope) {
  const sessions = readJson(getStorageKey(VOICE_PREFIX, scope), []);
  return Array.isArray(sessions) ? sessions : [];
}

export function saveVoiceSession(scope, session) {
  if (!session?.id) return;
  const existing = listVoiceSessions(scope).filter((item) => item?.id !== session.id);
  const next = [session, ...existing].slice(0, 30);
  writeJson(getStorageKey(VOICE_PREFIX, scope), next);
}

export function listChatSessions(scope) {
  const sessions = readJson(getStorageKey(CHAT_PREFIX, scope), []);
  return Array.isArray(sessions) ? sessions : [];
}

export function saveChatSession(scope, session) {
  if (!session?.id) return;
  const existing = listChatSessions(scope).filter((item) => item?.id !== session.id);
  const next = [session, ...existing].slice(0, 40);
  writeJson(getStorageKey(CHAT_PREFIX, scope), next);
}

export function deleteChatSession(scope, id) {
  const next = listChatSessions(scope).filter((item) => item?.id !== id);
  writeJson(getStorageKey(CHAT_PREFIX, scope), next);
  return next;
}

export function loadChatPreferences(scope) {
  return readJson(getStorageKey(PREFS_PREFIX, scope), {
    tone: "concise",
    rememberContext: true,
    autoOpenActions: true,
  });
}

export function saveChatPreferences(scope, preferences) {
  writeJson(getStorageKey(PREFS_PREFIX, scope), preferences || {});
}
