package com.moneyops.transactions.service;

import com.lowagie.text.*;
import com.lowagie.text.pdf.*;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
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
import java.util.Map;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class LedgerPdfService {

    private final TransactionService transactionService;
    private final BusinessOrganizationRepository orgRepository;

    private static final Font TITLE_FONT = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 20, Color.BLACK);
    private static final Font HEADER_FONT = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 12, Color.DARK_GRAY);
    private static final Font NORMAL_FONT = FontFactory.getFont(FontFactory.HELVETICA, 10, Color.BLACK);
    private static final Font BOLD_FONT = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 10, Color.BLACK);
    private static final Font TH_FONT = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 10, Color.WHITE);
    private static final Color PRIMARY_COLOR = new Color(26, 26, 26);
    private static final Color INCOME_COLOR = new Color(76, 187, 23); // Green
    private static final Color EXPENSE_COLOR = new Color(205, 28, 24); // Red

    public byte[] generateLedgerPdf(String orgId, LocalDate dateFrom, LocalDate dateTo) {
        BusinessOrganization org = orgRepository.findByIdAndDeletedAtIsNull(orgId).orElse(null);
        List<TransactionDto> transactions = transactionService.getTransactionsByDateRange(orgId, dateFrom, dateTo);

        // Sort chronologically
        transactions.sort((a, b) -> a.getTransactionDate().compareTo(b.getTransactionDate()));

        try (ByteArrayOutputStream outputStream = new ByteArrayOutputStream()) {
            Document document = new Document(PageSize.A4, 40, 40, 40, 40);
            PdfWriter.getInstance(document, outputStream);
            document.open();

            // ── Header ───────────────────────────────────────────────
            String orgName = org != null && org.getLegalName() != null ? org.getLegalName() : "MoneyOps";
            document.add(new Paragraph(orgName, TITLE_FONT));
            document.add(new Paragraph("General Ledger Report", HEADER_FONT));
            document.add(new Paragraph("Period: " + formatDate(dateFrom) + " to " + formatDate(dateTo), NORMAL_FONT));
            document.add(new Paragraph(" "));
            document.add(new Paragraph(" "));

            // ── Summary Totals ───────────────────────────────────────
            BigDecimal totalIncome = BigDecimal.ZERO;
            BigDecimal totalExpense = BigDecimal.ZERO;
            for (TransactionDto t : transactions) {
                if ("INCOME".equalsIgnoreCase(t.getType())) {
                    totalIncome = totalIncome.add(t.getAmount());
                } else if ("EXPENSE".equalsIgnoreCase(t.getType())) {
                    totalExpense = totalExpense.add(t.getAmount());
                }
            }
            BigDecimal netMovement = totalIncome.subtract(totalExpense);

            PdfPTable summaryTable = new PdfPTable(3);
            summaryTable.setWidthPercentage(100);
            summaryTable.addCell(buildSummaryBox("Total Income", formatMoney(totalIncome), INCOME_COLOR));
            summaryTable.addCell(buildSummaryBox("Total Expense", formatMoney(totalExpense), EXPENSE_COLOR));
            summaryTable.addCell(buildSummaryBox("Net Movement", formatMoney(netMovement), netMovement.compareTo(BigDecimal.ZERO) >= 0 ? INCOME_COLOR : EXPENSE_COLOR));
            document.add(summaryTable);
            document.add(new Paragraph(" "));
            document.add(new Paragraph(" "));

            // ── Client-wise Summary ──────────────────────────────────
            Map<String, BigDecimal> clientBalances = transactions.stream()
                    .filter(t -> t.getClientId() != null && !t.getClientId().trim().isEmpty())
                    .collect(Collectors.groupingBy(
                            TransactionDto::getClientId,
                            Collectors.reducing(BigDecimal.ZERO,
                                    t -> "INCOME".equalsIgnoreCase(t.getType()) ? t.getAmount() : t.getAmount().negate(),
                                    BigDecimal::add)
                    ));

            if (!clientBalances.isEmpty()) {
                document.add(new Paragraph("Client/Vendor Summary", HEADER_FONT));
                document.add(new Paragraph(" "));
                PdfPTable clientTable = new PdfPTable(2);
                clientTable.setWidthPercentage(50);
                clientTable.setHorizontalAlignment(Element.ALIGN_LEFT);
                clientTable.addCell(buildHeaderCell("Client / Vendor"));
                clientTable.addCell(buildHeaderCell("Net Amount"));
                
                for (Map.Entry<String, BigDecimal> entry : clientBalances.entrySet()) {
                    clientTable.addCell(buildBodyCell(entry.getKey(), Element.ALIGN_LEFT));
                    clientTable.addCell(buildBodyCell(formatMoney(entry.getValue()), Element.ALIGN_RIGHT));
                }
                document.add(clientTable);
                document.add(new Paragraph(" "));
                document.add(new Paragraph(" "));
            }

            // ── Transactions Ledger ──────────────────────────────────
            document.add(new Paragraph("Transaction Details", HEADER_FONT));
            document.add(new Paragraph(" "));

            PdfPTable table = new PdfPTable(6);
            table.setWidthPercentage(100);
            table.setWidths(new float[]{1.5f, 2f, 3f, 1.5f, 1.5f, 2f});
            
            table.addCell(buildHeaderCell("Date"));
            table.addCell(buildHeaderCell("Category"));
            table.addCell(buildHeaderCell("Description"));
            table.addCell(buildHeaderCell("Income"));
            table.addCell(buildHeaderCell("Expense"));
            table.addCell(buildHeaderCell("Running Bal"));

            BigDecimal runningBalance = BigDecimal.ZERO;
            
            for (TransactionDto t : transactions) {
                boolean isIncome = "INCOME".equalsIgnoreCase(t.getType());
                if (isIncome) {
                    runningBalance = runningBalance.add(t.getAmount());
                } else {
                    runningBalance = runningBalance.subtract(t.getAmount());
                }

                table.addCell(buildBodyCell(formatDate(t.getTransactionDate()), Element.ALIGN_LEFT));
                table.addCell(buildBodyCell(t.getCategory() != null ? t.getCategory() : "Uncategorized", Element.ALIGN_LEFT));
                table.addCell(buildBodyCell(t.getDescription() != null ? t.getDescription() : "", Element.ALIGN_LEFT));
                
                if (isIncome) {
                    table.addCell(buildBodyCell(formatMoney(t.getAmount()), Element.ALIGN_RIGHT));
                    table.addCell(buildBodyCell("", Element.ALIGN_RIGHT));
                } else {
                    table.addCell(buildBodyCell("", Element.ALIGN_RIGHT));
                    table.addCell(buildBodyCell(formatMoney(t.getAmount()), Element.ALIGN_RIGHT));
                }
                
                table.addCell(buildBodyCell(formatMoney(runningBalance), Element.ALIGN_RIGHT));
            }

            if (transactions.isEmpty()) {
                PdfPCell emptyCell = new PdfPCell(new Phrase("No transactions found for this period.", NORMAL_FONT));
                emptyCell.setColspan(6);
                emptyCell.setHorizontalAlignment(Element.ALIGN_CENTER);
                emptyCell.setPadding(10);
                table.addCell(emptyCell);
            }

            document.add(table);
            document.close();
            return outputStream.toByteArray();

        } catch (DocumentException | java.io.IOException ex) {
            log.error("Failed to generate ledger PDF", ex);
            throw new RuntimeException("Failed to generate ledger PDF", ex);
        }
    }

    private PdfPCell buildSummaryBox(String label, String value, Color valueColor) {
        PdfPCell cell = new PdfPCell();
        cell.setBorder(Rectangle.BOX);
        cell.setBorderColor(new Color(220, 220, 220));
        cell.setPadding(10);
        cell.addElement(new Paragraph(label, NORMAL_FONT));
        cell.addElement(new Paragraph(value, FontFactory.getFont(FontFactory.HELVETICA_BOLD, 14, valueColor)));
        return cell;
    }

    private PdfPCell buildHeaderCell(String text) {
        PdfPCell cell = new PdfPCell(new Phrase(text, TH_FONT));
        cell.setBackgroundColor(PRIMARY_COLOR);
        cell.setPadding(8);
        return cell;
    }

    private PdfPCell buildBodyCell(String text, int alignment) {
        PdfPCell cell = new PdfPCell(new Phrase(text, NORMAL_FONT));
        cell.setHorizontalAlignment(alignment);
        cell.setVerticalAlignment(Element.ALIGN_MIDDLE);
        cell.setPadding(6);
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
