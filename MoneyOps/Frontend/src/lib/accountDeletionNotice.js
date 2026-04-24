const STORAGE_KEY = "moneyops.accountDeletedNotice";

export function rememberDeletedAccountNotice(payload = {}) {
    if (typeof window === "undefined") return;

    window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
            businessName: payload.businessName || "",
            deletedAt: new Date().toISOString(),
        })
    );
}

export function consumeDeletedAccountNotice() {
    if (typeof window === "undefined") return null;

    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;

    window.localStorage.removeItem(STORAGE_KEY);

    try {
        const parsed = JSON.parse(raw);
        return {
            businessName: parsed.businessName || "",
            deletedAt: parsed.deletedAt || "",
        };
    } catch {
        return null;
    }
}
