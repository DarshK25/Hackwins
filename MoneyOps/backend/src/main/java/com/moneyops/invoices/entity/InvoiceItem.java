package com.moneyops.invoices.entity;

import lombok.Data;

import java.math.BigDecimal;

/**
 * Embedded inside Invoice — NOT a separate MongoDB collection.
 * No @Document annotation needed here.
 */
@Data
public class InvoiceItem {

    private String id = java.util.UUID.randomUUID().toString();
    private ItemType type;
    private String description;
    private Integer quantity;
    private BigDecimal rate;
    private BigDecimal gstPercent;
    private BigDecimal lineSubtotal;
    private BigDecimal lineGst;
    private BigDecimal lineTotal;

    public enum ItemType {
        PRODUCT, SERVICE
    }
}