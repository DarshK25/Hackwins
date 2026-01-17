// src/main/java/com/ledgertalk/invoices/validator/InvoiceValidator.java
package com.ledgertalk.invoices.validator;

import com.ledgertalk.invoices.dto.InvoiceDto;
import com.ledgertalk.invoices.dto.InvoiceItemDto;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.List;

@Component
public class InvoiceValidator {

    public void validate(InvoiceDto dto) {
        if (dto.getInvoiceNumber() == null || dto.getInvoiceNumber().isEmpty()) {
            throw new IllegalArgumentException("Invoice number is required");
        }
        if (dto.getClientId() == null) {
            throw new IllegalArgumentException("Client ID is required");
        }
        if (dto.getIssueDate() == null) {
            throw new IllegalArgumentException("Issue date is required");
        }
        if (dto.getDueDate() == null) {
            throw new IllegalArgumentException("Due date is required");
        }
        if (dto.getDueDate().isBefore(dto.getIssueDate())) {
            throw new IllegalArgumentException("Due date cannot be before issue date");
        }
        if (dto.getItems() == null || dto.getItems().isEmpty()) {
            throw new IllegalArgumentException("At least one item is required");
        }
        validateItems(dto.getItems());
        calculateTotals(dto);
    }

    private void validateItems(List<InvoiceItemDto> items) {
        for (InvoiceItemDto item : items) {
            if (item.getDescription() == null || item.getDescription().isEmpty()) {
                throw new IllegalArgumentException("Item description is required");
            }
            if (item.getRate() == null || item.getRate().compareTo(BigDecimal.ZERO) <= 0) {
                throw new IllegalArgumentException("Item rate must be positive");
            }
            if (item.getGstPercent() == null || item.getGstPercent().compareTo(BigDecimal.ZERO) < 0) {
                throw new IllegalArgumentException("GST percent cannot be negative");
            }
            if ("SERVICE".equals(item.getType()) && item.getQuantity() != null) {
                throw new IllegalArgumentException("Quantity must be null for SERVICE items");
            }
            if ("PRODUCT".equals(item.getType()) && (item.getQuantity() == null || item.getQuantity() <= 0)) {
                throw new IllegalArgumentException("Quantity must be positive for PRODUCT items");
            }
        }
    }

    private void calculateTotals(InvoiceDto dto) {
        BigDecimal subtotal = BigDecimal.ZERO;
        BigDecimal gstTotal = BigDecimal.ZERO;
        BigDecimal total = BigDecimal.ZERO;

        for (InvoiceItemDto item : dto.getItems()) {
            BigDecimal qty = item.getType().equals("SERVICE") ? BigDecimal.ONE : BigDecimal.valueOf(item.getQuantity());
            BigDecimal lineSubtotal = item.getRate().multiply(qty);
            BigDecimal lineGst = lineSubtotal.multiply(item.getGstPercent().divide(BigDecimal.valueOf(100)));
            BigDecimal lineTotal = lineSubtotal.add(lineGst);

            item.setLineSubtotal(lineSubtotal);
            item.setLineGst(lineGst);
            item.setLineTotal(lineTotal);

            subtotal = subtotal.add(lineSubtotal);
            gstTotal = gstTotal.add(lineGst);
            total = total.add(lineTotal);
        }

        dto.setSubtotal(subtotal);
        dto.setGstTotal(gstTotal);
        dto.setTotalAmount(total);
    }
}