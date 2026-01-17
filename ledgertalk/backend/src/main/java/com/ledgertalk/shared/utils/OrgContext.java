// src/main/java/com/ledgertalk/shared/utils/OrgContext.java
package com.ledgertalk.shared.utils;

import java.util.UUID;

public class OrgContext {

    private static final ThreadLocal<UUID> orgId = new ThreadLocal<>();
    private static final ThreadLocal<UUID> userId = new ThreadLocal<>();

    public static void setOrgId(UUID orgId) {
        OrgContext.orgId.set(orgId);
    }

    public static UUID getOrgId() {
        return orgId.get();
    }

    public static void setUserId(UUID userId) {
        OrgContext.userId.set(userId);
    }

    public static UUID getUserId() {
        return userId.get();
    }

    public static void clear() {
        orgId.remove();
        userId.remove();
    }
}