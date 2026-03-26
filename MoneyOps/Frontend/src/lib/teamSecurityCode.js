const teamSecurityCodeStorageKey = (orgId) => `moneyops.teamSecurityCode.${orgId}`;

export function getRememberedTeamSecurityCode(orgId) {
    if (!orgId || typeof window === "undefined") return "";
    return window.localStorage.getItem(teamSecurityCodeStorageKey(orgId)) || "";
}

export function rememberTeamSecurityCode(orgId, code) {
    if (!orgId || typeof window === "undefined") return;
    const trimmed = (code || "").trim();
    if (!trimmed) return;
    window.localStorage.setItem(teamSecurityCodeStorageKey(orgId), trimmed);
}

export function clearRememberedTeamSecurityCode(orgId) {
    if (!orgId || typeof window === "undefined") return;
    window.localStorage.removeItem(teamSecurityCodeStorageKey(orgId));
}
