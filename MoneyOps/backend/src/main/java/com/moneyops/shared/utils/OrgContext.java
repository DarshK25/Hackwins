// src/main/java/com/moneyops/shared/utils/OrgContext.java
package com.moneyops.shared.utils;

import java.util.UUID;

public class OrgContext {

    private static final ThreadLocal<String> orgId = new ThreadLocal<>();
    private static final ThreadLocal<String> userId = new ThreadLocal<>();

    public static void setOrgId(String orgId) {
        OrgContext.orgId.set(orgId);
    }

    public static String getOrgId() {
        return orgId.get();
    }

    public static void setUserId(String userId) {
        OrgContext.userId.set(userId);
    }

    public static String getUserId() {
        return userId.get();
    }

    public static void clear() {
        orgId.remove();
        userId.remove();
    }
}