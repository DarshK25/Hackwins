package com.moneyops.overview.service;

import com.lowagie.text.Document;
import com.lowagie.text.DocumentException;
import com.lowagie.text.Element;
import com.lowagie.text.FontFactory;
import com.lowagie.text.PageSize;
import com.lowagie.text.Paragraph;
import com.lowagie.text.Phrase;
import com.lowagie.text.Rectangle;
import com.lowagie.text.pdf.PdfPCell;
import com.lowagie.text.pdf.PdfPTable;
import com.lowagie.text.pdf.PdfWriter;
import com.moneyops.clients.entity.Client;
import com.moneyops.clients.repository.ClientRepository;
import com.moneyops.compliance.ComplianceService;
import com.moneyops.compliance.dto.ComplianceSummaryDTO;
import com.moneyops.invoices.entity.Invoice;
import com.moneyops.invoices.entity.InvoiceStatus;
import com.moneyops.invoices.repository.InvoiceRepository;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.entity.RegulatoryProfile;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.organizations.repository.RegulatoryProfileRepository;
import com.moneyops.overview.dto.OverviewMetricsDTO;
import com.moneyops.shared.exceptions.UnauthorizedException;
import com.moneyops.transactions.entity.Transaction;
import com.moneyops.transactions.entity.TransactionType;
import com.moneyops.transactions.repository.TransactionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.YearMonth;
import java.time.format.DateTimeFormatter;
import java.time.format.TextStyle;
import java.time.temporal.TemporalAdjusters;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class OverviewReportService {

    private static final Color BRAND_DARK = new Color(15, 23, 42);
    private static final Color BRAND_GREEN = new Color(76, 187, 23);
    private static final Color BRAND_RED = new Color(205, 28, 24);
    private static final Color BRAND_AMBER = new Color(255, 179, 0);
    private static final Color BORDER = new Color(226, 232, 240);
    private static final Color SURFACE = new Color(248, 250, 252);
    private static final Color TEXT_PRIMARY = new Color(15, 23, 42);
    private static final Color TEXT_MUTED = new Color(100, 116, 139);
    private static final DateTimeFormatter DATE_FORMAT = DateTimeFormatter.ofPattern("dd MMM yyyy", Locale.US);

    private final TransactionRepository transactionRepository;
    private final InvoiceRepository invoiceRepository;
    private final ClientRepository clientRepository;
    private final BusinessOrganizationRepository organizationRepository;
    private final RegulatoryProfileRepository regulatoryProfileRepository;
    private final ComplianceService complianceService;

    public OverviewMetricsDTO getMetrics(String orgId, String period) {
        if (orgId == null || orgId.isBlank()) {
            throw new UnauthorizedException("Missing organization context");
        }

        PeriodRange range = resolvePeriod(period);
        List<Transaction> allTransactions = transactionRepository.findAllByOrgIdAndDeletedAtIsNull(orgId);
        List<Invoice> allInvoices = invoiceRepository.findAllByOrgIdAndDeletedAtIsNull(orgId);
        List<Client> allClients = clientRepository.findAllByOrgIdAndDeletedAtIsNull(orgId);
        BusinessOrganization organization = organizationRepository.findByIdAndDeletedAtIsNull(orgId).orElse(null);
        RegulatoryProfile regulatoryProfile = regulatoryProfileRepository.findByOrgIdAndDeletedAtIsNull(orgId).orElse(null);

        Map<String, Client> clientsById = allClients.stream()
                .collect(Collectors.toMap(Client::getId, client -> client, (left, right) -> left));
        Map<String, Invoice> invoicesById = allInvoices.stream()
                .collect(Collectors.toMap(Invoice::getId, invoice -> invoice, (left, right) -> left));

        List<Transaction> periodTransactions = allTransactions.stream()
                .filter(transaction -> isWithinPeriod(transaction.getTransactionDate(), range.startDate(), range.endDate()))
                .collect(Collectors.toList());

        List<Invoice> periodInvoices = allInvoices.stream()
                .filter(invoice -> isWithinPeriod(resolveInvoiceDate(invoice), range.startDate(), range.endDate()))
                .collect(Collectors.toList());

        OverviewMetricsDTO dto = new OverviewMetricsDTO();
        dto.setOrgId(orgId);
        dto.setPeriod(range.period());
        dto.setReportTitle(buildReportTitle(range));
        dto.setPeriodStart(range.startDate());
        dto.setPeriodEnd(range.endDate());
        dto.setOrganization(buildOrganizationSummary(organization, regulatoryProfile));

        BigDecimal totalRevenue = sumTransactionsByType(periodTransactions, TransactionType.INCOME);
        BigDecimal totalExpenses = sumTransactionsByType(periodTransactions, TransactionType.EXPENSE);
        dto.setTotalRevenue(totalRevenue);
        dto.setTotalExpenses(totalExpenses);
        dto.setNetProfitLoss(totalRevenue.subtract(totalExpenses));

        InvoiceSnapshot invoiceSnapshot = buildInvoiceSnapshot(allInvoices);
        dto.setOutstandingInvoicesCount(invoiceSnapshot.outstandingCount());
        dto.setOutstandingInvoicesAmount(invoiceSnapshot.outstandingAmount());
        dto.setOverdueInvoicesCount(invoiceSnapshot.overdueCount());
        dto.setOverdueInvoicesAmount(invoiceSnapshot.overdueAmount());

        long newClients = allClients.stream()
                .filter(client -> client.getCreatedAt() != null)
                .filter(client -> isWithinPeriod(client.getCreatedAt().toLocalDate(), range.startDate(), range.endDate()))
                .count();
        dto.setNewClients(newClients);

        dto.setTopClients(buildTopClients(periodTransactions, clientsById, invoicesById));
        dto.setInvoiceStatusBreakdown(buildInvoiceStatusBreakdown(periodInvoices));
        dto.setMonthComparisons(buildMonthlyComparisons(periodTransactions, range));
        dto.setComplianceSummary(complianceService.getComplianceSummary(orgId));
        return dto;
    }

    public byte[] generateOverviewPdf(String orgId, String period) {
        OverviewMetricsDTO metrics = getMetrics(orgId, period);

        try (ByteArrayOutputStream outputStream = new ByteArrayOutputStream()) {
            Document document = new Document(PageSize.A4, 36, 36, 40, 36);
            PdfWriter.getInstance(document, outputStream);
            document.open();

            addHero(document, metrics);
            addSectionTitle(document, "Key Metrics");
            document.add(buildMetricCards(metrics));

            addSectionTitle(document, "Operations Summary");
            document.add(buildOperationsTable(metrics));

            addSectionTitle(document, "Top 5 Clients by Revenue");
            document.add(buildTopClientsTable(metrics.getTopClients()));

            addSectionTitle(document, "Invoice Status Breakdown");
            document.add(buildInvoiceBreakdownTable(metrics.getInvoiceStatusBreakdown()));

            if (!"MONTHLY".equals(metrics.getPeriod())) {
                addSectionTitle(document, "Month-by-Month Comparison");
                document.add(buildMonthlyComparisonTable(metrics.getMonthComparisons()));
            }

            addSectionTitle(document, "Compliance Status Summary");
            document.add(buildComplianceTable(metrics.getComplianceSummary()));

            addFooter(document, metrics);
            document.close();
            return outputStream.toByteArray();
        } catch (Exception exception) {
            throw new RuntimeException("Failed to generate overview report PDF", exception);
        }
    }

    public String buildFilename(String orgId, String period) {
        BusinessOrganization organization = organizationRepository.findByIdAndDeletedAtIsNull(orgId).orElse(null);
        String organizationName = getOrganizationName(organization);
        String normalizedPeriod = normalizePeriod(period).toLowerCase(Locale.ROOT);
        String safeName = organizationName.toLowerCase(Locale.ROOT)
                .replaceAll("[^a-z0-9]+", "-")
                .replaceAll("(^-|-$)", "");
        if (safeName.isBlank()) {
            safeName = "moneyops";
        }
        return safeName + "-overview-" + normalizedPeriod + "-" + LocalDate.now() + ".pdf";
    }

    private OverviewMetricsDTO.OrganizationSummary buildOrganizationSummary(
            BusinessOrganization organization,
            RegulatoryProfile regulatoryProfile
    ) {
        OverviewMetricsDTO.OrganizationSummary summary = new OverviewMetricsDTO.OrganizationSummary();
        if (organization != null) {
            summary.setLegalName(organization.getLegalName());
            summary.setTradingName(organization.getTradingName());
            summary.setBusinessType(organization.getBusinessType());
            summary.setIndustry(organization.getIndustry());
            summary.setPrimaryEmail(organization.getPrimaryEmail());
            summary.setPrimaryPhone(organization.getPrimaryPhone());
            summary.setWebsite(organization.getWebsite());
            summary.setRegisteredAddress(organization.getRegisteredAddress());
            summary.setCurrency(organization.getCurrency());
        }
        if (regulatoryProfile != null) {
            summary.setGstNumber(regulatoryProfile.getGstNumber());
            summary.setPanNumber(regulatoryProfile.getPanNumber());
        } else if (organization != null) {
            summary.setGstNumber(organization.getGstin());
            summary.setPanNumber(organization.getPanNumber());
        }
        return summary;
    }

    private BigDecimal sumTransactionsByType(List<Transaction> transactions, TransactionType type) {
        return transactions.stream()
                .filter(transaction -> transaction.getType() == type)
                .map(Transaction::getAmount)
                .map(this::safeAmount)
                .map(BigDecimal::abs)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    private InvoiceSnapshot buildInvoiceSnapshot(List<Invoice> invoices) {
        LocalDate today = LocalDate.now();
        long outstandingCount = 0;
        BigDecimal outstandingAmount = BigDecimal.ZERO;
        long overdueCount = 0;
        BigDecimal overdueAmount = BigDecimal.ZERO;

        for (Invoice invoice : invoices) {
            BigDecimal balanceDue = resolveBalanceDue(invoice);
            boolean isOutstanding = balanceDue.compareTo(BigDecimal.ZERO) > 0 && invoice.getStatus() != InvoiceStatus.PAID;
            boolean isOverdue = invoice.getStatus() == InvoiceStatus.OVERDUE
                    || (invoice.getDueDate() != null
                    && invoice.getDueDate().isBefore(today)
                    && invoice.getStatus() != InvoiceStatus.PAID
                    && invoice.getStatus() != InvoiceStatus.DRAFT);

            if (isOutstanding) {
                outstandingCount++;
                outstandingAmount = outstandingAmount.add(balanceDue);
            }
            if (isOverdue) {
                overdueCount++;
                overdueAmount = overdueAmount.add(balanceDue);
            }
        }

        return new InvoiceSnapshot(outstandingCount, outstandingAmount, overdueCount, overdueAmount);
    }

    private List<OverviewMetricsDTO.TopClientDTO> buildTopClients(
            List<Transaction> periodTransactions,
            Map<String, Client> clientsById,
            Map<String, Invoice> invoicesById
    ) {
        Map<String, TopClientAccumulator> totalsByClient = new HashMap<>();

        for (Transaction transaction : periodTransactions) {
            if (transaction.getType() != TransactionType.INCOME) {
                continue;
            }

            ClientResolution resolution = resolveClient(transaction, clientsById, invoicesById);
            String key = resolution.clientId() != null ? resolution.clientId() : resolution.clientName();
            if (key == null || key.isBlank()) {
                key = "UNASSIGNED";
            }

            TopClientAccumulator accumulator = totalsByClient.computeIfAbsent(
                    key,
                    ignored -> new TopClientAccumulator(resolution.clientId(), resolution.clientName())
            );
            accumulator.revenue = accumulator.revenue.add(safeAmount(transaction.getAmount()).abs());
            accumulator.transactionCount++;
        }

        return totalsByClient.values().stream()
                .sorted(Comparator.comparing(TopClientAccumulator::revenue).reversed())
                .limit(5)
                .map(accumulator -> {
                    OverviewMetricsDTO.TopClientDTO dto = new OverviewMetricsDTO.TopClientDTO();
                    dto.setClientId(accumulator.clientId);
                    dto.setClientName(accumulator.clientName);
                    dto.setRevenue(accumulator.revenue);
                    dto.setTransactionCount(accumulator.transactionCount);
                    return dto;
                })
                .collect(Collectors.toList());
    }

    private OverviewMetricsDTO.InvoiceStatusBreakdown buildInvoiceStatusBreakdown(List<Invoice> invoices) {
        EnumMap<InvoiceStatus, Long> counts = new EnumMap<>(InvoiceStatus.class);
        for (InvoiceStatus status : InvoiceStatus.values()) {
            counts.put(status, 0L);
        }

        for (Invoice invoice : invoices) {
            InvoiceStatus status = invoice.getStatus() != null ? invoice.getStatus() : InvoiceStatus.DRAFT;
            counts.put(status, counts.getOrDefault(status, 0L) + 1);
        }

        OverviewMetricsDTO.InvoiceStatusBreakdown dto = new OverviewMetricsDTO.InvoiceStatusBreakdown();
        dto.setDraft(counts.getOrDefault(InvoiceStatus.DRAFT, 0L));
        dto.setSent(counts.getOrDefault(InvoiceStatus.SENT, 0L));
        dto.setPaid(counts.getOrDefault(InvoiceStatus.PAID, 0L));
        dto.setOverdue(counts.getOrDefault(InvoiceStatus.OVERDUE, 0L));
        return dto;
    }

    private List<OverviewMetricsDTO.MonthlyComparisonDTO> buildMonthlyComparisons(
            List<Transaction> transactions,
            PeriodRange range
    ) {
        Map<YearMonth, MonthlyBucket> buckets = new LinkedHashMap<>();
        YearMonth current = YearMonth.from(range.startDate());
        YearMonth end = YearMonth.from(range.endDate());

        while (!current.isAfter(end)) {
            buckets.put(current, new MonthlyBucket());
            current = current.plusMonths(1);
        }

        for (Transaction transaction : transactions) {
            if (transaction.getTransactionDate() == null) {
                continue;
            }
            YearMonth bucketKey = YearMonth.from(transaction.getTransactionDate());
            MonthlyBucket bucket = buckets.get(bucketKey);
            if (bucket == null) {
                continue;
            }
            BigDecimal amount = safeAmount(transaction.getAmount()).abs();
            if (transaction.getType() == TransactionType.INCOME) {
                bucket.revenue = bucket.revenue.add(amount);
            } else if (transaction.getType() == TransactionType.EXPENSE) {
                bucket.expenses = bucket.expenses.add(amount);
            }
        }

        return buckets.entrySet().stream()
                .map(entry -> {
                    OverviewMetricsDTO.MonthlyComparisonDTO dto = new OverviewMetricsDTO.MonthlyComparisonDTO();
                    dto.setLabel(entry.getKey().getMonth().getDisplayName(TextStyle.SHORT, Locale.US) + " " + entry.getKey().getYear());
                    dto.setRevenue(entry.getValue().revenue);
                    dto.setExpenses(entry.getValue().expenses);
                    dto.setNetProfitLoss(entry.getValue().revenue.subtract(entry.getValue().expenses));
                    return dto;
                })
                .collect(Collectors.toList());
    }

    private ClientResolution resolveClient(
            Transaction transaction,
            Map<String, Client> clientsById,
            Map<String, Invoice> invoicesById
    ) {
        String clientId = transaction.getClientId();
        String clientName = null;

        if (clientId != null && !clientId.isBlank()) {
            Client client = clientsById.get(clientId);
            clientName = client != null ? client.getName() : null;
        }

        if ((clientId == null || clientId.isBlank()) && transaction.getInvoiceId() != null) {
            Invoice invoice = invoicesById.get(transaction.getInvoiceId());
            if (invoice != null) {
                clientId = invoice.getClientId();
                clientName = invoice.getClientName();
                if ((clientName == null || clientName.isBlank()) && clientId != null) {
                    Client client = clientsById.get(clientId);
                    clientName = client != null ? client.getName() : null;
                }
            }
        }

        if ((clientName == null || clientName.isBlank()) && clientId != null) {
            Client client = clientsById.get(clientId);
            clientName = client != null ? client.getName() : null;
        }

        if (clientName == null || clientName.isBlank()) {
            clientName = "Unassigned Client";
        }

        return new ClientResolution(clientId, clientName);
    }

    private LocalDate resolveInvoiceDate(Invoice invoice) {
        if (invoice.getIssueDate() != null) {
            return invoice.getIssueDate();
        }
        if (invoice.getCreatedAt() != null) {
            return invoice.getCreatedAt().toLocalDate();
        }
        return null;
    }

    private BigDecimal resolveBalanceDue(Invoice invoice) {
        if (invoice.getBalanceDue() != null) {
            return safeAmount(invoice.getBalanceDue()).max(BigDecimal.ZERO);
        }
        return safeAmount(invoice.getTotalAmount()).subtract(safeAmount(invoice.getAmountPaid())).max(BigDecimal.ZERO);
    }

    private boolean isWithinPeriod(LocalDate value, LocalDate startDate, LocalDate endDate) {
        return value != null && !value.isBefore(startDate) && !value.isAfter(endDate);
    }

    private PeriodRange resolvePeriod(String requestedPeriod) {
        String period = normalizePeriod(requestedPeriod);
        LocalDate today = LocalDate.now();

        return switch (period) {
            case "QUARTERLY" -> {
                int quarterStartMonth = ((today.getMonthValue() - 1) / 3) * 3 + 1;
                LocalDate start = LocalDate.of(today.getYear(), quarterStartMonth, 1);
                LocalDate end = start.plusMonths(2).with(TemporalAdjusters.lastDayOfMonth());
                yield new PeriodRange(period, start, end);
            }
            case "YEARLY" -> {
                LocalDate start = LocalDate.of(today.getYear(), 1, 1);
                LocalDate end = LocalDate.of(today.getYear(), 12, 31);
                yield new PeriodRange(period, start, end);
            }
            default -> {
                LocalDate start = today.withDayOfMonth(1);
                LocalDate end = today.with(TemporalAdjusters.lastDayOfMonth());
                yield new PeriodRange("MONTHLY", start, end);
            }
        };
    }

    private String normalizePeriod(String value) {
        if (value == null || value.isBlank()) {
            return "MONTHLY";
        }
        return switch (value.trim().toUpperCase(Locale.ROOT)) {
            case "MONTHLY", "QUARTERLY", "YEARLY" -> value.trim().toUpperCase(Locale.ROOT);
            default -> "MONTHLY";
        };
    }

    private String buildReportTitle(PeriodRange range) {
        return switch (range.period()) {
            case "QUARTERLY" -> "Quarterly Report — Q" + (((range.startDate().getMonthValue() - 1) / 3) + 1) + " " + range.startDate().getYear();
            case "YEARLY" -> "Yearly Report — " + range.startDate().getYear();
            default -> "Monthly Report — " + range.startDate().getMonth().getDisplayName(TextStyle.FULL, Locale.US) + " " + range.startDate().getYear();
        };
    }

    private void addHero(Document document, OverviewMetricsDTO metrics) throws DocumentException {
        PdfPTable table = new PdfPTable(1);
        table.setWidthPercentage(100);
        table.setSpacingAfter(18);

        PdfPCell cell = new PdfPCell();
        cell.setPadding(18);
        cell.setBorder(Rectangle.NO_BORDER);
        cell.setBackgroundColor(BRAND_DARK);

        Paragraph title = new Paragraph(metrics.getReportTitle(), FontFactory.getFont(FontFactory.HELVETICA_BOLD, 18, Color.WHITE));
        title.setSpacingAfter(6);
        cell.addElement(title);

        String orgName = getOrganizationDisplayName(metrics.getOrganization());
        Paragraph orgText = new Paragraph(orgName, FontFactory.getFont(FontFactory.HELVETICA_BOLD, 13, Color.WHITE));
        orgText.setSpacingAfter(8);
        cell.addElement(orgText);

        StringBuilder details = new StringBuilder();
        details.append("Period: ").append(metrics.getPeriodStart().format(DATE_FORMAT)).append(" to ").append(metrics.getPeriodEnd().format(DATE_FORMAT));
        if (metrics.getOrganization().getIndustry() != null && !metrics.getOrganization().getIndustry().isBlank()) {
            details.append("\nIndustry: ").append(metrics.getOrganization().getIndustry());
        }
        if (metrics.getOrganization().getBusinessType() != null && !metrics.getOrganization().getBusinessType().isBlank()) {
            details.append(" | Type: ").append(metrics.getOrganization().getBusinessType());
        }
        if (metrics.getOrganization().getPrimaryEmail() != null && !metrics.getOrganization().getPrimaryEmail().isBlank()) {
            details.append("\nEmail: ").append(metrics.getOrganization().getPrimaryEmail());
        }
        if (metrics.getOrganization().getPrimaryPhone() != null && !metrics.getOrganization().getPrimaryPhone().isBlank()) {
            details.append(" | Phone: ").append(metrics.getOrganization().getPrimaryPhone());
        }
        if (metrics.getOrganization().getRegisteredAddress() != null && !metrics.getOrganization().getRegisteredAddress().isBlank()) {
            details.append("\nAddress: ").append(metrics.getOrganization().getRegisteredAddress());
        }
        if (metrics.getOrganization().getGstNumber() != null && !metrics.getOrganization().getGstNumber().isBlank()) {
            details.append("\nGSTIN: ").append(metrics.getOrganization().getGstNumber());
        }
        if (metrics.getOrganization().getPanNumber() != null && !metrics.getOrganization().getPanNumber().isBlank()) {
            details.append(" | PAN: ").append(metrics.getOrganization().getPanNumber());
        }

        Paragraph body = new Paragraph(details.toString(), FontFactory.getFont(FontFactory.HELVETICA, 10, new Color(203, 213, 225)));
        body.setLeading(14f);
        cell.addElement(body);
        table.addCell(cell);
        document.add(table);
    }

    private PdfPTable buildMetricCards(OverviewMetricsDTO metrics) throws DocumentException {
        PdfPTable table = new PdfPTable(3);
        table.setWidthPercentage(100);
        table.setSpacingAfter(12);
        table.setWidths(new float[]{1f, 1f, 1f});

        table.addCell(buildMetricCard("Total Revenue", formatMoney(metrics.getTotalRevenue()), BRAND_GREEN));
        table.addCell(buildMetricCard("Total Expenses", formatMoney(metrics.getTotalExpenses()), BRAND_RED));
        table.addCell(buildMetricCard("Net Profit/Loss", formatMoney(metrics.getNetProfitLoss()), metrics.getNetProfitLoss().compareTo(BigDecimal.ZERO) >= 0 ? BRAND_GREEN : BRAND_RED));
        table.addCell(buildMetricCard("Outstanding Invoices", metrics.getOutstandingInvoicesCount() + " | " + formatMoney(metrics.getOutstandingInvoicesAmount()), BRAND_AMBER));
        table.addCell(buildMetricCard("Overdue Invoices", metrics.getOverdueInvoicesCount() + " | " + formatMoney(metrics.getOverdueInvoicesAmount()), BRAND_RED));
        table.addCell(buildMetricCard("New Clients", String.valueOf(metrics.getNewClients()), BRAND_GREEN));
        return table;
    }

    private PdfPCell buildMetricCard(String label, String value, Color accent) {
        PdfPCell cell = new PdfPCell();
        cell.setPadding(12);
        cell.setBackgroundColor(SURFACE);
        cell.setBorderColor(BORDER);

        Paragraph labelText = new Paragraph(label, FontFactory.getFont(FontFactory.HELVETICA_BOLD, 10, TEXT_MUTED));
        labelText.setSpacingAfter(8);
        cell.addElement(labelText);

        Paragraph valueText = new Paragraph(value, FontFactory.getFont(FontFactory.HELVETICA_BOLD, 16, accent));
        cell.addElement(valueText);
        return cell;
    }

    private PdfPTable buildOperationsTable(OverviewMetricsDTO metrics) throws DocumentException {
        PdfPTable table = buildDataTable(new float[]{2.2f, 1.2f, 2f});
        addHeaderRow(table, "Metric", "Value", "Notes");
        addDataRow(table, "Period", metrics.getReportTitle(), metrics.getPeriodStart().format(DATE_FORMAT) + " to " + metrics.getPeriodEnd().format(DATE_FORMAT));
        addDataRow(table, "Currency", defaultText(metrics.getOrganization().getCurrency(), "INR"), "Primary reporting currency");
        addDataRow(table, "Outstanding", String.valueOf(metrics.getOutstandingInvoicesCount()), formatMoney(metrics.getOutstandingInvoicesAmount()));
        addDataRow(table, "Overdue", String.valueOf(metrics.getOverdueInvoicesCount()), formatMoney(metrics.getOverdueInvoicesAmount()));
        addDataRow(table, "New Clients", String.valueOf(metrics.getNewClients()), "Created during selected period");
        return table;
    }

    private PdfPTable buildTopClientsTable(List<OverviewMetricsDTO.TopClientDTO> topClients) throws DocumentException {
        PdfPTable table = buildDataTable(new float[]{2.4f, 1.4f, 1.2f});
        addHeaderRow(table, "Client", "Revenue", "Transactions");

        if (topClients == null || topClients.isEmpty()) {
            addEmptyStateRow(table, "No client revenue recorded for the selected period.");
            return table;
        }

        for (OverviewMetricsDTO.TopClientDTO topClient : topClients) {
            addDataRow(table, defaultText(topClient.getClientName(), "Unassigned Client"), formatMoney(topClient.getRevenue()), String.valueOf(topClient.getTransactionCount()));
        }
        return table;
    }

    private PdfPTable buildInvoiceBreakdownTable(OverviewMetricsDTO.InvoiceStatusBreakdown breakdown) throws DocumentException {
        PdfPTable table = buildDataTable(new float[]{1.5f, 1.1f});
        addHeaderRow(table, "Status", "Count");
        addDataRow(table, "Draft", String.valueOf(breakdown.getDraft()));
        addDataRow(table, "Sent", String.valueOf(breakdown.getSent()));
        addDataRow(table, "Paid", String.valueOf(breakdown.getPaid()));
        addDataRow(table, "Overdue", String.valueOf(breakdown.getOverdue()));
        return table;
    }

    private PdfPTable buildMonthlyComparisonTable(List<OverviewMetricsDTO.MonthlyComparisonDTO> rows) throws DocumentException {
        PdfPTable table = buildDataTable(new float[]{1.4f, 1.3f, 1.3f, 1.3f});
        addHeaderRow(table, "Month", "Revenue", "Expenses", "Net");

        if (rows == null || rows.isEmpty()) {
            addEmptyStateRow(table, "No month-by-month comparison is available.");
            return table;
        }

        for (OverviewMetricsDTO.MonthlyComparisonDTO row : rows) {
            addDataRow(table, row.getLabel(), formatMoney(row.getRevenue()), formatMoney(row.getExpenses()), formatMoney(row.getNetProfitLoss()));
        }
        return table;
    }

    private PdfPTable buildComplianceTable(ComplianceSummaryDTO complianceSummary) throws DocumentException {
        PdfPTable table = buildDataTable(new float[]{2.2f, 1.2f, 2.2f});
        addHeaderRow(table, "Area", "Value", "Commentary");

        if (complianceSummary == null) {
            addEmptyStateRow(table, "Compliance summary is not available.");
            return table;
        }

        addDataRow(table, "Regulatory Completeness", round(complianceSummary.getRegulatoryCompletenessPercentage()) + "%", "Profile readiness across core identifiers");
        addDataRow(table, "Total GST Collected", formatMoney(complianceSummary.getTotalGstCollected()), "Based on non-draft invoices");
        addDataRow(table, "Paid Invoices", String.valueOf(complianceSummary.getPaidInvoices()), "Invoices marked PAID");
        addDataRow(table, "Overdue Invoices", String.valueOf(complianceSummary.getOverdueInvoices()), "Compliance-sensitive follow-up items");

        if (complianceSummary.getMissingComplianceFields() == null || complianceSummary.getMissingComplianceFields().isEmpty()) {
            addDataRow(table, "Missing Fields", "0", "No missing regulatory fields detected");
        } else {
            addDataRow(
                    table,
                    "Missing Fields",
                    String.valueOf(complianceSummary.getMissingComplianceFields().size()),
                    complianceSummary.getMissingComplianceFields().stream().limit(2).collect(Collectors.joining(" | "))
            );
        }

        return table;
    }

    private void addFooter(Document document, OverviewMetricsDTO metrics) throws DocumentException {
        Paragraph note = new Paragraph(
                "Generated by MoneyOps on " + LocalDateTime.now().format(DateTimeFormatter.ofPattern("dd MMM yyyy HH:mm", Locale.US))
                        + " for " + getOrganizationDisplayName(metrics.getOrganization()) + ".",
                FontFactory.getFont(FontFactory.HELVETICA_OBLIQUE, 9, TEXT_MUTED)
        );
        note.setAlignment(Element.ALIGN_CENTER);
        note.setSpacingBefore(8);
        document.add(note);
    }

    private void addSectionTitle(Document document, String title) throws DocumentException {
        Paragraph paragraph = new Paragraph(title, FontFactory.getFont(FontFactory.HELVETICA_BOLD, 13, TEXT_PRIMARY));
        paragraph.setSpacingBefore(4);
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
            PdfPCell cell = new PdfPCell(new Phrase(defaultText(value, "N/A"), FontFactory.getFont(FontFactory.HELVETICA, 9, TEXT_PRIMARY)));
            cell.setBackgroundColor(Color.WHITE);
            cell.setBorderColor(BORDER);
            cell.setPadding(8);
            table.addCell(cell);
        }
    }

    private void addEmptyStateRow(PdfPTable table, String message) {
        PdfPCell cell = new PdfPCell(new Phrase(message, FontFactory.getFont(FontFactory.HELVETICA_OBLIQUE, 9, TEXT_MUTED)));
        cell.setColspan(table.getNumberOfColumns());
        cell.setPadding(10);
        cell.setHorizontalAlignment(Element.ALIGN_CENTER);
        cell.setBorderColor(BORDER);
        table.addCell(cell);
    }

    private String getOrganizationDisplayName(OverviewMetricsDTO.OrganizationSummary organization) {
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
        return "INR " + safeAmount(amount).setScale(2, RoundingMode.HALF_UP).toPlainString();
    }

    private String round(double value) {
        return String.format(Locale.US, "%.1f", value);
    }

    private String defaultText(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private record PeriodRange(String period, LocalDate startDate, LocalDate endDate) {
    }

    private record InvoiceSnapshot(
            long outstandingCount,
            BigDecimal outstandingAmount,
            long overdueCount,
            BigDecimal overdueAmount
    ) {
    }

    private record ClientResolution(String clientId, String clientName) {
    }

    private static final class TopClientAccumulator {
        private final String clientId;
        private final String clientName;
        private BigDecimal revenue = BigDecimal.ZERO;
        private long transactionCount = 0;

        private TopClientAccumulator(String clientId, String clientName) {
            this.clientId = clientId;
            this.clientName = clientName;
        }

        private BigDecimal revenue() {
            return revenue;
        }
    }

    private static final class MonthlyBucket {
        private BigDecimal revenue = BigDecimal.ZERO;
        private BigDecimal expenses = BigDecimal.ZERO;
    }
}
