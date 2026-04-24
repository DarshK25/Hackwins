const teamSecurityCodeStorageKey = (orgId) => `moneyops.teamSecurityCode.${orgId}`;

export function getRememberedTeamSecurityCode(orgId) {
    if (orgId && typeof window !== "undefined") {
        window.localStorage.removeItem(teamSecurityCodeStorageKey(orgId));
    }
    return "";
}

export function rememberTeamSecurityCode(orgId, code) {
    if (!orgId || typeof window === "undefined") return;
    window.localStorage.removeItem(teamSecurityCodeStorageKey(orgId));
}

export function clearRememberedTeamSecurityCode(orgId) {
    if (!orgId || typeof window === "undefined") return;
    window.localStorage.removeItem(teamSecurityCodeStorageKey(orgId));
}
