package com.moneyops.invoices.entity;

import lombok.Data;

import java.math.BigDecimal;
import java.util.UUID;

/**
 * Embedded inside Invoice — NOT a separate MongoDB collection.
 * No @Document annotation needed here.
 */
@Data
public class InvoiceItem {

    private UUID id = UUID.randomUUID();
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