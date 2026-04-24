package com.moneyops.compliance;

import com.lowagie.text.*;
import com.lowagie.text.pdf.*;
import com.moneyops.invoices.entity.Invoice;
import com.moneyops.invoices.entity.InvoiceStatus;
import com.moneyops.invoices.repository.InvoiceRepository;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.entity.RegulatoryProfile;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.organizations.repository.RegulatoryProfileRepository;
import com.moneyops.transactions.dto.TransactionDto;
import com.moneyops.transactions.service.TransactionService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class CompliancePdfService {

    private final InvoiceRepository invoiceRepository;
    private final TransactionService transactionService;
    private final BusinessOrganizationRepository orgRepository;
    private final RegulatoryProfileRepository regulatoryProfileRepository;

    private static final Font TITLE_FONT = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 20, Color.BLACK);
    private static final Font HEADER_FONT = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 12, Color.DARK_GRAY);
    private static final Font NORMAL_FONT = FontFactory.getFont(FontFactory.HELVETICA, 10, Color.BLACK);
    private static final Font BOLD_FONT = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 10, Color.BLACK);
    private static final Font TH_FONT = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 10, Color.WHITE);
    private static final Color PRIMARY_COLOR = new Color(26, 26, 26);
    private static final Color ACCENT_COLOR = new Color(76, 187, 23); // Green

    public byte[] generateCompliancePdf(String orgId, String reportType, LocalDate dateFrom, LocalDate dateTo) {
        BusinessOrganization org = orgRepository.findByIdAndDeletedAtIsNull(orgId).orElse(null);
        RegulatoryProfile profile = regulatoryProfileRepository.findByOrgIdAndDeletedAtIsNull(orgId).orElse(null);

        // Fetch Invoices in Date Range
        List<Invoice> invoices = invoiceRepository.findAllByOrgIdAndDeletedAtIsNull(orgId).stream()
                .filter(inv -> {
                    LocalDate d = inv.getIssueDate();
                    if (d == null) return false;
                    return (d.isEqual(dateFrom) || d.isAfter(dateFrom)) && (d.isEqual(dateTo) || d.isBefore(dateTo));
                }).collect(Collectors.toList());

        // Fetch Transactions in Date Range
        List<TransactionDto> transactions = transactionService.getTransactionsByDateRange(orgId, dateFrom, dateTo);

        // Calcs
        BigDecimal totalRevenue = transactions.stream()
                .filter(t -> "INCOME".equalsIgnoreCase(t.getType()))
                .map(TransactionDto::getAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
                
        BigDecimal totalExpense = transactions.stream()
                .filter(t -> "EXPENSE".equalsIgnoreCase(t.getType()))
                .map(TransactionDto::getAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        // GST Collected from invoices (only if not draft/deleted, etc)
        BigDecimal gstCollected = invoices.stream()
                .filter(inv -> inv.getStatus() != InvoiceStatus.DRAFT)
                .map(inv -> inv.getGstTotal() != null ? inv.getGstTotal() : BigDecimal.ZERO)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        // GST Paid from transactions categorized as GST or TAX
        BigDecimal gstPaid = transactions.stream()
                .filter(t -> "EXPENSE".equalsIgnoreCase(t.getType()) && 
                            (t.getCategory() != null && t.getCategory().toUpperCase().contains("GST")))
                .map(TransactionDto::getAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        BigDecimal netGstPayable = gstCollected.subtract(gstPaid);

        try (ByteArrayOutputStream outputStream = new ByteArrayOutputStream()) {
            Document document = new Document(PageSize.A4, 40, 40, 40, 40);
            PdfWriter.getInstance(document, outputStream);
            document.open();

            // ── Header ───────────────────────────────────────────────
            String orgName = org != null && org.getLegalName() != null ? org.getLegalName() : "MoneyOps";
            document.add(new Paragraph(orgName, TITLE_FONT));
            
            String title = reportType != null ? reportType.replace("_", " ") : "COMPLIANCE REPORT";
            document.add(new Paragraph(title, HEADER_FONT));
            document.add(new Paragraph("Period: " + formatDate(dateFrom) + " to " + formatDate(dateTo), NORMAL_FONT));
            document.add(new Paragraph(" "));
            
            // Org & Regulatory Profile Info
            PdfPTable infoTable = new PdfPTable(2);
            infoTable.setWidthPercentage(100);
            infoTable.addCell(buildBorderlessCell("GSTIN: " + (profile != null && profile.getGstNumber() != null ? profile.getGstNumber() : "N/A"), BOLD_FONT));
            infoTable.addCell(buildBorderlessCell("PAN: " + (profile != null && profile.getPanNumber() != null ? profile.getPanNumber() : "N/A"), BOLD_FONT));
            infoTable.addCell(buildBorderlessCell("CIN/LLPIN: " + (profile != null && profile.getCinOrLlpIn() != null ? profile.getCinOrLlpIn() : "N/A"), BOLD_FONT));
            infoTable.addCell(buildBorderlessCell("TAN: " + (profile != null && profile.getTanNumber() != null ? profile.getTanNumber() : "N/A"), BOLD_FONT));
            document.add(infoTable);
            document.add(new Paragraph(" "));
            document.add(new Paragraph(" "));

            // ── Financial Summary ────────────────────────────────────
            document.add(new Paragraph("Financial Summary", HEADER_FONT));
            document.add(new Paragraph(" "));
            
            PdfPTable financialTable = new PdfPTable(2);
            financialTable.setWidthPercentage(60);
            financialTable.setHorizontalAlignment(Element.ALIGN_LEFT);
            financialTable.addCell(buildBorderedCell("Total Revenue", NORMAL_FONT));
            financialTable.addCell(buildBorderedCellRight(formatMoney(totalRevenue), BOLD_FONT));
            financialTable.addCell(buildBorderedCell("Total Expense", NORMAL_FONT));
            financialTable.addCell(buildBorderedCellRight(formatMoney(totalExpense), BOLD_FONT));
            document.add(financialTable);
            document.add(new Paragraph(" "));

            // ── GST Summary ──────────────────────────────────────────
            document.add(new Paragraph("GST Summary", HEADER_FONT));
            document.add(new Paragraph(" "));
            
            PdfPTable gstTable = new PdfPTable(2);
            gstTable.setWidthPercentage(60);
            gstTable.setHorizontalAlignment(Element.ALIGN_LEFT);
            gstTable.addCell(buildBorderedCell("GST Collected (Output)", NORMAL_FONT));
            gstTable.addCell(buildBorderedCellRight(formatMoney(gstCollected), BOLD_FONT));
            gstTable.addCell(buildBorderedCell("GST Paid (Input)", NORMAL_FONT));
            gstTable.addCell(buildBorderedCellRight(formatMoney(gstPaid), BOLD_FONT));
            
            PdfPCell netLbl = buildBorderedCell("Net GST Payable", BOLD_FONT);
            netLbl.setBackgroundColor(new Color(240, 240, 240));
            PdfPCell netVal = buildBorderedCellRight(formatMoney(netGstPayable), BOLD_FONT);
            netVal.setBackgroundColor(new Color(240, 240, 240));
            gstTable.addCell(netLbl);
            gstTable.addCell(netVal);
            
            document.add(gstTable);
            document.add(new Paragraph(" "));
            document.add(new Paragraph(" "));

            // ── Compliance Status ────────────────────────────────────
            document.add(new Paragraph("Compliance Checklist", HEADER_FONT));
            document.add(new Paragraph(" "));
            
            PdfPTable statusTable = new PdfPTable(2);
            statusTable.setWidthPercentage(100);
            statusTable.setWidths(new float[]{3f, 1f});
            
            statusTable.addCell(buildHeaderCell("Requirement"));
            statusTable.addCell(buildHeaderCell("Status"));
            
            addStatusRow(statusTable, "GST Registration", profile != null && Boolean.TRUE.equals(profile.getGstRegistered()));
            addStatusRow(statusTable, "PAN Present", profile != null && profile.getPanNumber() != null && !profile.getPanNumber().isBlank());
            addStatusRow(statusTable, "TAN Present", profile != null && profile.getTanNumber() != null && !profile.getTanNumber().isBlank());
            addStatusRow(statusTable, "CIN / LLPIN Present", profile != null && profile.getCinOrLlpIn() != null && !profile.getCinOrLlpIn().isBlank());
            addStatusRow(statusTable, "MSME Registered", profile != null && profile.getMsmeNumber() != null && !profile.getMsmeNumber().isBlank());
            
            document.add(statusTable);
            
            document.close();
            return outputStream.toByteArray();
        } catch (Exception ex) {
            log.error("Failed to generate compliance PDF", ex);
            throw new RuntimeException("Failed to generate compliance PDF", ex);
        }
    }

    private void addStatusRow(PdfPTable table, String req, boolean status) {
        table.addCell(buildBorderedCell(req, NORMAL_FONT));
        PdfPCell statusCell = new PdfPCell(new Phrase(status ? "COMPLETE" : "PENDING", BOLD_FONT));
        statusCell.setHorizontalAlignment(Element.ALIGN_CENTER);
        statusCell.setVerticalAlignment(Element.ALIGN_MIDDLE);
        statusCell.setPadding(6);
        statusCell.setBackgroundColor(status ? new Color(230, 255, 230) : new Color(255, 230, 230));
        table.addCell(statusCell);
    }

    private PdfPCell buildHeaderCell(String text) {
        PdfPCell cell = new PdfPCell(new Phrase(text, TH_FONT));
        cell.setBackgroundColor(PRIMARY_COLOR);
        cell.setPadding(8);
        return cell;
    }

    private PdfPCell buildBorderlessCell(String text, Font font) {
        PdfPCell cell = new PdfPCell(new Phrase(text, font));
        cell.setBorder(Rectangle.NO_BORDER);
        cell.setPadding(4);
        return cell;
    }

    private PdfPCell buildBorderedCell(String text, Font font) {
        PdfPCell cell = new PdfPCell(new Phrase(text, font));
        cell.setPadding(6);
        cell.setBorderColor(new Color(220, 220, 220));
        return cell;
    }

    private PdfPCell buildBorderedCellRight(String text, Font font) {
        PdfPCell cell = new PdfPCell(new Phrase(text, font));
        cell.setPadding(6);
        cell.setHorizontalAlignment(Element.ALIGN_RIGHT);
        cell.setBorderColor(new Color(220, 220, 220));
        return cell;
    }

    private String formatDate(LocalDate date) {
        return date == null ? "" : date.format(DateTimeFormatter.ofPattern("dd MMM yyyy"));
    }

    private String formatMoney(BigDecimal amount) {
        if (amount == null) amount = BigDecimal.ZERO;
        return amount.setScale(2, java.math.RoundingMode.HALF_UP).toString();
    }
}
