// src/main/java/com/ledgertalk/invoices/dto/InvoiceItemDto.java
package com.ledgertalk.invoices.dto;

import lombok.Data;
import java.math.BigDecimal;

@Data
public class InvoiceItemDto {
    private String type;
    private String description;
    private Integer quantity;
    private BigDecimal rate;
    private BigDecimal gstPercent;
    private BigDecimal lineSubtotal;
    private BigDecimal lineGst;
    private BigDecimal lineTotal;
}