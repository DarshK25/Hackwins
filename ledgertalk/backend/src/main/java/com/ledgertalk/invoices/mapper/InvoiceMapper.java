// src/main/java/com/ledgertalk/invoices/mapper/InvoiceMapper.java
package com.ledgertalk.invoices.mapper;

import com.ledgertalk.invoices.dto.InvoiceDto;
import com.ledgertalk.invoices.dto.InvoiceItemDto;
import com.ledgertalk.invoices.entity.Invoice;
import com.ledgertalk.invoices.entity.InvoiceItem;
import com.ledgertalk.invoices.entity.InvoiceStatus;

import org.springframework.stereotype.Component;

import java.util.stream.Collectors;

@Component
public class InvoiceMapper {

    public InvoiceDto toDto(Invoice invoice) {
        InvoiceDto dto = new InvoiceDto();
        dto.setId(invoice.getId());
        dto.setInvoiceNumber(invoice.getInvoiceNumber());
        dto.setClientId(invoice.getClientId());
        dto.setIssueDate(invoice.getIssueDate());
        dto.setDueDate(invoice.getDueDate());
        dto.setStatus(invoice.getStatus().name());
        dto.setSubtotal(invoice.getSubtotal());
        dto.setGstTotal(invoice.getGstTotal());
        dto.setTotalAmount(invoice.getTotalAmount());
        dto.setCurrency(invoice.getCurrency());
        dto.setPaymentDate(invoice.getPaymentDate());
        dto.setNotes(invoice.getNotes());
        if (invoice.getItems() != null) {
            dto.setItems(invoice.getItems().stream()
                    .map(this::toItemDto)
                    .collect(Collectors.toList()));
        }
        return dto;
    }

    public Invoice toEntity(InvoiceDto dto) {
        Invoice invoice = new Invoice();
        invoice.setId(dto.getId());
        invoice.setInvoiceNumber(dto.getInvoiceNumber());
        invoice.setClientId(dto.getClientId());
        invoice.setIssueDate(dto.getIssueDate());
        invoice.setDueDate(dto.getDueDate());
        invoice.setStatus(InvoiceStatus.valueOf(dto.getStatus()));
        invoice.setSubtotal(dto.getSubtotal());
        invoice.setGstTotal(dto.getGstTotal());
        invoice.setTotalAmount(dto.getTotalAmount());
        invoice.setCurrency(dto.getCurrency());
        invoice.setPaymentDate(dto.getPaymentDate());
        invoice.setNotes(dto.getNotes());
        if (dto.getItems() != null) {
            invoice.setItems(dto.getItems().stream()
                    .map(itemDto -> toItemEntity(itemDto, invoice))
                    .collect(Collectors.toList()));
        }
        return invoice;
    }

    public InvoiceItemDto toItemDto(InvoiceItem item) {
        InvoiceItemDto dto = new InvoiceItemDto();
        dto.setType(item.getType().name());
        dto.setDescription(item.getDescription());
        dto.setQuantity(item.getQuantity());
        dto.setRate(item.getRate());
        dto.setGstPercent(item.getGstPercent());
        dto.setLineSubtotal(item.getLineSubtotal());
        dto.setLineGst(item.getLineGst());
        dto.setLineTotal(item.getLineTotal());
        return dto;
    }

    private InvoiceItem toItemEntity(InvoiceItemDto dto, Invoice invoice) {
        InvoiceItem item = new InvoiceItem();
        item.setInvoice(invoice);
        item.setType(InvoiceItem.ItemType.valueOf(dto.getType()));
        item.setDescription(dto.getDescription());
        item.setQuantity(dto.getQuantity());
        item.setRate(dto.getRate());
        item.setGstPercent(dto.getGstPercent());
        item.setLineSubtotal(dto.getLineSubtotal());
        item.setLineGst(dto.getLineGst());
        item.setLineTotal(dto.getLineTotal());
        return item;
    }
}