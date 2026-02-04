// src/main/java/com/moneyops/invoices/entity/InvoiceItem.java
package com.moneyops.invoices.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.math.BigDecimal;
import java.util.UUID;

@Entity
@Table(name = "invoice_items")
@Data
public class InvoiceItem {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "invoice_id", nullable = false)
    private Invoice invoice;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private ItemType type;

    @Column(nullable = false)
    private String description;

    private Integer quantity; // nullable for SERVICE

    @Column(nullable = false, precision = 19, scale = 2)
    private BigDecimal rate;

    @Column(nullable = false)
    private BigDecimal gstPercent;

    @Column(nullable = false, precision = 19, scale = 2)
    private BigDecimal lineSubtotal;

    @Column(nullable = false, precision = 19, scale = 2)
    private BigDecimal lineGst;

    @Column(nullable = false, precision = 19, scale = 2)
    private BigDecimal lineTotal;

    public enum ItemType {
        PRODUCT,
        SERVICE
    }
}