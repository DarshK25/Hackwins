// src/main/java/com/moneyops/invoices/service/InvoiceService.java
package com.moneyops.invoices.service;

import com.moneyops.clients.repository.ClientRepository;
import com.lowagie.text.Document;
import com.lowagie.text.DocumentException;
import com.lowagie.text.Element;
import com.lowagie.text.FontFactory;
import com.lowagie.text.PageSize;
import com.lowagie.text.Paragraph;
import com.lowagie.text.Phrase;
import com.lowagie.text.pdf.PdfPCell;
import com.lowagie.text.pdf.PdfPTable;
import com.lowagie.text.pdf.PdfWriter;
import com.moneyops.invoices.dto.InvoiceDto;
import com.moneyops.invoices.dto.InvoiceItemDto;
import com.moneyops.invoices.entity.Invoice;
import com.moneyops.invoices.entity.InvoiceItem;
import com.moneyops.invoices.entity.InvoiceStatus;
import com.moneyops.invoices.mapper.InvoiceMapper;
import com.moneyops.clients.mapper.ClientMapper;
import com.moneyops.clients.dto.ClientDto;
import com.moneyops.invoices.repository.InvoiceRepository;
import com.moneyops.invoices.validator.InvoiceValidator;
import com.moneyops.invites.EmailService;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.security.team.TeamActionAuthorizationService;
import com.moneyops.shared.exceptions.ValidationException;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.io.ByteArrayOutputStream;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;


@Service
@RequiredArgsConstructor
@Transactional
public class InvoiceService {

    private final InvoiceRepository invoiceRepository;
    private final ClientRepository clientRepository;
    private final InvoiceMapper invoiceMapper;
    private final ClientMapper clientMapper;
    private final InvoiceValidator invoiceValidator;
    private final com.moneyops.audit.service.AuditLogService auditLogService;
    private final com.moneyops.transactions.service.TransactionService transactionService;
    private final TeamActionAuthorizationService teamActionAuthorizationService;
    private final EmailService emailService;
    private final BusinessOrganizationRepository orgRepository;

    public List<InvoiceDto> getAllInvoices(String orgId) {
        if (orgId == null || orgId.isBlank()) throw new com.moneyops.shared.exceptions.UnauthorizedException("Missing organization context");
        var invoices = invoiceRepository.findAllByOrgIdAndDeletedAtIsNull(orgId);
        return populateClientDetails(invoices, orgId);
    }

    public void validateAndCalculate(InvoiceDto dto) {
        invoiceValidator.validate(dto);
    }

    public List<InvoiceDto> searchInvoices(String orgId, String status, String clientName, String clientId, int limit) {
        List<Invoice> allInvoices = invoiceRepository.findAllByOrgIdAndDeletedAtIsNull(orgId);
        
        // Use a wrapper or just process sequentially to keep it simple and final-safe
        List<Invoice> filtered = allInvoices;

        // 1. Filter by status if provided
        if (status != null && !status.trim().isEmpty()) {
            final String targetStatus = status.toUpperCase();
            filtered = filtered.stream()
                    .filter(inv -> inv.getStatus().name().equals(targetStatus))
                    .collect(Collectors.toList());
        }

        // 2. Filter by clientId if provided
        if (clientId != null && !clientId.trim().isEmpty()) {
            filtered = filtered.stream()
                    .filter(inv -> inv.getClientId() != null && inv.getClientId().equals(clientId))
                    .collect(Collectors.toList());
        }

        // 3. Filter by client name (Fuzzy Match) - only if clientId is NOT provided
        if ((clientId == null || clientId.trim().isEmpty()) && clientName != null && !clientName.trim().isEmpty()) {
            final String query = clientName.toLowerCase().trim();
            var clients = clientRepository.findAllByOrgIdAndDeletedAtIsNull(orgId);
            org.apache.commons.text.similarity.JaroWinklerSimilarity similarity = new org.apache.commons.text.similarity.JaroWinklerSimilarity();
            
            var matchedClientIds = clients.stream()
                .filter(c -> similarity.apply(query, c.getName().toLowerCase()) > 0.85)
                .map(com.moneyops.clients.entity.Client::getId)
                .collect(Collectors.toSet());
                
            filtered = filtered.stream()
                .filter(inv -> inv.getClientId() != null && matchedClientIds.contains(inv.getClientId()))
                .collect(Collectors.toList());
        }

        return populateClientDetails(filtered.stream().limit(limit).collect(Collectors.toList()), orgId);
    }

