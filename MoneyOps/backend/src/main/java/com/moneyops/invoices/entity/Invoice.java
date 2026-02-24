package com.moneyops.invoices.entity;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Document(collection = "invoices")
@Data
public class Invoice {

    @Id
    @org.springframework.data.mongodb.core.mapping.Field("_id")
    private String id;

    private UUID orgId;
    private String invoiceNumber;
    private UUID clientId;
    private String clientName;     // Snapshot of client name at time of creation
    private String clientEmail;    // Snapshot of client email
    private String clientCompany;  // Snapshot of client company
    private String clientPhone;    // Snapshot of client phone
    private LocalDate issueDate;
    private LocalDate dueDate;
    private InvoiceStatus status = InvoiceStatus.DRAFT;
    private BigDecimal subtotal;
    private BigDecimal gstTotal;
    private BigDecimal totalAmount;
    private String currency = "INR";
    private LocalDate paymentDate;
    private String notes;

    // Items embedded directly in the invoice document (no separate collection needed)
    private List<InvoiceItem> items;

    private LocalDateTime createdAt = LocalDateTime.now();
    private LocalDateTime updatedAt = LocalDateTime.now();
    private UUID createdBy;
}