// src/main/java/com/ledgertalk/invoices/dto/InvoiceDto.java
package com.ledgertalk.invoices.dto;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

@Data
public class InvoiceDto {
    private UUID id;
    private String invoiceNumber;
    private UUID clientId;
    private LocalDate issueDate;
    private LocalDate dueDate;
    private String status;
    private BigDecimal subtotal;
    private BigDecimal gstTotal;
    private BigDecimal totalAmount;
    private String currency;
    private LocalDate paymentDate;
    private String notes;
    private List<InvoiceItemDto> items;
}