    public InvoiceDto getInvoiceById(String id, String orgId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));

        return populateClientDetails(invoice);
    }

    public InvoiceDto createInvoice(InvoiceDto dto, String orgId, String userId) {
        if (orgId == null || orgId.isBlank()) throw new com.moneyops.shared.exceptions.UnauthorizedException("Missing organization context");

        if (userId == null || userId.isBlank()) {
            throw new com.moneyops.shared.exceptions.UnauthorizedException("Missing user context");
        }

        // Enforce protected create rules (membership + active status + PIN).
        var creator = teamActionAuthorizationService.assertUserCanCreateSensitiveAction(
                orgId,
                userId,
                dto.getTeamActionCode()
        );

        // Default source to MANUAL if caller didn't specify.
        if (dto.getSource() == null || dto.getSource().isBlank()) {
            dto.setSource("MANUAL");
        }

        // ✨ Idempotency check 
        if (dto.getIdempotencyKey() != null) {
            var existing = invoiceRepository.findByOrgIdAndInvoiceNumberAndDeletedAtIsNull(orgId, dto.getInvoiceNumber());
            if (existing.isPresent()) return populateClientDetails(existing.get());
        }

        invoiceValidator.validate(dto);

        if (dto.getClientId() != null) {
            clientRepository.findByIdAndOrgIdAndDeletedAtIsNull(dto.getClientId(), orgId).ifPresentOrElse(client -> {
                // Lock in the snapshot data
                dto.setClientName(client.getName());
                dto.setClientEmail(client.getEmail());
                dto.setClientCompany(client.getCompany());
                dto.setClientPhone(client.getPhoneNumber());
            }, () -> {
                throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found.");
            });
        }

        Invoice invoice = invoiceMapper.toEntity(dto);
        invoice.setOrgId(orgId);
        invoice.setCreatedBy(creator.userId());
        invoice.setCreatedByEmail(creator.email());
        invoice.setCreatedByRole(creator.role());
        invoice.setSource(dto.getSource());
        
        // Auto-generate invoice number if not provided
        if (invoice.getInvoiceNumber() == null || invoice.getInvoiceNumber().trim().isEmpty()) {
            String dateStamp = java.time.format.DateTimeFormatter.ofPattern("yyyyMMdd").format(java.time.LocalDate.now());
            String randomStr = UUID.randomUUID().toString().substring(0, 4).toUpperCase();
            invoice.setInvoiceNumber("INV-" + dateStamp + "-" + randomStr);
        }

        invoice.setStatus(InvoiceStatus.DRAFT);
        invoice.setCreatedAt(LocalDateTime.now());
        invoice.setUpdatedAt(LocalDateTime.now());
        // Balance initialization
        invoice.setAmountPaid(BigDecimal.ZERO);
        invoice.setBalanceDue(BigDecimal.ZERO); // Will be updated by recalculateInvoiceTotals

        // Recalculate totals server-side (do not trust frontend)
        recalculateInvoiceTotals(invoice);

        Invoice saved = invoiceRepository.save(invoice);
        auditLogService.logCreate("INVOICE", saved.getId(), saved);
        return populateClientDetails(saved);
    }

    public InvoiceDto updateInvoice(String id, InvoiceDto dto, String orgId) {
        Invoice existing = invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));

        if (existing.getStatus() != InvoiceStatus.DRAFT) {
            throw new IllegalStateException("Can only update draft invoices");
        }

        invoiceValidator.validate(dto);

        Invoice updated = invoiceMapper.toEntity(dto);
        updated.setId(id);
        updated.setOrgId(orgId);
        updated.setCreatedAt(existing.getCreatedAt());
        updated.setCreatedBy(existing.getCreatedBy());
        updated.setCreatedByEmail(existing.getCreatedByEmail());
        updated.setCreatedByRole(existing.getCreatedByRole());
        updated.setSource(existing.getSource());
        updated.setUpdatedAt(LocalDateTime.now());
        updated.setAmountPaid(existing.getAmountPaid()); // Preserve amount paid

        // Since items are embedded, simply saving the updated invoice includes its items
        recalculateInvoiceTotals(updated); // Recalculate totals after item changes
        Invoice saved = invoiceRepository.save(updated);
        return populateClientDetails(saved);
    }

    public void deleteInvoice(String id, String orgId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));

        if (invoice.getStatus() == InvoiceStatus.PAID) {
            throw new IllegalStateException("Cannot delete paid invoices");
        }

        // ✨ Soft Delete
        invoice.setDeletedAt(LocalDateTime.now());
        invoiceRepository.save(invoice);
    }

    public InvoiceDto sendInvoice(String id, String orgId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));

        if (invoice.getClientEmail() == null || invoice.getClientEmail().isBlank()) {
            throw new ValidationException("Invoice recipient email is missing.");
        }

        InvoiceStatus currentStatus = invoice.getStatus();
        if (currentStatus == InvoiceStatus.PAID) {
            throw new ValidationException("Paid invoices cannot be sent.");
        }
        if (currentStatus == InvoiceStatus.OVERDUE) {
            throw new ValidationException("Overdue invoices cannot be sent until they are updated or resent through the allowed workflow.");
        }
        if (currentStatus != InvoiceStatus.DRAFT && currentStatus != InvoiceStatus.SENT) {
            throw new ValidationException("Only draft or sent invoices can be emailed.");
        }

        String orgName = getOrganizationDisplayName(orgId);
        String subject = buildInvoiceEmailSubject(invoice, orgName);
        String htmlContent = buildInvoiceEmailContent(invoice, orgName);
        emailService.sendInvoiceEmail(invoice.getClientEmail(), subject, htmlContent);

        Invoice beforeUpdate = invoiceMapper.toEntity(invoiceMapper.toDto(invoice));
        if (currentStatus == InvoiceStatus.DRAFT) {
            invoice.setStatus(InvoiceStatus.SENT);
        }
        invoice.setUpdatedAt(LocalDateTime.now());
        Invoice saved = invoiceRepository.save(invoice);
        auditLogService.logUpdate("INVOICE", saved.getId(), beforeUpdate, saved);
        return populateClientDetails(saved);
    }

    public InvoiceDto markPaid(String id, String orgId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));

        if (invoice.getStatus() != InvoiceStatus.SENT) {
            throw new IllegalStateException("Can only mark sent invoices as paid");
        }

        invoice.setStatus(InvoiceStatus.PAID);
        invoice.setPaymentDate(LocalDate.now());
        invoice.setAmountPaid(invoice.getTotalAmount());
        invoice.setBalanceDue(BigDecimal.ZERO);
        invoice.setUpdatedAt(LocalDateTime.now());
        Invoice saved = invoiceRepository.save(invoice);
        return populateClientDetails(saved);
    }

    public byte[] generateInvoicePdf(String id, String orgId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));

        String orgName = getOrganizationDisplayName(orgId);
        try (ByteArrayOutputStream outputStream = new ByteArrayOutputStream()) {
            Document document = new Document(PageSize.A4, 36, 36, 36, 36);
            PdfWriter.getInstance(document, outputStream);
            document.open();

            addTitle(document, "Invoice " + invoice.getInvoiceNumber());
            addText(document, orgName, 14, true);
            addSpacer(document, 8);

            PdfPTable summaryTable = new PdfPTable(2);
            summaryTable.setWidthPercentage(100);
            summaryTable.setSpacingAfter(16);
            summaryTable.setWidths(new float[]{1f, 1f});
            summaryTable.getDefaultCell().setBorder(PdfPCell.NO_BORDER);
            summaryTable.addCell(buildBorderlessCell("Client", true));
            summaryTable.addCell(buildBorderlessCell("Invoice Details", true));
            summaryTable.addCell(buildBorderlessCell(safe(invoice.getClientName()), false));
            summaryTable.addCell(buildBorderlessCell(
                    "Issue Date: " + formatDate(invoice.getIssueDate()) + "\n" +
                    "Due Date: " + formatDate(invoice.getDueDate()) + "\n" +
                    "Status: " + invoice.getStatus().name(),
                    false
            ));
            if (invoice.getClientEmail() != null && !invoice.getClientEmail().isBlank()) {
                summaryTable.addCell(buildBorderlessCell(invoice.getClientEmail(), false));
            } else {
                summaryTable.addCell(buildBorderlessCell("No client email", false));
            }
            summaryTable.addCell(buildBorderlessCell("Currency: " + safe(invoice.getCurrency()), false));
            document.add(summaryTable);

            PdfPTable itemsTable = new PdfPTable(4);
            itemsTable.setWidthPercentage(100);
            itemsTable.setWidths(new float[]{4f, 1f, 2f, 2f});
            itemsTable.setSpacingAfter(16);
            itemsTable.addCell(buildHeaderCell("Description"));
            itemsTable.addCell(buildHeaderCell("Qty"));
            itemsTable.addCell(buildHeaderCell("Rate"));
            itemsTable.addCell(buildHeaderCell("Amount"));

            if (invoice.getItems() != null && !invoice.getItems().isEmpty()) {
                for (InvoiceItem item : invoice.getItems()) {
                    itemsTable.addCell(buildBodyCell(safe(item.getDescription())));
                    itemsTable.addCell(buildBodyCell(String.valueOf(item.getQuantity())));
                    itemsTable.addCell(buildBodyCell(formatMoney(item.getRate())));
                    itemsTable.addCell(buildBodyCell(formatMoney(item.getLineTotal())));
                }
            } else {
                PdfPCell emptyCell = buildBodyCell("No line items");
                emptyCell.setColspan(4);
                emptyCell.setHorizontalAlignment(Element.ALIGN_CENTER);
                itemsTable.addCell(emptyCell);
            }
            document.add(itemsTable);

            PdfPTable totalsTable = new PdfPTable(2);
            totalsTable.setHorizontalAlignment(Element.ALIGN_RIGHT);
            totalsTable.setWidthPercentage(45);
            totalsTable.setWidths(new float[]{1.5f, 1f});
            totalsTable.addCell(buildBorderlessCell("Subtotal", true));
            totalsTable.addCell(buildBorderlessCell(formatMoney(invoice.getSubtotal()), false));
            totalsTable.addCell(buildBorderlessCell("GST", true));
            totalsTable.addCell(buildBorderlessCell(formatMoney(invoice.getGstTotal()), false));
            totalsTable.addCell(buildBorderlessCell("Total", true));
            totalsTable.addCell(buildBorderlessCell(formatMoney(invoice.getTotalAmount()), true));
            document.add(totalsTable);

            if (invoice.getNotes() != null && !invoice.getNotes().isBlank()) {
                addSpacer(document, 16);
                addText(document, "Notes", 12, true);
                addText(document, invoice.getNotes(), 11, false);
            }

            if (invoice.getTermsAndConditions() != null && !invoice.getTermsAndConditions().isBlank()) {
                addSpacer(document, 12);
                addText(document, "Terms and Conditions", 12, true);
                addText(document, invoice.getTermsAndConditions(), 11, false);
            }

            document.close();
            return outputStream.toByteArray();
        } catch (DocumentException | java.io.IOException ex) {
            throw new RuntimeException("Failed to generate invoice PDF", ex);
        }
    }

    public List<InvoiceDto> getOverdueInvoices(String orgId) {
        List<Invoice> overdue = invoiceRepository.findOverdueByOrgId(orgId, LocalDate.now());
        for (Invoice invoice : overdue) {
            invoice.setStatus(InvoiceStatus.OVERDUE);
            invoiceRepository.save(invoice);
        }
        return populateClientDetails(overdue, orgId);
    }

    // InvoiceItem operations
    public InvoiceItemDto addItem(String invoiceId, InvoiceItemDto itemDto, String orgId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(invoiceId, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));

        if (invoice.getStatus() != InvoiceStatus.DRAFT) {
            throw new IllegalStateException("Can only add items to draft invoices");
        }

        InvoiceItem item = new InvoiceItem();
        item.setType(InvoiceItem.ItemType.valueOf(itemDto.getType()));
        item.setDescription(itemDto.getDescription());
        item.setQuantity(itemDto.getQuantity());
        item.setRate(itemDto.getRate());
        item.setGstPercent(itemDto.getGstPercent());

        // Calculate line amounts
        var qty = item.getType() == InvoiceItem.ItemType.SERVICE ? 1 : item.getQuantity();
        var lineSubtotal = item.getRate().multiply(BigDecimal.valueOf(qty));
        var lineGst = lineSubtotal.multiply(item.getGstPercent().divide(BigDecimal.valueOf(100)));
        var lineTotal = lineSubtotal.add(lineGst);

        item.setLineSubtotal(lineSubtotal);
        item.setLineGst(lineGst);
        item.setLineTotal(lineTotal);

        if (invoice.getItems() == null) {
            invoice.setItems(new java.util.ArrayList<>());
        }
        invoice.getItems().add(item);

        // Recalculate invoice totals
        recalculateInvoiceTotals(invoice);

        invoiceRepository.save(invoice);
        return invoiceMapper.toItemDto(item);
    }

    public void updateItem(String itemId, InvoiceItemDto itemDto, String orgId) {
        // Need to find which invoice contains this item
        // In MongoDB we usually know the invoice ID, but if only itemId is provided:
        Invoice invoice = invoiceRepository.findAllByOrgIdAndDeletedAtIsNull(orgId).stream()
                .filter(inv -> inv.getItems() != null && inv.getItems().stream().anyMatch(i -> i.getId().equals(itemId)))
                .findFirst()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Item not found in any invoice for this org"));

        if (invoice.getStatus() != InvoiceStatus.DRAFT) {
            throw new IllegalStateException("Can only update items in draft invoices");
        }

        InvoiceItem item = invoice.getItems().stream()
                .filter(i -> i.getId().equals(itemId))
                .findFirst()
                .get();

        item.setDescription(itemDto.getDescription());
        item.setQuantity(itemDto.getQuantity());
        item.setRate(itemDto.getRate());
        item.setGstPercent(itemDto.getGstPercent());

        // Recalculate
        var qty = item.getType() == InvoiceItem.ItemType.SERVICE ? 1 : item.getQuantity();
        var lineSubtotal = item.getRate().multiply(BigDecimal.valueOf(qty));
        var lineGst = lineSubtotal.multiply(item.getGstPercent().divide(BigDecimal.valueOf(100)));
        var lineTotal = lineSubtotal.add(lineGst);

        item.setLineSubtotal(lineSubtotal);
        item.setLineGst(lineGst);
        item.setLineTotal(lineTotal);

        // Recalculate invoice totals
        recalculateInvoiceTotals(invoice);
        invoiceRepository.save(invoice);
    }

    public void deleteItem(String itemId, String orgId) {
        Invoice invoice = invoiceRepository.findAllByOrgIdAndDeletedAtIsNull(orgId).stream()
                .filter(inv -> inv.getItems() != null && inv.getItems().stream().anyMatch(i -> i.getId().equals(itemId)))
                .findFirst()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Item not found in any invoice for this org"));

        if (invoice.getStatus() != InvoiceStatus.DRAFT) {
            throw new IllegalStateException("Can only delete items from draft invoices");
        }

        invoice.getItems().removeIf(i -> i.getId().equals(itemId));

        // Recalculate invoice totals
        recalculateInvoiceTotals(invoice);
        invoiceRepository.save(invoice);
    }

    private void recalculateInvoiceTotals(Invoice invoice) {
        BigDecimal subtotal = BigDecimal.ZERO;
        BigDecimal gstTotal = BigDecimal.ZERO;
        BigDecimal totalAmount = BigDecimal.ZERO;

        if (invoice.getItems() != null) {
            for (InvoiceItem item : invoice.getItems()) {
                subtotal = subtotal.add(item.getLineSubtotal());
                gstTotal = gstTotal.add(item.getLineGst());
                totalAmount = totalAmount.add(item.getLineTotal());
            }
        }

        invoice.setSubtotal(subtotal);
        invoice.setGstTotal(gstTotal);
        invoice.setTotalAmount(totalAmount);
        
        // Update balance due
        BigDecimal paid = invoice.getAmountPaid() != null ? invoice.getAmountPaid() : BigDecimal.ZERO;
        invoice.setBalanceDue(totalAmount.subtract(paid));
        invoice.setUpdatedAt(LocalDateTime.now());
    }

    private InvoiceDto populateClientDetails(Invoice invoice) {
        InvoiceDto dto = invoiceMapper.toDto(invoice);
        
        // If snapshot exists, it's already in the DTO from mapping.
        // We only fallback to lookup if snapshot is missing (for legacy data).
        if (dto.getClientName() == null && invoice.getClientId() != null) {
            clientRepository.findByIdAndOrgIdAndDeletedAtIsNull(invoice.getClientId(), invoice.getOrgId())
                    .ifPresentOrElse(client -> {
                        dto.setClientName(client.getName());
                        dto.setClientEmail(client.getEmail());
                        dto.setClientCompany(client.getCompany());
                        dto.setClientPhone(client.getPhoneNumber());
                    }, () -> {
                        dto.setClientName("Unknown Client (Orphan)");
                    });
        }
        return dto;
    }

    private List<InvoiceDto> populateClientDetails(List<Invoice> invoices, String orgId) {
        return invoices.stream()
                .map(this::populateClientDetails)
                .collect(Collectors.toList());
    }

    private String getOrganizationDisplayName(String orgId) {
        return orgRepository.findByIdAndDeletedAtIsNull(orgId)
                .map(org -> {
                    if (org.getTradingName() != null && !org.getTradingName().isBlank()) {
                        return org.getTradingName();
                    }
                    if (org.getLegalName() != null && !org.getLegalName().isBlank()) {
                        return org.getLegalName();
                    }
                    return "MoneyOps";
                })
                .orElse("MoneyOps");
    }

    private String buildInvoiceEmailSubject(Invoice invoice, String orgName) {
        return "Invoice " + invoice.getInvoiceNumber() + " from " + orgName;
    }

    private String buildInvoiceEmailContent(Invoice invoice, String orgName) {
        String issueDate = invoice.getIssueDate() != null
                ? invoice.getIssueDate().format(DateTimeFormatter.ofPattern("dd MMM yyyy"))
                : "N/A";
        String dueDate = invoice.getDueDate() != null
                ? invoice.getDueDate().format(DateTimeFormatter.ofPattern("dd MMM yyyy"))
                : "N/A";
        String clientName = invoice.getClientName() != null && !invoice.getClientName().isBlank()
                ? invoice.getClientName()
                : "Customer";

        String itemsHtml = "";
        if (invoice.getItems() != null && !invoice.getItems().isEmpty()) {
            itemsHtml = invoice.getItems().stream()
                    .map(item -> "<tr>" +
                            "<td style='padding: 8px 0; color: #333;'>" + safe(item.getDescription()) + "</td>" +
                            "<td style='padding: 8px 0; color: #666; text-align: right;'>" + item.getQuantity() + "</td>" +
                            "<td style='padding: 8px 0; color: #666; text-align: right;'>INR " + item.getRate() + "</td>" +
                            "<td style='padding: 8px 0; color: #111; text-align: right; font-weight: 600;'>INR " + item.getLineTotal() + "</td>" +
                            "</tr>")
                    .collect(Collectors.joining());
            itemsHtml = "<table style='width: 100%; border-collapse: collapse; margin-top: 16px;'>" +
                    "<thead><tr>" +
                    "<th style='text-align: left; padding-bottom: 8px; color: #666; border-bottom: 1px solid #eee;'>Item</th>" +
                    "<th style='text-align: right; padding-bottom: 8px; color: #666; border-bottom: 1px solid #eee;'>Qty</th>" +
                    "<th style='text-align: right; padding-bottom: 8px; color: #666; border-bottom: 1px solid #eee;'>Rate</th>" +
                    "<th style='text-align: right; padding-bottom: 8px; color: #666; border-bottom: 1px solid #eee;'>Amount</th>" +
                    "</tr></thead><tbody>" + itemsHtml + "</tbody></table>";
        }

        return "<div style='font-family: Arial, sans-serif; max-width: 640px; margin: 0 auto; padding: 24px; border: 1px solid #eee; border-radius: 12px;'>" +
                "<h2 style='color: #111; margin-top: 0;'>Invoice " + safe(invoice.getInvoiceNumber()) + "</h2>" +
                "<p style='color: #444;'>Hello " + safe(clientName) + ",</p>" +
                "<p style='color: #444;'>Please find your invoice details below from <strong>" + safe(orgName) + "</strong>.</p>" +
                "<div style='background: #f8f8f8; border-radius: 10px; padding: 16px; margin: 20px 0;'>" +
                "<p style='margin: 0 0 8px; color: #666;'>Issue Date: <strong style='color: #111;'>" + issueDate + "</strong></p>" +
                "<p style='margin: 0 0 8px; color: #666;'>Due Date: <strong style='color: #111;'>" + dueDate + "</strong></p>" +
                "<p style='margin: 0; color: #666;'>Total Amount: <strong style='color: #111;'>INR " + invoice.getTotalAmount() + "</strong></p>" +
                "</div>" +
                itemsHtml +
                "<p style='margin-top: 20px; color: #444;'>If you have any questions, please reply to this email.</p>" +
                "<p style='margin-top: 24px; color: #777; font-size: 12px;'>Sent via MoneyOps</p>" +
                "</div>";
    }

    private String safe(String value) {
        return value == null ? "" : value;
    }

    private String formatDate(LocalDate date) {
        return date == null ? "N/A" : date.format(DateTimeFormatter.ofPattern("dd MMM yyyy"));
    }

    private String formatMoney(BigDecimal amount) {
        return "INR " + (amount == null ? BigDecimal.ZERO : amount);
    }

    private void addTitle(Document document, String text) throws DocumentException {
        var title = new Paragraph(text, FontFactory.getFont(FontFactory.HELVETICA_BOLD, 20));
        title.setSpacingAfter(8);
        document.add(title);
    }

    private void addText(Document document, String text, float size, boolean bold) throws DocumentException {
        var fontName = bold ? FontFactory.HELVETICA_BOLD : FontFactory.HELVETICA;
        var paragraph = new Paragraph(text, FontFactory.getFont(fontName, size));
        paragraph.setSpacingAfter(4);
        document.add(paragraph);
    }

    private void addSpacer(Document document, float spacing) throws DocumentException {
        Paragraph spacer = new Paragraph(" ");
        spacer.setSpacingAfter(spacing);
        document.add(spacer);
    }

    private PdfPCell buildHeaderCell(String text) {
        PdfPCell cell = new PdfPCell(new Phrase(text, FontFactory.getFont(FontFactory.HELVETICA_BOLD, 11)));
        cell.setPadding(8);
        return cell;
    }

    private PdfPCell buildBodyCell(String text) {
        PdfPCell cell = new PdfPCell(new Phrase(text, FontFactory.getFont(FontFactory.HELVETICA, 10)));
        cell.setPadding(8);
        return cell;
    }

    private PdfPCell buildBorderlessCell(String text, boolean bold) {
        var fontName = bold ? FontFactory.HELVETICA_BOLD : FontFactory.HELVETICA;
        PdfPCell cell = new PdfPCell(new Phrase(text, FontFactory.getFont(fontName, 11)));
        cell.setBorder(PdfPCell.NO_BORDER);
        cell.setPadding(4);
        return cell;
    }

    public List<com.moneyops.audit.entity.AuditLog> getInvoiceLogs(String id, String orgId) {
        // First verify ownership
        getInvoiceById(id, orgId);
        return auditLogService.getAuditLogsByEntityId(id);
    }

    public List<com.moneyops.transactions.dto.TransactionDto> getInvoicePayments(String id, String orgId) {
        // First verify ownership
        getInvoiceById(id, orgId);
        return transactionService.getTransactionsByInvoice(id, orgId);
    }

    public com.moneyops.transactions.dto.TransactionDto recordPayment(String id, com.moneyops.transactions.dto.TransactionDto paymentDto, String orgId, String userId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));
        
        paymentDto.setInvoiceId(id);
        paymentDto.setClientId(invoice.getClientId());
        paymentDto.setType("INCOME");
        if (paymentDto.getCurrency() == null) paymentDto.setCurrency(invoice.getCurrency());
        
        // Ensure transaction date is present for validation
        if (paymentDto.getTransactionDate() == null) {
            paymentDto.setTransactionDate(LocalDate.now());
        }

        // ✨ We don't call transactionService here if we want to avoid double-processing, 
        // but transactionService is where the DB write happens.
        com.moneyops.transactions.dto.TransactionDto saved = transactionService.createTransaction(paymentDto, orgId, userId);

        // ✨ Denormalized sync
        BigDecimal paid = invoice.getAmountPaid() != null ? invoice.getAmountPaid() : BigDecimal.ZERO;
        invoice.setAmountPaid(paid.add(paymentDto.getAmount()));
        invoice.setBalanceDue(invoice.getTotalAmount().subtract(invoice.getAmountPaid()));
        
        if (invoice.getBalanceDue().compareTo(BigDecimal.ZERO) <= 0) {
            invoice.setStatus(InvoiceStatus.PAID);
            invoice.setPaymentDate(paymentDto.getTransactionDate());
        } else if (invoice.getStatus() == InvoiceStatus.DRAFT) {
            invoice.setStatus(InvoiceStatus.SENT); // Transition out of draft if payment received
        }

        invoice.setUpdatedAt(LocalDateTime.now());
        invoiceRepository.save(invoice);
        
        return saved;
    }
}
