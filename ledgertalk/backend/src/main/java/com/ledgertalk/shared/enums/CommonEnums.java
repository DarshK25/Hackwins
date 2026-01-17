// src/main/java/com/ledgertalk/shared/enums/CommonEnums.java
package com.ledgertalk.shared.enums;

public class CommonEnums {

    public enum Status {
        ACTIVE, INACTIVE, SUSPENDED, DELETED
    }

    public enum Priority {
        LOW, MEDIUM, HIGH, URGENT
    }

    public enum EventType {
        INVOICE_CREATED, INVOICE_PAID, CLIENT_CREATED, USER_INVITED, ORG_CREATED, REMINDER_SCHEDULED
    }

    public enum AuditAction {
        CREATE, UPDATE, DELETE, VIEW
    }
}