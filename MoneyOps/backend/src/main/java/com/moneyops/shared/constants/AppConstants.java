// src/main/java/com/moneyops/shared/constants/AppConstants.java
package com.moneyops.shared.constants;

public class AppConstants {

    public static final String API_VERSION = "v1";
    public static final String API_BASE_PATH = "/api/" + API_VERSION;

    public static final int DEFAULT_PAGE_SIZE = 20;
    public static final int MAX_PAGE_SIZE = 100;

    public static final String DEFAULT_CURRENCY = "INR";

    public static final long JWT_EXPIRATION_TIME = 86400000; // 24 hours
    public static final long REFRESH_TOKEN_EXPIRATION_TIME = 604800000; // 7 days

    public static final String HEADER_ORG_ID = "X-Org-Id";
    public static final String HEADER_USER_ID = "X-User-Id";

    public static final String ROLE_OWNER = "OWNER";
    public static final String ROLE_ADMIN = "ADMIN";
    public static final String ROLE_MANAGER = "MANAGER";
    public static final String ROLE_STAFF = "STAFF";
    public static final String ROLE_VIEWER = "VIEWER";
}