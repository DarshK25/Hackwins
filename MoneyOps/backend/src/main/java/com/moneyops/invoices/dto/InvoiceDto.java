// src/main/java/com/moneyops/invoices/dto/InvoiceDto.java
package com.moneyops.invoices.dto;

import com.moneyops.clients.dto.ClientDto;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

@Data
public class InvoiceDto {
    private String id;
    private String orgId;
    private String invoiceNumber;
    private String clientId;   // Standardized to String
    private String clientName;
    private String clientEmail;
    private String clientCompany;
    private String clientPhone;
    private ClientDto client;
    private LocalDate issueDate;
    private LocalDate dueDate;
    private String status;
    private BigDecimal subtotal;
    private BigDecimal gstTotal;
    private BigDecimal totalAmount;
    private BigDecimal amountPaid;
    private BigDecimal balanceDue;
    private String currency;
    private LocalDate paymentDate;
    private String notes;
    private String termsAndConditions;
    private List<InvoiceItemDto> items;
    private String idempotencyKey;
    private com.moneyops.invoices.entity.Invoice.VoiceContext voiceContext;
}
