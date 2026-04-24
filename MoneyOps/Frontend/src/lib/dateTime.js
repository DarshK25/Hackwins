function normalizeDateParts(value) {
    if (!Array.isArray(value) || value.length < 3) {
        return null;
    }

    const [
        year,
        month = 1,
        day = 1,
        hour = 0,
        minute = 0,
        second = 0,
        nanosecond = 0,
    ] = value.map((part) => Number(part) || 0);

    if (!year) {
        return null;
    }

    return new Date(
        year,
        Math.max(month - 1, 0),
        Math.max(day, 1),
        hour,
        minute,
        second,
        Math.floor(nanosecond / 1000000),
    );
}

export function parseAppDate(value) {
    if (!value) {
        return null;
    }

    if (value instanceof Date) {
        return Number.isNaN(value.getTime()) ? null : value;
    }

    if (Array.isArray(value)) {
        const parsedArrayDate = normalizeDateParts(value);
        return parsedArrayDate && !Number.isNaN(parsedArrayDate.getTime()) ? parsedArrayDate : null;
    }

    if (typeof value === "object") {
        if (typeof value.epochSecond === "number") {
            const epochDate = new Date(value.epochSecond * 1000);
            return Number.isNaN(epochDate.getTime()) ? null : epochDate;
        }

        if (typeof value.year === "number") {
            const parsedObjectDate = normalizeDateParts([
                value.year,
                value.monthValue ?? value.month ?? 1,
                value.dayOfMonth ?? value.day ?? 1,
                value.hour ?? 0,
                value.minute ?? 0,
                value.second ?? 0,
                value.nano ?? 0,
            ]);
            return parsedObjectDate && !Number.isNaN(parsedObjectDate.getTime()) ? parsedObjectDate : null;
        }
    }

    const parsedDate = new Date(value);
    return Number.isNaN(parsedDate.getTime()) ? null : parsedDate;
}

export function formatAppDateTime(value, locale = "en-IN", options = undefined) {
    const parsedDate = parseAppDate(value);
    return parsedDate ? parsedDate.toLocaleString(locale, options) : "N/A";
}
