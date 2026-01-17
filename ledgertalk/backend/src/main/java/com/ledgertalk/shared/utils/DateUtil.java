// src/main/java/com/ledgertalk/shared/utils/DateUtil.java
package com.ledgertalk.shared.utils;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public class DateUtil {

    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    public static String format(LocalDateTime dateTime) {
        return dateTime.format(FORMATTER);
    }

    public static LocalDateTime parse(String dateTimeStr) {
        return LocalDateTime.parse(dateTimeStr, FORMATTER);
    }

    public static LocalDateTime now() {
        return LocalDateTime.now();
    }

    public static boolean isExpired(LocalDateTime expiry) {
        return LocalDateTime.now().isAfter(expiry);
    }
}