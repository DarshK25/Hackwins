export const MAX_TEAM_SECURITY_ATTEMPTS = 2;

export function getTeamSecurityAttemptState(error, previousAttempts) {
    const message = String(error?.message || error || "");
    const normalized = message.toLowerCase();
    const isSecurityCodeError =
        normalized.includes("invalid team security code") ||
        normalized.includes("team security code is incorrect") ||
        normalized.includes("security code is incorrect");

    if (!isSecurityCodeError) {
        return {
            isSecurityCodeError: false,
            nextAttempts: previousAttempts,
            shouldCancel: false,
            message,
        };
    }

    const nextAttempts = previousAttempts + 1;
    const shouldCancel = nextAttempts >= MAX_TEAM_SECURITY_ATTEMPTS;

    return {
        isSecurityCodeError: true,
        nextAttempts,
        shouldCancel,
        message: shouldCancel
            ? "Incorrect team security code twice. Task cancelled."
            : "Incorrect team security code. Please try once more.",
    };
}
