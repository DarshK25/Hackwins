package com.moneyops.intelligence;

import com.lowagie.text.Document;
import com.lowagie.text.DocumentException;
import com.lowagie.text.Element;
import com.lowagie.text.Font;
import com.lowagie.text.FontFactory;
import com.lowagie.text.PageSize;
import com.lowagie.text.Paragraph;
import com.lowagie.text.Phrase;
import com.lowagie.text.Rectangle;
import com.lowagie.text.pdf.PdfPCell;
import com.lowagie.text.pdf.PdfPTable;
import com.lowagie.text.pdf.PdfWriter;
import com.moneyops.clients.dto.ClientDto;
import com.moneyops.clients.service.ClientService;
import com.moneyops.invoices.dto.InvoiceDto;
import com.moneyops.invoices.service.InvoiceService;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.transactions.dto.TransactionDto;
import com.moneyops.transactions.service.TransactionService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.YearMonth;
import java.time.format.DateTimeFormatter;
import java.time.format.TextStyle;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class AnalyticsReportExportService {

    private static final Color BRAND_DARK = new Color(15, 23, 42);
    private static final Color BRAND_GREEN = new Color(76, 187, 23);
    private static final Color BRAND_RED = new Color(205, 28, 24);
    private static final Color SURFACE = new Color(248, 250, 252);
    private static final Color SURFACE_ALT = new Color(241, 245, 249);
    private static final Color BORDER = new Color(226, 232, 240);
    private static final Color TEXT_PRIMARY = new Color(15, 23, 42);
    private static final Color TEXT_MUTED = new Color(100, 116, 139);
    private static final DateTimeFormatter REPORT_DATE_FORMAT =
            DateTimeFormatter.ofPattern("dd MMM yyyy, hh:mm a", Locale.US);
    private final FinanceIntelligenceService financeIntelligenceService;
    private final TransactionService transactionService;
    private final InvoiceService invoiceService;
    private final ClientService clientService;
    private final BusinessOrganizationRepository organizationRepository;

    public byte[] generateOverviewReport(String businessId, String orgId) {
        if (orgId == null || orgId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Organization context missing");
        }

        FinanceIntelligenceService.MetricsDTO metrics = financeIntelligenceService.getMetrics(businessId);
        FinanceIntelligenceService.InsightsDTO insights = financeIntelligenceService.getInsights(businessId);
        FinanceIntelligenceService.ClientRevenueSummaryDTO clientRevenueSummary =
                financeIntelligenceService.getClientRevenueSummary(businessId, 5);

        List<TransactionDto> transactions = transactionService.getAllTransactions(orgId);
        List<InvoiceDto> invoices = invoiceService.getAllInvoices(orgId);
        List<ClientDto> clients = clientService.getAllClients(orgId);

        BusinessOrganization organization = organizationRepository.findByIdAndDeletedAtIsNull(orgId).orElse(null);
        String organizationName = getOrganizationName(organization);

        List<MonthlyTrendRow> monthlyTrends = buildMonthlyTrendRows(transactions);
        List<ExpenseCategoryRow> expenseBreakdown = buildExpenseBreakdown(transactions);
        List<InvoiceDto> recentInvoices = buildRecentInvoices(invoices);

        try (ByteArrayOutputStream outputStream = new ByteArrayOutputStream()) {
            Document document = new Document(PageSize.A4, 36, 36, 40, 36);
            PdfWriter.getInstance(document, outputStream);
            document.open();

            addHero(document, organizationName, organization);
            addSectionTitle(document, "Executive Snapshot");
            document.add(buildExecutiveCards(metrics, clients.size()));

            addSectionTitle(document, "Financial Health");
            document.add(buildFinancialHealthTable(metrics, clients.size(), invoices.size()));

            addSectionTitle(document, "Six-Month Performance");
            document.add(buildMonthlyTrendTable(monthlyTrends));

            addSectionTitle(document, "Expense Breakdown");
            document.add(buildExpenseBreakdownTable(expenseBreakdown));

            addSectionTitle(document, "Client Revenue Leaders");
            document.add(buildTopClientsTable(clientRevenueSummary));

            addSectionTitle(document, "Recent Billing Activity");
            document.add(buildRecentInvoicesTable(recentInvoices));

            addSectionTitle(document, "Recommended Focus Areas");
            addInsights(document, insights);

            addFooterNote(document, organizationName);
            document.close();
            return outputStream.toByteArray();
        } catch (Exception ex) {
            throw new RuntimeException("Failed to generate analytics report PDF", ex);
        }
    }

    public String buildOverviewReportFilename(String orgId) {
        BusinessOrganization organization = organizationRepository.findByIdAndDeletedAtIsNull(orgId).orElse(null);
        String organizationName = getOrganizationName(organization);
        return sanitizeFileName(organizationName) + "-overview-report-" + LocalDate.now() + ".pdf";
    }

    private void addHero(Document document, String organizationName, BusinessOrganization organization)
            throws DocumentException {
        PdfPTable heroTable = new PdfPTable(1);
        heroTable.setWidthPercentage(100);
        heroTable.setSpacingAfter(18);

        PdfPCell heroCell = new PdfPCell();
        heroCell.setBackgroundColor(BRAND_DARK);
        heroCell.setBorder(Rectangle.NO_BORDER);
        heroCell.setPadding(18);

        Font eyebrowFont = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 10, Color.WHITE);
        Font titleFont = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 20, Color.WHITE);
        Font detailFont = FontFactory.getFont(FontFactory.HELVETICA, 10, new Color(203, 213, 225));

        Paragraph eyebrow = new Paragraph("MoneyOps Overview Report", eyebrowFont);
        eyebrow.setSpacingAfter(8);
        heroCell.addElement(eyebrow);

        Paragraph title = new Paragraph(organizationName, titleFont);
        title.setSpacingAfter(10);
        heroCell.addElement(title);

        String metadata = "Generated: " + LocalDateTime.now().format(REPORT_DATE_FORMAT);
        if (organization != null) {
            StringBuilder descriptor = new StringBuilder();
            if (organization.getIndustry() != null && !organization.getIndustry().isBlank()) {
                descriptor.append(organization.getIndustry());
            }
            if (organization.getBusinessType() != null && !organization.getBusinessType().isBlank()) {
                if (descriptor.length() > 0) {
                    descriptor.append(" | ");
                }
                descriptor.append(organization.getBusinessType());
            }
            if (descriptor.length() > 0) {
                metadata += "\nProfile: " + descriptor;
            }
        }

        Paragraph details = new Paragraph(metadata, detailFont);
        details.setLeading(14f);
        heroCell.addElement(details);

        heroTable.addCell(heroCell);
        document.add(heroTable);
    }

    private PdfPTable buildExecutiveCards(FinanceIntelligenceService.MetricsDTO metrics, int activeClients)
            throws DocumentException {
        PdfPTable cards = new PdfPTable(2);
        cards.setWidthPercentage(100);
        cards.setSpacingAfter(10);
        cards.setWidths(new float[]{1f, 1f});

        cards.addCell(buildMetricCard(
                "Total Revenue",
                formatMoney(metrics.getRevenue()),
                round(metrics.getCollectionRate()) + "% invoice collection",
                BRAND_GREEN
        ));
        cards.addCell(buildMetricCard(
                "Net Profit",
                formatMoney(metrics.getNetProfit()),
                marginText(metrics),
                safeAmount(metrics.getNetProfit()).compareTo(BigDecimal.ZERO) >= 0 ? BRAND_GREEN : BRAND_RED
        ));
        cards.addCell(buildMetricCard(
                "Expenses",
                formatMoney(metrics.getExpenses()),
                shareOfRevenue(metrics.getExpenses(), metrics.getRevenue()) + " of revenue",
                BRAND_RED
        ));
        cards.addCell(buildMetricCard(
                "Active Clients",
                String.valueOf(activeClients),
                metrics.getTotalInvoices() + " total invoices",
                BRAND_GREEN
        ));

        return cards;
    }

    private PdfPCell buildMetricCard(String label, String value, String caption, Color accent) {
        PdfPCell cell = new PdfPCell();
        cell.setBackgroundColor(SURFACE);
        cell.setBorderColor(BORDER);
        cell.setBorderWidth(1f);
        cell.setPadding(14);
        cell.setMinimumHeight(90);

        Paragraph labelText = new Paragraph(label, FontFactory.getFont(FontFactory.HELVETICA_BOLD, 10, TEXT_MUTED));
        labelText.setSpacingAfter(8);
        cell.addElement(labelText);

        Paragraph valueText = new Paragraph(value, FontFactory.getFont(FontFactory.HELVETICA_BOLD, 18, TEXT_PRIMARY));
        valueText.setSpacingAfter(6);
        cell.addElement(valueText);

        Paragraph captionText = new Paragraph(caption, FontFactory.getFont(FontFactory.HELVETICA, 9, accent));
        cell.addElement(captionText);
        return cell;
    }

    private PdfPTable buildFinancialHealthTable(
            FinanceIntelligenceService.MetricsDTO metrics,
            int activeClients,
            int totalInvoices
    ) throws DocumentException {
        PdfPTable table = buildDataTable(new float[]{2.2f, 1.1f, 1.7f});
        addHeaderRow(table, "Metric", "Value", "Commentary");

        addDataRow(table, "Total Revenue", formatMoney(metrics.getRevenue()), "Income recorded across all transactions");
        addDataRow(table, "Total Expenses", formatMoney(metrics.getExpenses()), shareOfRevenue(metrics.getExpenses(), metrics.getRevenue()) + " of revenue");
        addDataRow(table, "Net Profit", formatMoney(metrics.getNetProfit()), marginText(metrics));
        addDataRow(table, "Collection Rate", round(metrics.getCollectionRate()) + "%", metrics.getPaidCount() + " paid invoices");
        addDataRow(table, "Overdue Exposure", formatMoney(metrics.getOverdueAmount()), metrics.getOverdueCount() + " overdue invoices");
        addDataRow(table, "Active Clients", String.valueOf(activeClients), totalInvoices + " invoice relationships");
        return table;
    }

    private PdfPTable buildMonthlyTrendTable(List<MonthlyTrendRow> rows) throws DocumentException {
        PdfPTable table = buildDataTable(new float[]{1.4f, 1.3f, 1.3f, 1.3f});
        addHeaderRow(table, "Month", "Revenue", "Expenses", "Net");

        for (MonthlyTrendRow row : rows) {
            addDataRow(
                    table,
                    row.label(),
                    formatMoney(row.revenue()),
                    formatMoney(row.expenses()),
                    formatMoney(row.net())
            );
        }
        return table;
    }

    private PdfPTable buildExpenseBreakdownTable(List<ExpenseCategoryRow> rows) throws DocumentException {
        PdfPTable table = buildDataTable(new float[]{2.4f, 1.2f, 1f});
        addHeaderRow(table, "Category", "Amount", "Share");

        if (rows.isEmpty()) {
            addEmptyStateRow(table, "No categorized expenses available yet.");
            return table;
        }

        for (ExpenseCategoryRow row : rows) {
            addDataRow(table, row.category(), formatMoney(row.amount()), round(row.share()) + "%");
        }
        return table;
    }

    private PdfPTable buildTopClientsTable(FinanceIntelligenceService.ClientRevenueSummaryDTO summary)
            throws DocumentException {
        PdfPTable table = buildDataTable(new float[]{2.2f, 1.1f, 1.1f, 1.1f, 1f});
        addHeaderRow(table, "Client", "Billed", "Collected", "Outstanding", "Paid");

        if (summary.getTopClients() == null || summary.getTopClients().isEmpty()) {
            addEmptyStateRow(table, "No client revenue data available yet.");
            return table;
        }

        for (FinanceIntelligenceService.ClientRevenueItemDTO client : summary.getTopClients()) {
            addDataRow(
                    table,
                    defaultText(client.getClientName(), "Unknown Client"),
                    formatMoney(client.getBilledRevenue()),
                    formatMoney(client.getCollectedRevenue()),
                    formatMoney(client.getOutstandingRevenue()),
                    client.getPaidInvoiceCount() + "/" + client.getInvoiceCount()
            );
        }
        return table;
    }

    private PdfPTable buildRecentInvoicesTable(List<InvoiceDto> invoices) throws DocumentException {
        PdfPTable table = buildDataTable(new float[]{1.4f, 2f, 1.1f, 1.1f, 1f});
        addHeaderRow(table, "Invoice", "Client", "Due Date", "Amount", "Status");

        if (invoices.isEmpty()) {
            addEmptyStateRow(table, "No invoices available yet.");
            return table;
        }

        for (InvoiceDto invoice : invoices) {
            addDataRow(
                    table,
                    defaultText(invoice.getInvoiceNumber(), "Draft"),
                    defaultText(invoice.getClientName(), "Unknown Client"),
                    invoice.getDueDate() != null ? invoice.getDueDate().format(DateTimeFormatter.ofPattern("dd MMM yyyy")) : "N/A",
                    formatMoney(invoice.getTotalAmount()),
                    defaultText(invoice.getStatus(), "UNKNOWN")
            );
        }
        return table;
    }

    private void addInsights(Document document, FinanceIntelligenceService.InsightsDTO insights)
            throws DocumentException {
        if (insights.getInsights() == null || insights.getInsights().isEmpty()) {
            Paragraph empty = new Paragraph(
                    "No automated insights are available yet. Add more transactions and invoice history to deepen the report.",
                    FontFactory.getFont(FontFactory.HELVETICA, 10, TEXT_MUTED)
            );
            empty.setSpacingAfter(12);
            document.add(empty);
            return;
        }

        for (FinanceIntelligenceService.InsightItemDTO insight : insights.getInsights()) {
            PdfPTable insightCard = new PdfPTable(1);
            insightCard.setWidthPercentage(100);
            insightCard.setSpacingAfter(8);

            PdfPCell cell = new PdfPCell();
            cell.setBackgroundColor(SURFACE_ALT);
            cell.setBorderColor(BORDER);
            cell.setPadding(12);

            Paragraph title = new Paragraph(
                    defaultText(insight.getTitle(), "Insight"),
                    FontFactory.getFont(FontFactory.HELVETICA_BOLD, 11, TEXT_PRIMARY)
            );
            title.setSpacingAfter(4);
            cell.addElement(title);

            String meta = defaultText(insight.getType(), "GENERAL") + " | Severity: " +
                    defaultText(insight.getSeverity(), "NORMAL");
            Paragraph metaText = new Paragraph(meta, FontFactory.getFont(FontFactory.HELVETICA, 9, BRAND_GREEN));
            metaText.setSpacingAfter(6);
            cell.addElement(metaText);

            Paragraph description = new Paragraph(
                    defaultText(insight.getDescription(), "No description available."),
                    FontFactory.getFont(FontFactory.HELVETICA, 10, TEXT_MUTED)
            );
            cell.addElement(description);

            insightCard.addCell(cell);
            document.add(insightCard);
        }
    }

    private void addFooterNote(Document document, String organizationName) throws DocumentException {
        Paragraph spacer = new Paragraph(" ");
        spacer.setSpacingBefore(6);
        document.add(spacer);

        Paragraph note = new Paragraph(
                "This report was generated automatically by MoneyOps for " + organizationName +
                        ". Use it as an executive snapshot and pair it with the live dashboard for drill-down analysis.",
                FontFactory.getFont(FontFactory.HELVETICA_OBLIQUE, 9, TEXT_MUTED)
        );
        note.setAlignment(Element.ALIGN_CENTER);
        document.add(note);
    }

    private void addSectionTitle(Document document, String title) throws DocumentException {
        Paragraph paragraph = new Paragraph(title, FontFactory.getFont(FontFactory.HELVETICA_BOLD, 13, TEXT_PRIMARY));
        paragraph.setSpacingBefore(6);
        paragraph.setSpacingAfter(8);
        document.add(paragraph);
    }

    private PdfPTable buildDataTable(float[] widths) throws DocumentException {
        PdfPTable table = new PdfPTable(widths.length);
        table.setWidthPercentage(100);
        table.setSpacingAfter(12);
        table.setWidths(widths);
        return table;
    }

    private void addHeaderRow(PdfPTable table, String... values) {
        for (String value : values) {
            PdfPCell cell = new PdfPCell(new Phrase(value, FontFactory.getFont(FontFactory.HELVETICA_BOLD, 10, Color.WHITE)));
            cell.setBackgroundColor(BRAND_DARK);
            cell.setBorderColor(BRAND_DARK);
            cell.setPadding(8);
            table.addCell(cell);
        }
    }

    private void addDataRow(PdfPTable table, String... values) {
        for (String value : values) {
            PdfPCell cell = new PdfPCell(new Phrase(value, FontFactory.getFont(FontFactory.HELVETICA, 9, TEXT_PRIMARY)));
            cell.setBackgroundColor(Color.WHITE);
            cell.setBorderColor(BORDER);
            cell.setPadding(8);
            table.addCell(cell);
        }
    }

    private void addEmptyStateRow(PdfPTable table, String text) {
        PdfPCell cell = new PdfPCell(new Phrase(text, FontFactory.getFont(FontFactory.HELVETICA_OBLIQUE, 9, TEXT_MUTED)));
        cell.setColspan(table.getNumberOfColumns());
        cell.setPadding(10);
        cell.setBorderColor(BORDER);
        cell.setHorizontalAlignment(Element.ALIGN_CENTER);
        cell.setBackgroundColor(Color.WHITE);
        table.addCell(cell);
    }

    private List<MonthlyTrendRow> buildMonthlyTrendRows(List<TransactionDto> transactions) {
        YearMonth currentMonth = YearMonth.now();
        YearMonth startMonth = currentMonth.minusMonths(5);
        Map<YearMonth, MonthlyTotals> totalsByMonth = new LinkedHashMap<>();

        for (int i = 0; i < 6; i++) {
            YearMonth month = startMonth.plusMonths(i);
            totalsByMonth.put(month, new MonthlyTotals());
        }

        for (TransactionDto transaction : transactions) {
            if (transaction.getTransactionDate() == null) {
                continue;
            }

            YearMonth month = YearMonth.from(transaction.getTransactionDate());
            MonthlyTotals totals = totalsByMonth.get(month);
            if (totals == null) {
                continue;
            }

            BigDecimal amount = safeAmount(transaction.getAmount());
            if ("INCOME".equalsIgnoreCase(transaction.getType())) {
                totals.revenue = totals.revenue.add(amount);
            } else if ("EXPENSE".equalsIgnoreCase(transaction.getType())) {
                totals.expenses = totals.expenses.add(amount);
            }
        }

        List<MonthlyTrendRow> rows = new ArrayList<>();
        for (Map.Entry<YearMonth, MonthlyTotals> entry : totalsByMonth.entrySet()) {
            YearMonth month = entry.getKey();
            MonthlyTotals totals = entry.getValue();
            String label = month.getMonth().getDisplayName(TextStyle.SHORT, Locale.US) + " " + month.getYear();
            rows.add(new MonthlyTrendRow(label, totals.revenue, totals.expenses));
        }
        return rows;
    }

    private List<ExpenseCategoryRow> buildExpenseBreakdown(List<TransactionDto> transactions) {
        Map<String, BigDecimal> expensesByCategory = new HashMap<>();
        BigDecimal totalExpenses = BigDecimal.ZERO;

        for (TransactionDto transaction : transactions) {
            if (!"EXPENSE".equalsIgnoreCase(transaction.getType())) {
                continue;
            }

            BigDecimal amount = safeAmount(transaction.getAmount());
            String category = defaultText(transaction.getCategory(), "Uncategorized");
            expensesByCategory.merge(category, amount, BigDecimal::add);
            totalExpenses = totalExpenses.add(amount);
        }

        BigDecimal denominator = totalExpenses;
        return expensesByCategory.entrySet().stream()
                .sorted(Map.Entry.<String, BigDecimal>comparingByValue().reversed())
                .limit(8)
                .map(entry -> new ExpenseCategoryRow(
                        entry.getKey(),
                        entry.getValue(),
                        toPercent(entry.getValue(), denominator)
                ))
                .collect(Collectors.toList());
    }

    private List<InvoiceDto> buildRecentInvoices(List<InvoiceDto> invoices) {
        return invoices.stream()
                .sorted(
                        Comparator.comparing(
                                InvoiceDto::getIssueDate,
                                Comparator.nullsLast(Comparator.reverseOrder())
                        ).thenComparing(
                                InvoiceDto::getDueDate,
                                Comparator.nullsLast(Comparator.reverseOrder())
                        )
                )
                .limit(6)
                .collect(Collectors.toList());
    }

    private String getOrganizationName(BusinessOrganization organization) {
        if (organization == null) {
            return "MoneyOps Workspace";
        }
        if (organization.getTradingName() != null && !organization.getTradingName().isBlank()) {
            return organization.getTradingName();
        }
        if (organization.getLegalName() != null && !organization.getLegalName().isBlank()) {
            return organization.getLegalName();
        }
        return "MoneyOps Workspace";
    }

    private BigDecimal safeAmount(BigDecimal amount) {
        return amount == null ? BigDecimal.ZERO : amount;
    }

    private String formatMoney(BigDecimal amount) {
        return "INR " + new java.text.DecimalFormat("#,##0.00").format(safeAmount(amount));
    }

    private String marginText(FinanceIntelligenceService.MetricsDTO metrics) {
        if (safeAmount(metrics.getRevenue()).compareTo(BigDecimal.ZERO) <= 0) {
            return "No revenue recorded yet";
        }

        BigDecimal margin = safeAmount(metrics.getNetProfit())
                .multiply(BigDecimal.valueOf(100))
                .divide(safeAmount(metrics.getRevenue()), 1, java.math.RoundingMode.HALF_UP);
        return margin + "% profit margin";
    }

    private String shareOfRevenue(BigDecimal part, BigDecimal whole) {
        if (safeAmount(whole).compareTo(BigDecimal.ZERO) <= 0) {
            return "0%";
        }

        BigDecimal percentage = safeAmount(part)
                .multiply(BigDecimal.valueOf(100))
                .divide(safeAmount(whole), 1, java.math.RoundingMode.HALF_UP);
        return percentage + "%";
    }

    private double toPercent(BigDecimal numerator, BigDecimal denominator) {
        if (safeAmount(denominator).compareTo(BigDecimal.ZERO) <= 0) {
            return 0;
        }

        return safeAmount(numerator)
                .multiply(BigDecimal.valueOf(100))
                .divide(safeAmount(denominator), 1, java.math.RoundingMode.HALF_UP)
                .doubleValue();
    }

    private String round(double value) {
        return String.format(Locale.US, "%.1f", value);
    }

    private String defaultText(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private String sanitizeFileName(String value) {
        String base = defaultText(value, "moneyops").toLowerCase(Locale.US);
        String sanitized = base.replaceAll("[^a-z0-9]+", "-").replaceAll("(^-|-$)", "");
        return sanitized.isBlank() ? "moneyops" : sanitized;
    }

    private static final class MonthlyTotals {
        private BigDecimal revenue = BigDecimal.ZERO;
        private BigDecimal expenses = BigDecimal.ZERO;
    }

    private record MonthlyTrendRow(String label, BigDecimal revenue, BigDecimal expenses) {
        private BigDecimal net() {
            return revenue.subtract(expenses);
        }
    }

    private record ExpenseCategoryRow(String category, BigDecimal amount, double share) {
    }
}
