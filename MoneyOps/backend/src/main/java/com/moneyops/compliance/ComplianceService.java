package com.moneyops.compliance;

import com.moneyops.clients.entity.Client;
import com.moneyops.clients.repository.ClientRepository;
import com.moneyops.documents.entity.MoneyOpsDocument;
import com.moneyops.documents.repository.DocumentRepository;
import com.moneyops.invoices.entity.Invoice;
import com.moneyops.invoices.entity.InvoiceStatus;
import com.moneyops.invoices.repository.InvoiceRepository;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.transactions.entity.Transaction;
import com.moneyops.transactions.entity.TransactionType;
import com.moneyops.transactions.repository.TransactionRepository;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.YearMonth;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class ComplianceService {

    private static final Set<String> TDS_194J_CATEGORIES = Set.of("PROFESSIONAL_FEES", "PROFESSIONAL", "CONSULTING");
    private static final Set<String> TDS_194I_CATEGORIES = Set.of("RENT");
    private static final Set<String> TDS_194C_CATEGORIES = Set.of("CONTRACTOR", "SUBCONTRACTOR");
    private static final Set<String> TDS_DEDUCTOR_HINTS = Set.of("infosys", "tcs", "wipro", "lemon tree", "marriott", "bluedart", "blue dart");

    private final InvoiceRepository invoiceRepository;
    private final ClientRepository clientRepository;
    private final DocumentRepository documentRepository;
    private final TransactionRepository transactionRepository;
    private final BusinessOrganizationRepository businessOrganizationRepository;
    private final ComplianceMetadataService complianceMetadataService;

    @Data
    public static class DeadlineDTO {
        private String id;
        private String title;
        private String dueDate;
        private String type;
        private String priority;
        private String status;
        private long daysRemaining;

        public DeadlineDTO(String id, String title, String dueDate, String type, String priority, String status, long daysRemaining) {
            this.id = id;
            this.title = title;
            this.dueDate = dueDate;
            this.type = type;
            this.priority = priority;
            this.status = status;
            this.daysRemaining = daysRemaining;
        }
    }

    @Data
    public static class DeadlinesResponse {
        private List<DeadlineDTO> deadlines = new ArrayList<>();
    }

    @Data
    public static class TdsCalcRequest {
        private BigDecimal amount;
        private String category;
        private Boolean isIndividual;
    }

    @Data
    public static class TdsCalculationResponse {
        private String section;
        private double rate;
        private String deductible;
    }

    @Data
    public static class ChecklistItem {
        private String item;
        private String status;
        private String completion;
        private String action;
        private List<String> affected = new ArrayList<>();
        private Integer failedCount;
        private BigDecimal amountAtRisk;

        public ChecklistItem(String item, String status, String completion) {
            this.item = item;
            this.status = status;
            this.completion = completion;
        }
    }

    @Data
    public static class AuditReadinessResponse {
        private int auditReadinessScore;
        private String status;
        private String message;
        private List<ChecklistItem> checklist = new ArrayList<>();
    }

    @Data
    public static class ComplianceIssueDTO {
        private String id;
        private String module;
        private String severity;
        private String title;
        private String description;
        private String sourceType;
        private String sourceId;
        private String sourceLabel;
        private String actionLabel;
        private String actionRoute;
        private BigDecimal amountAtRisk;
        private String dueDate;
        private boolean resolved;
    }

    @Data
    public static class GstSummaryResponse {
        private String period;
        private int invoicesReported;
        private BigDecimal totalTaxableValue;
        private BigDecimal outputTax;
        private BigDecimal claimableItc;
        private BigDecimal blockedItc;
        private BigDecimal missingGstinItc;
        private BigDecimal netGstPayable;
        private BigDecimal cgstPayable;
        private BigDecimal sgstPayable;
        private int itcRiskCount;
        private List<String> alerts = new ArrayList<>();
        private List<GstInvoiceBreakdownDTO> invoiceBreakdown = new ArrayList<>();
        private List<GstExpenseBreakdownDTO> expenseBreakdown = new ArrayList<>();
        private List<String> calculationNotes = new ArrayList<>();
    }

    @Data
    public static class GstInvoiceBreakdownDTO {
        private String invoiceId;
        private String invoiceNumber;
        private String clientName;
        private String issueDate;
        private String status;
        private BigDecimal taxableValue;
        private BigDecimal gstAmount;
        private BigDecimal totalAmount;
    }

    @Data
    public static class GstExpenseBreakdownDTO {
        private String transactionId;
        private String description;
        private String vendorName;
        private String category;
        private String transactionDate;
        private BigDecimal grossAmount;
        private BigDecimal taxableValue;
        private BigDecimal gstAmount;
        private boolean claimable;
        private String reason;
    }

    @Data
    public static class TdsObligationDTO {
        private String vendorName;
        private String section;
        private BigDecimal annualPayment;
        private BigDecimal tdsRate;
        private BigDecimal tdsAmount;
        private String action;
        private String actionRoute;
        private List<String> transactionIds = new ArrayList<>();
    }

    @Data
    public static class TdsCreditDTO {
        private String clientName;
        private String invoiceId;
        private String invoiceNumber;
        private BigDecimal tdsCredit;
        private String section;
    }

    @Data
    public static class TdsObligationsResponse {
        private String financialYear;
        private List<TdsObligationDTO> payableTdsObligations = new ArrayList<>();
        private List<TdsCreditDTO> receivableTdsCredits = new ArrayList<>();
        private BigDecimal totalTdsToDeduct = BigDecimal.ZERO;
        private BigDecimal totalTdsCredits = BigDecimal.ZERO;
        private BigDecimal netTdsPosition = BigDecimal.ZERO;
        private String depositDeadline;
        private String formToFile;
        private List<String> calculationNotes = new ArrayList<>();
    }

    @Data
    public static class TdsSummary {
        private BigDecimal payable;
        private BigDecimal credits;
        private BigDecimal net;
    }

    @Data
    public static class ComplianceStatusResponse {
        private int complianceScore;
        private String status;
        private String grade;
        private boolean readyToFile;
        private int pendingFilings;
        private int riskAlerts;
        private DeadlineDTO nextDeadline;
        private List<DeadlineDTO> upcomingDeadlines = new ArrayList<>();
        private List<String> alerts = new ArrayList<>();
        private List<String> keyRequirements = new ArrayList<>();
        private AuditReadinessResponse auditReadiness;
        private GstSummaryResponse gstSummary;
        private TdsSummary tdsSummary;
        private List<ComplianceIssueDTO> issues = new ArrayList<>();
        private String generatedAt;
    }

    public DeadlinesResponse getDeadlines(String orgId, String businessId) {
        DeadlinesResponse response = new DeadlinesResponse();
        response.setDeadlines(buildDynamicDeadlines(LocalDate.now(), getBusiness(orgId)));
        return response;
    }

    public ComplianceStatusResponse getComplianceStatus(String orgId, String businessId, String userId) {
        List<Invoice> invoices = getInvoices(orgId);
        List<Client> clients = getClients(orgId);
        List<MoneyOpsDocument> documents = getDocuments(orgId);
        List<Transaction> transactions = getTransactions(orgId);
        BusinessOrganization business = getBusiness(orgId);
        YearMonth currentPeriod = resolveActivePeriod(invoices, expenseTransactions(transactions), null);

        GstSummaryResponse gstSummary = buildGstSummary(invoices, expenseTransactions(transactions), currentPeriod);
        TdsObligationsResponse tdsObligations = buildTdsObligations(invoices, expenseTransactions(transactions), currentFinancialYear(LocalDate.now()));
        AuditReadinessResponse auditReadiness = buildAuditReadiness(invoices, clients, documents, transactions, business);
        List<ComplianceIssueDTO> issues = buildComplianceIssues(invoices, transactions, documents, business, currentPeriod);

        List<DeadlineDTO> deadlines = buildDynamicDeadlines(LocalDate.now(), business);
        List<DeadlineDTO> pendingDeadlines = deadlines.stream()
                .filter(d -> !LocalDate.parse(d.getDueDate()).isBefore(LocalDate.now()))
                .sorted(Comparator.comparing(DeadlineDTO::getDueDate))
                .collect(Collectors.toList());

        int score = computeComplianceScore(issues, deadlines);
        ComplianceStatusResponse response = new ComplianceStatusResponse();
        response.setComplianceScore(score);
        response.setGrade(score >= 90 ? "A" : score >= 75 ? "B" : score >= 60 ? "C" : "D");
        response.setReadyToFile(score >= 75);
        response.setStatus(score >= 85 ? "compliant" : score >= 65 ? "needs_attention" : "at_risk");
        response.setPendingFilings((int) pendingDeadlines.stream().filter(d -> d.getDaysRemaining() <= 30).count());
        response.setRiskAlerts((int) issues.stream().filter(i -> !"LOW".equals(i.getSeverity())).count());
        response.setUpcomingDeadlines(pendingDeadlines);
        response.setNextDeadline(pendingDeadlines.isEmpty() ? null : pendingDeadlines.get(0));
        response.setAlerts(buildAlerts(gstSummary, issues));
        response.setKeyRequirements(buildKeyRequirements(gstSummary, issues));
        response.setAuditReadiness(auditReadiness);
        response.setGstSummary(gstSummary);
        TdsSummary tdsSummary = new TdsSummary();
        tdsSummary.setPayable(scale(tdsObligations.getTotalTdsToDeduct()));
        tdsSummary.setCredits(scale(tdsObligations.getTotalTdsCredits()));
        tdsSummary.setNet(scale(tdsObligations.getNetTdsPosition()));
        response.setTdsSummary(tdsSummary);
        response.setIssues(issues);
        response.setGeneratedAt(LocalDate.now().toString());
        return response;
    }

    public GstSummaryResponse getGstSummary(String orgId, String period) {
        List<Invoice> invoices = getInvoices(orgId);
        List<Transaction> expenses = expenseTransactions(getTransactions(orgId));
        return buildGstSummary(invoices, expenses, resolveActivePeriod(invoices, expenses, period));
    }

    public TdsObligationsResponse getTdsObligations(String orgId, String financialYear) {
        return buildTdsObligations(getInvoices(orgId), expenseTransactions(getTransactions(orgId)), parseFinancialYear(financialYear));
    }

    public AuditReadinessResponse getAuditReadiness(String orgId) {
        return buildAuditReadiness(
                getInvoices(orgId),
                getClients(orgId),
                getDocuments(orgId),
                getTransactions(orgId),
                getBusiness(orgId)
        );
    }

    public List<ComplianceIssueDTO> getComplianceIssues(String orgId, String period) {
        List<Invoice> invoices = getInvoices(orgId);
        List<Transaction> transactions = getTransactions(orgId);
        return buildComplianceIssues(
                invoices,
                transactions,
                getDocuments(orgId),
                getBusiness(orgId),
                resolveActivePeriod(invoices, expenseTransactions(transactions), period)
        );
    }

    public TdsCalculationResponse calculateTds(TdsCalcRequest request) {
        TdsCalculationResponse response = new TdsCalculationResponse();
        BigDecimal amount = request.getAmount() != null ? request.getAmount() : BigDecimal.ZERO;
        String category = request.getCategory() != null ? request.getCategory().toLowerCase(Locale.ROOT) : "professional";
        boolean isInd = request.getIsIndividual() != null && request.getIsIndividual();

        double rate;
        String section;
        switch (category) {
            case "professional":
                rate = 10.0;
                section = "194J";
                break;
            case "contract":
                rate = isInd ? 1.0 : 2.0;
                section = "194C";
                break;
            case "rent":
                rate = 10.0;
                section = "194I";
                break;
            case "commission":
                rate = 5.0;
                section = "194H";
                break;
            default:
                rate = 10.0;
                section = "194J";
        }

        response.setRate(rate);
        response.setSection(section);
        BigDecimal deductible = amount.multiply(BigDecimal.valueOf(rate)).divide(BigDecimal.valueOf(100), 2, RoundingMode.HALF_UP);
        response.setDeductible(String.format(Locale.US, "%.2f", deductible.doubleValue()));
        return response;
    }

    private GstSummaryResponse buildGstSummary(List<Invoice> invoices, List<Transaction> expenses, YearMonth period) {
        List<Invoice> monthInvoices = invoices.stream()
                .filter(invoice -> isInvoiceInPeriod(invoice, period))
                .collect(Collectors.toList());

        List<Transaction> monthExpenses = expenses.stream()
                .filter(txn -> isTransactionInPeriod(txn, period))
                .collect(Collectors.toList());

        BigDecimal outputTax = monthInvoices.stream()
                .map(this::invoiceGstAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        BigDecimal totalTaxable = monthInvoices.stream()
                .map(this::invoiceTaxableAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        BigDecimal claimableItc = monthExpenses.stream()
                .filter(this::isItcClaimable)
                .map(this::transactionGstAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        BigDecimal blockedItc = monthExpenses.stream()
                .filter(txn -> transactionGstAmount(txn).compareTo(BigDecimal.ZERO) > 0 && !isItcClaimable(txn))
                .map(this::transactionGstAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        BigDecimal missingGstinItc = monthExpenses.stream()
                .filter(this::isEligibleExpenseMissingGstin)
                .map(this::transactionGstAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        BigDecimal netGst = outputTax.subtract(claimableItc).max(BigDecimal.ZERO);

        GstSummaryResponse response = new GstSummaryResponse();
        response.setPeriod(period.toString());
        response.setInvoicesReported(monthInvoices.size());
        response.setTotalTaxableValue(scale(totalTaxable));
        response.setOutputTax(scale(outputTax));
        response.setClaimableItc(scale(claimableItc));
        response.setBlockedItc(scale(blockedItc));
        response.setMissingGstinItc(scale(missingGstinItc));
        response.setNetGstPayable(scale(netGst));
        response.setCgstPayable(scale(netGst.divide(BigDecimal.valueOf(2), 2, RoundingMode.HALF_UP)));
        response.setSgstPayable(scale(netGst.divide(BigDecimal.valueOf(2), 2, RoundingMode.HALF_UP)));
        response.setItcRiskCount((int) monthExpenses.stream().filter(this::isEligibleExpenseMissingGstin).count());
        response.setInvoiceBreakdown(monthInvoices.stream().map(this::toGstInvoiceBreakdown).collect(Collectors.toList()));
        response.setExpenseBreakdown(monthExpenses.stream().map(this::toGstExpenseBreakdown).collect(Collectors.toList()));
        response.getCalculationNotes().add("Output GST is calculated from invoices issued in the selected period.");
        response.getCalculationNotes().add("Claimable ITC includes only expense GST with vendor GSTIN, receipt evidence, and eligible category.");
        response.getCalculationNotes().add("Net GST payable is output GST minus claimable ITC, floored at zero.");
        if (missingGstinItc.compareTo(BigDecimal.ZERO) > 0) {
            response.getAlerts().add("ITC is at risk on " + response.getItcRiskCount() + " expense record(s) due to missing vendor GSTIN.");
        }
        if (monthInvoices.stream().anyMatch(invoice -> invoiceGstAmount(invoice).compareTo(BigDecimal.ZERO) <= 0)) {
            response.getAlerts().add("Some invoices in this period do not have GST captured, which can block accurate GSTR-1 filing.");
        }
        return response;
    }

    private TdsObligationsResponse buildTdsObligations(List<Invoice> invoices, List<Transaction> expenses, FinancialYearRange financialYear) {
        List<Transaction> fyExpenses = expenses.stream()
                .filter(txn -> isWithinFinancialYear(txn.getTransactionDate(), financialYear))
                .collect(Collectors.toList());

        Map<String, List<Transaction>> byVendor = fyExpenses.stream()
                .collect(Collectors.groupingBy(txn -> firstNonBlank(txn.getVendorName(), txn.getDescription(), "Unknown vendor"), LinkedHashMap::new, Collectors.toList()));

        List<TdsObligationDTO> obligations = new ArrayList<>();
        for (Map.Entry<String, List<Transaction>> entry : byVendor.entrySet()) {
            String vendorName = entry.getKey();
            List<Transaction> vendorTransactions = entry.getValue();
            BigDecimal annualTotal = vendorTransactions.stream()
                    .map(txn -> defaultAmount(txn.getAmount()))
                    .reduce(BigDecimal.ZERO, BigDecimal::add);

            String section = determineTdsSection(vendorTransactions, annualTotal);
            if (section == null) {
                continue;
            }

            BigDecimal rate = switch (section) {
                case "194J" -> BigDecimal.valueOf(0.10);
                case "194I" -> BigDecimal.valueOf(0.10);
                default -> BigDecimal.valueOf(0.02);
            };

            TdsObligationDTO dto = new TdsObligationDTO();
            dto.setVendorName(vendorName);
            dto.setSection(section);
            dto.setAnnualPayment(scale(annualTotal));
            dto.setTdsRate(rate);
            dto.setTdsAmount(scale(annualTotal.multiply(rate)));
            dto.setAction("Deduct TDS before the next payment to " + vendorName + ".");
            dto.setActionRoute("/transactions?vendor=" + vendorName + "&focus=tds");
            dto.setTransactionIds(vendorTransactions.stream().map(Transaction::getId).filter(id -> id != null && !id.isBlank()).collect(Collectors.toList()));
            obligations.add(dto);
        }

        List<TdsCreditDTO> credits = invoices.stream()
                .filter(invoice -> isWithinFinancialYear(invoiceEffectiveDate(invoice), financialYear))
                .map(this::toTdsCredit)
                .filter(dto -> dto.getTdsCredit().compareTo(BigDecimal.ZERO) > 0)
                .collect(Collectors.toList());

        TdsObligationsResponse response = new TdsObligationsResponse();
        response.setFinancialYear(financialYear.label());
        response.setPayableTdsObligations(obligations);
        response.setReceivableTdsCredits(credits);
        response.setTotalTdsToDeduct(scale(obligations.stream().map(TdsObligationDTO::getTdsAmount).reduce(BigDecimal.ZERO, BigDecimal::add)));
        response.setTotalTdsCredits(scale(credits.stream().map(TdsCreditDTO::getTdsCredit).reduce(BigDecimal.ZERO, BigDecimal::add)));
        response.setNetTdsPosition(scale(response.getTotalTdsCredits().subtract(response.getTotalTdsToDeduct())));
        response.setDepositDeadline("7th of next month");
        response.setFormToFile("Form 26Q");
        response.getCalculationNotes().add("TDS obligations are grouped vendor-wise across the financial year.");
        response.getCalculationNotes().add("194C is applied only to contractor-style payments, not plain hardware purchases.");
        response.getCalculationNotes().add("Client-side TDS credits are heuristic and should be matched with Form 26AS.");
        return response;
    }

    private AuditReadinessResponse buildAuditReadiness(
            List<Invoice> invoices,
            List<Client> clients,
            List<MoneyOpsDocument> documents,
            List<Transaction> transactions,
            BusinessOrganization business
    ) {
        List<Transaction> expenses = expenseTransactions(transactions);
        List<Transaction> eligibleGstExpenses = expenses.stream()
                .filter(txn -> !complianceMetadataService.isBlockedItcCategory(txn.getCategory()))
                .filter(txn -> transactionGstAmount(txn).compareTo(BigDecimal.ZERO) > 0)
                .collect(Collectors.toList());
        List<Transaction> missingExpenseGstCapture = expenses.stream()
                .filter(this::isPotentialGstExpenseMissingCapturedGst)
                .collect(Collectors.toList());

        List<Invoice> invoicesMissingGst = invoices.stream()
                .filter(invoice -> invoiceGstAmount(invoice).compareTo(BigDecimal.ZERO) <= 0)
                .collect(Collectors.toList());
        List<Transaction> missingVendorGstin = eligibleGstExpenses.stream()
                .filter(txn -> txn.getVendorGstin() == null || txn.getVendorGstin().isBlank())
                .collect(Collectors.toList());
        List<Invoice> paidMissingPaymentDate = invoices.stream()
                .filter(invoice -> invoice.getStatus() == InvoiceStatus.PAID)
                .filter(invoice -> invoice.getPaymentDate() == null)
                .collect(Collectors.toList());
        Set<String> linkedExpenseIds = documents.stream()
                .filter(doc -> "TRANSACTION".equalsIgnoreCase(doc.getLinkedEntityType()))
                .map(MoneyOpsDocument::getLinkedEntityId)
                .collect(Collectors.toSet());
        List<Transaction> missingExpenseReceipts = eligibleGstExpenses.stream()
                .filter(txn -> !Boolean.TRUE.equals(txn.getHasReceipt()))
                .filter(txn -> !linkedExpenseIds.contains(txn.getId()))
                .collect(Collectors.toList());

        List<ChecklistItem> checklist = new ArrayList<>();
        checklist.add(checklistItem(
                "GST computed on all invoices",
                completion(invoices.size() - invoicesMissingGst.size(), invoices.size()),
                "Add GST to " + invoicesMissingGst.size() + " invoice(s)",
                invoiceNumbers(invoicesMissingGst),
                null,
                invoicesMissingGst.size()
        ));
        checklist.add(checklistItem(
                "Vendor GSTIN on ITC-eligible expenses",
                completion(eligibleGstExpenses.size() - missingVendorGstin.size(), eligibleGstExpenses.size()),
                "Collect GSTIN from " + missingVendorGstin.size() + " vendor record(s)",
                labelsForTransactions(missingVendorGstin),
                missingVendorGstin.stream().map(this::transactionGstAmount).reduce(BigDecimal.ZERO, BigDecimal::add),
                missingVendorGstin.size()
        ));
        checklist.add(checklistItem(
                "GST captured on GST-bearing expenses",
                completion(expenses.size() - missingExpenseGstCapture.size(), expenses.size()),
                "Record GST amount on GST-bearing expenses before filing",
                labelsForTransactions(missingExpenseGstCapture),
                missingExpenseGstCapture.stream().map(this::estimatedExpenseGstAmount).reduce(BigDecimal.ZERO, BigDecimal::add),
                missingExpenseGstCapture.size()
        ));
        checklist.add(checklistItem(
                "Payment dates recorded on paid invoices",
                completion(countPaidWithPaymentDate(invoices), countPaidInvoices(invoices)),
                "Add payment dates to paid invoices",
                invoiceNumbers(paidMissingPaymentDate),
                null,
                paidMissingPaymentDate.size()
        ));
        checklist.add(checklistItem(
                "Receipts linked to GST-bearing expenses",
                completion(eligibleGstExpenses.size() - missingExpenseReceipts.size(), eligibleGstExpenses.size()),
                "Upload receipts for expense records",
                labelsForTransactions(missingExpenseReceipts),
                missingExpenseReceipts.stream().map(this::transactionGstAmount).reduce(BigDecimal.ZERO, BigDecimal::add),
                missingExpenseReceipts.size()
        ));

        ChecklistItem businessGstinItem = new ChecklistItem(
                "GSTIN registered and active",
                !complianceMetadataService.requiresBusinessGstin(business) || hasBusinessGstin(business) ? "pass" : "fail",
                !complianceMetadataService.requiresBusinessGstin(business) || hasBusinessGstin(business) ? "100%" : "0%"
        );
        businessGstinItem.setAction(!complianceMetadataService.requiresBusinessGstin(business) || hasBusinessGstin(business) ? null : "Add GSTIN in business settings");
        businessGstinItem.setFailedCount(!complianceMetadataService.requiresBusinessGstin(business) || hasBusinessGstin(business) ? 0 : 1);
        checklist.add(businessGstinItem);

        int readinessScore = (int) Math.round(checklist.stream()
                .mapToInt(item -> Integer.parseInt(item.getCompletion().replace("%", "")))
                .average()
                .orElse(100));

        AuditReadinessResponse response = new AuditReadinessResponse();
        response.setAuditReadinessScore(readinessScore);
        response.setStatus(readinessScore >= 85 ? "ready" : readinessScore >= 65 ? "attention" : "not_ready");
        response.setMessage(readinessScore >= 85
                ? "Audit records are in good shape."
                : "Audit evidence needs work before the next filing or review.");
        response.setChecklist(checklist);
        return response;
    }

    private List<ComplianceIssueDTO> buildComplianceIssues(
            List<Invoice> invoices,
            List<Transaction> transactions,
            List<MoneyOpsDocument> documents,
            BusinessOrganization business,
            YearMonth period
    ) {
        List<ComplianceIssueDTO> issues = new ArrayList<>();
        List<Transaction> periodExpenses = expenseTransactions(transactions).stream()
                .filter(txn -> isTransactionInPeriod(txn, period))
                .collect(Collectors.toList());
        Set<String> linkedExpenseIds = documents.stream()
                .filter(doc -> "TRANSACTION".equalsIgnoreCase(doc.getLinkedEntityType()))
                .map(MoneyOpsDocument::getLinkedEntityId)
                .collect(Collectors.toSet());

        for (Invoice invoice : invoices) {
            if (!isInvoiceInPeriod(invoice, period)) {
                continue;
            }
            if (invoiceGstAmount(invoice).compareTo(BigDecimal.ZERO) <= 0) {
                issues.add(issue(
                        "GST",
                        "HIGH",
                        "Invoice missing GST amount",
                        "Invoice " + firstNonBlank(invoice.getInvoiceNumber(), invoice.getId(), "invoice") + " has no GST amount captured for filing.",
                        "INVOICE",
                        invoice.getId(),
                        firstNonBlank(invoice.getInvoiceNumber(), invoice.getClientName(), "Invoice"),
                        "Fix invoice GST",
                        "/invoices/" + invoice.getId(),
                        invoiceTotal(invoice),
                        invoice.getDueDate()
                ));
            }
            if (invoice.getStatus() == InvoiceStatus.PAID && invoice.getPaymentDate() == null) {
                issues.add(issue(
                        "AUDIT",
                        "MEDIUM",
                        "Paid invoice missing payment date",
                        "Paid invoice " + firstNonBlank(invoice.getInvoiceNumber(), invoice.getId(), "invoice") + " needs a payment date for audit traceability.",
                        "INVOICE",
                        invoice.getId(),
                        firstNonBlank(invoice.getInvoiceNumber(), invoice.getClientName(), "Invoice"),
                        "Record payment date",
                        "/invoices/" + invoice.getId(),
                        invoiceTotal(invoice),
                        invoice.getDueDate()
                ));
            }
        }

        for (Transaction txn : periodExpenses) {
            BigDecimal gstAmount = transactionGstAmount(txn);
            if (isPotentialGstExpenseMissingCapturedGst(txn)) {
                issues.add(issue(
                        "GST",
                        "MEDIUM",
                        "Expense missing GST details",
                        firstNonBlank(txn.getDescription(), "Expense") + " looks GST-bearing but has no GST amount captured yet.",
                        "TRANSACTION",
                        txn.getId(),
                        firstNonBlank(txn.getVendorName(), txn.getDescription(), "Expense"),
                        "Record GST amount",
                        "/transactions?highlight=" + txn.getId() + "&focus=gst",
                        estimatedExpenseGstAmount(txn),
                        txn.getTransactionDate()
                ));
            }
            if (isEligibleExpenseMissingGstin(txn)) {
                issues.add(issue(
                        "ITC",
                        "MEDIUM",
                        "ITC blocked due to missing vendor GSTIN",
                        firstNonBlank(txn.getDescription(), "Expense") + " has GST but no vendor GSTIN, so ITC cannot be claimed yet.",
                        "TRANSACTION",
                        txn.getId(),
                        firstNonBlank(txn.getVendorName(), txn.getDescription(), "Expense"),
                        "Update vendor GSTIN",
                        "/transactions?highlight=" + txn.getId() + "&focus=vendorGstin",
                        gstAmount,
                        txn.getTransactionDate()
                ));
            }
            if (gstAmount.compareTo(BigDecimal.ZERO) > 0
                    && !Boolean.TRUE.equals(txn.getHasReceipt())
                    && !linkedExpenseIds.contains(txn.getId())) {
                issues.add(issue(
                        "AUDIT",
                        "MEDIUM",
                        "Receipt missing for GST-bearing expense",
                        firstNonBlank(txn.getDescription(), "Expense") + " needs a linked receipt or tax invoice before audit review.",
                        "TRANSACTION",
                        txn.getId(),
                        firstNonBlank(txn.getVendorName(), txn.getDescription(), "Expense"),
                        "Upload receipt",
                        "/transactions?highlight=" + txn.getId() + "&focus=document",
                        gstAmount,
                        txn.getTransactionDate()
                ));
            }
        }

        if (complianceMetadataService.requiresBusinessGstin(business) && !hasBusinessGstin(business)) {
            issues.add(issue(
                    "PROFILE",
                    "CRITICAL",
                    "Business GSTIN missing",
                    "Add the business GSTIN before you rely on GST filing readiness.",
                    "BUSINESS",
                    business != null ? business.getId() : "business-profile",
                    business != null ? firstNonBlank(business.getLegalName(), "Business profile") : "Business profile",
                    "Open business settings",
                    "/settings/business?focus=gstin",
                    BigDecimal.ZERO,
                    null
            ));
        }

        return issues.stream()
                .sorted(Comparator.comparing(this::severityRank).thenComparing(ComplianceIssueDTO::getTitle))
                .collect(Collectors.toList());
    }

    private int computeComplianceScore(List<ComplianceIssueDTO> issues, List<DeadlineDTO> deadlines) {
        int score = 100;
        for (ComplianceIssueDTO issue : issues) {
            score -= switch (issue.getSeverity()) {
                case "CRITICAL" -> 15;
                case "HIGH" -> 6;
                case "MEDIUM" -> 3;
                default -> 1;
            };
        }
        boolean urgentAndBlocked = deadlines.stream().anyMatch(d -> d.getDaysRemaining() <= 3) && !issues.isEmpty();
        if (urgentAndBlocked) {
            score -= 10;
        }
        return Math.max(0, score);
    }

    private List<String> buildAlerts(GstSummaryResponse gstSummary, List<ComplianceIssueDTO> issues) {
        List<String> alerts = new ArrayList<>();
        alerts.addAll(gstSummary.getAlerts());
        issues.stream()
                .limit(3)
                .forEach(issue -> alerts.add(issue.getTitle() + ": " + issue.getDescription()));
        if (alerts.isEmpty()) {
            alerts.add("No immediate filing blockers detected.");
        }
        return alerts;
    }

    private List<String> buildKeyRequirements(GstSummaryResponse gstSummary, List<ComplianceIssueDTO> issues) {
        List<String> requirements = new ArrayList<>();
        requirements.add("Report all invoices raised in the period in GSTR-1, including unpaid ones.");
        requirements.add("Claim ITC only where GST amount, vendor GSTIN, and eligibility evidence are present.");
        requirements.add("Keep payment dates and receipts linked to invoices and expenses for audit trail.");
        if (gstSummary.getMissingGstinItc().compareTo(BigDecimal.ZERO) > 0) {
            requirements.add("Recover missing vendor GSTIN details to unlock blocked ITC.");
        }
        if (issues.stream().anyMatch(issue -> "CRITICAL".equals(issue.getSeverity()))) {
            requirements.add("Resolve critical profile or filing blockers before relying on the compliance score.");
        }
        return requirements;
    }

    private List<DeadlineDTO> buildDynamicDeadlines(LocalDate today, BusinessOrganization business) {
        LocalDate nextMonthBase = today.plusMonths(1).withDayOfMonth(1);
        LocalDate nextGstr1 = nextMonthBase.withDayOfMonth(11);
        LocalDate nextGstr3b = nextMonthBase.withDayOfMonth(20);
        LocalDate nextTdsPayment = nextMonthBase.withDayOfMonth(7);
        LocalDate nextTdsQuarterly = nextTdsReturnDeadline(today);
        LocalDate nextAdvanceTax = nextAdvanceTaxDeadline(today);
        LocalDate nextAnnualReturn = annualReturnDeadline(today);

        List<DeadlineDTO> deadlines = new ArrayList<>();
        if (complianceMetadataService.requiresBusinessGstin(business)) {
            deadlines.add(deadline("gstr1-" + nextGstr1, "GSTR-1", nextGstr1, "GST"));
            deadlines.add(deadline("gstr3b-" + nextGstr3b, "GSTR-3B", nextGstr3b, "GST"));
        }
        deadlines.add(deadline("tds-deposit-" + nextTdsPayment, "TDS Deposit", nextTdsPayment, "TDS"));
        deadlines.add(deadline("tds-return-" + nextTdsQuarterly, "TDS Return", nextTdsQuarterly, "TDS"));
        deadlines.add(deadline("advance-tax-" + nextAdvanceTax, "Advance Tax Installment", nextAdvanceTax, "TAX"));
        deadlines.add(deadline("itr-" + nextAnnualReturn, "Annual Income Tax Return", nextAnnualReturn, "ITR"));
        deadlines.sort(Comparator.comparing(DeadlineDTO::getDueDate));
        return deadlines;
    }

    private DeadlineDTO deadline(String id, String title, LocalDate dueDate, String type) {
        long days = daysUntil(dueDate);
        return new DeadlineDTO(
                id,
                title,
                dueDate.toString(),
                type,
                priorityFor(days),
                statusForDeadline(days),
                days
        );
    }

    private AuditReadinessResponse buildAuditReadiness(List<Invoice> invoices, List<Client> clients, List<MoneyOpsDocument> documents, List<Transaction> transactions) {
        return buildAuditReadiness(invoices, clients, documents, transactions, null);
    }

    private ChecklistItem checklistItem(
            String item,
            int completion,
            String action,
            List<String> affected,
            BigDecimal amountAtRisk,
            int failedCount
    ) {
        ChecklistItem checklistItem = new ChecklistItem(item, statusFor(completion), completion + "%");
        checklistItem.setAction(failedCount > 0 ? action : null);
        checklistItem.setAffected(affected.stream().limit(5).collect(Collectors.toList()));
        checklistItem.setAmountAtRisk(amountAtRisk != null && amountAtRisk.compareTo(BigDecimal.ZERO) > 0 ? scale(amountAtRisk) : null);
        checklistItem.setFailedCount(failedCount);
        return checklistItem;
    }

    private int completion(int passed, int total) {
        if (total <= 0) {
            return 100;
        }
        return Math.max(0, Math.min(100, Math.round((passed * 100f) / total)));
    }

    private int countPaidInvoices(List<Invoice> invoices) {
        return (int) invoices.stream().filter(invoice -> invoice.getStatus() == InvoiceStatus.PAID).count();
    }

    private int countPaidWithPaymentDate(List<Invoice> invoices) {
        return (int) invoices.stream().filter(invoice -> invoice.getStatus() == InvoiceStatus.PAID && invoice.getPaymentDate() != null).count();
    }

    private ComplianceIssueDTO issue(
            String module,
            String severity,
            String title,
            String description,
            String sourceType,
            String sourceId,
            String sourceLabel,
            String actionLabel,
            String actionRoute,
            BigDecimal amountAtRisk,
            LocalDate dueDate
    ) {
        ComplianceIssueDTO issue = new ComplianceIssueDTO();
        issue.setId(UUID.randomUUID().toString());
        issue.setModule(module);
        issue.setSeverity(severity);
        issue.setTitle(title);
        issue.setDescription(description);
        issue.setSourceType(sourceType);
        issue.setSourceId(sourceId);
        issue.setSourceLabel(sourceLabel);
        issue.setActionLabel(actionLabel);
        issue.setActionRoute(actionRoute);
        issue.setAmountAtRisk(scale(amountAtRisk));
        issue.setDueDate(dueDate != null ? dueDate.toString() : null);
        issue.setResolved(false);
        return issue;
    }

    private TdsCreditDTO toTdsCredit(Invoice invoice) {
        BigDecimal total = invoiceTotal(invoice);
        BigDecimal paid = defaultAmount(invoice.getAmountPaid());
        BigDecimal gap = total.subtract(paid);
        TdsCreditDTO credit = new TdsCreditDTO();
        credit.setClientName(firstNonBlank(invoice.getClientName(), invoice.getClientCompany(), "Client"));
        credit.setInvoiceId(invoice.getId());
        credit.setInvoiceNumber(firstNonBlank(invoice.getInvoiceNumber(), invoice.getId(), "Invoice"));
        credit.setSection("194J");
        boolean likelyTdsGap = gap.compareTo(BigDecimal.ZERO) > 0
                && total.compareTo(BigDecimal.ZERO) > 0
                && isLikelyTdsDeductor(invoice)
                && gap.compareTo(total.multiply(BigDecimal.valueOf(0.11))) <= 0;
        credit.setTdsCredit(likelyTdsGap ? scale(gap) : BigDecimal.ZERO);
        return credit;
    }

    private GstInvoiceBreakdownDTO toGstInvoiceBreakdown(Invoice invoice) {
        GstInvoiceBreakdownDTO dto = new GstInvoiceBreakdownDTO();
        dto.setInvoiceId(invoice.getId());
        dto.setInvoiceNumber(firstNonBlank(invoice.getInvoiceNumber(), invoice.getId(), "Invoice"));
        dto.setClientName(firstNonBlank(invoice.getClientName(), invoice.getClientCompany(), "Client"));
        dto.setIssueDate(invoiceEffectiveDate(invoice) != null ? invoiceEffectiveDate(invoice).toString() : null);
        dto.setStatus(invoice.getStatus() != null ? invoice.getStatus().name() : null);
        dto.setTaxableValue(invoiceTaxableAmount(invoice));
        dto.setGstAmount(invoiceGstAmount(invoice));
        dto.setTotalAmount(invoiceTotal(invoice));
        return dto;
    }

    private GstExpenseBreakdownDTO toGstExpenseBreakdown(Transaction txn) {
        GstExpenseBreakdownDTO dto = new GstExpenseBreakdownDTO();
        dto.setTransactionId(txn.getId());
        dto.setDescription(firstNonBlank(txn.getDescription(), "Expense"));
        dto.setVendorName(firstNonBlank(txn.getVendorName(), "Unknown vendor"));
        dto.setCategory(normalizeCategory(txn.getCategory()));
        dto.setTransactionDate(txn.getTransactionDate() != null ? txn.getTransactionDate().toString() : null);
        dto.setGrossAmount(scale(defaultAmount(txn.getAmount())));
        dto.setTaxableValue(scale(defaultAmount(txn.getTaxableAmount())));
        dto.setGstAmount(transactionGstAmount(txn));
        boolean claimable = isItcClaimable(txn);
        dto.setClaimable(claimable);
        dto.setReason(claimable ? "Included in claimable ITC" : itcExclusionReason(txn));
        return dto;
    }

    private String itcExclusionReason(Transaction txn) {
        if (transactionGstAmount(txn).compareTo(BigDecimal.ZERO) <= 0) {
            return "No GST captured on this expense";
        }
        if (complianceMetadataService.isBlockedItcCategory(txn.getCategory())) {
            return "Category is treated as non-claimable for ITC";
        }
        if (!Boolean.TRUE.equals(txn.getItcEligible())) {
            return "Marked ineligible for ITC";
        }
        if (txn.getVendorGstin() == null || txn.getVendorGstin().isBlank()) {
            return "Vendor GSTIN missing";
        }
        if (!Boolean.TRUE.equals(txn.getHasReceipt())) {
            return "Receipt or tax invoice not marked available";
        }
        return "Excluded from claimable ITC";
    }

    private String determineTdsSection(List<Transaction> transactions, BigDecimal annualTotal) {
        String category = normalizeCategory(transactions.get(0).getCategory());
        if (TDS_194J_CATEGORIES.contains(category) && annualTotal.compareTo(BigDecimal.valueOf(30_000)) > 0) {
            return "194J";
        }
        if (TDS_194I_CATEGORIES.contains(category) && annualTotal.compareTo(BigDecimal.valueOf(240_000)) > 0) {
            return "194I";
        }
        if ((TDS_194C_CATEGORIES.contains(category) || descriptionsSuggestContractor(transactions))
                && annualTotal.compareTo(BigDecimal.valueOf(30_000)) > 0) {
            return "194C";
        }
        return null;
    }

    private boolean descriptionsSuggestContractor(List<Transaction> transactions) {
        return transactions.stream()
                .map(Transaction::getDescription)
                .filter(desc -> desc != null)
                .map(desc -> desc.toLowerCase(Locale.ROOT))
                .anyMatch(desc -> desc.contains("subcontract") || desc.contains("labour") || desc.contains("contract"));
    }

    private boolean isLikelyTdsDeductor(Invoice invoice) {
        String client = firstNonBlank(invoice.getClientName(), invoice.getClientCompany(), "").toLowerCase(Locale.ROOT);
        return TDS_DEDUCTOR_HINTS.stream().anyMatch(client::contains);
    }

    private boolean isItcClaimable(Transaction txn) {
        return Boolean.TRUE.equals(txn.getItcEligible())
                && transactionGstAmount(txn).compareTo(BigDecimal.ZERO) > 0
                && txn.getVendorGstin() != null
                && !txn.getVendorGstin().isBlank()
                && Boolean.TRUE.equals(txn.getHasReceipt())
                && !complianceMetadataService.isBlockedItcCategory(txn.getCategory());
    }

    private boolean isEligibleExpenseMissingGstin(Transaction txn) {
        return transactionGstAmount(txn).compareTo(BigDecimal.ZERO) > 0
                && !complianceMetadataService.isBlockedItcCategory(txn.getCategory())
                && (txn.getVendorGstin() == null || txn.getVendorGstin().isBlank());
    }

    private boolean isPotentialGstExpenseMissingCapturedGst(Transaction txn) {
        return txn != null
                && txn.getType() == TransactionType.EXPENSE
                && defaultAmount(txn.getAmount()).compareTo(BigDecimal.ZERO) > 0
                && transactionGstAmount(txn).compareTo(BigDecimal.ZERO) <= 0
                && complianceMetadataService.isPotentialGstBearingCategory(txn.getCategory());
    }

    private boolean isInvoiceInPeriod(Invoice invoice, YearMonth period) {
        LocalDate effectiveDate = invoiceEffectiveDate(invoice);
        return effectiveDate != null && YearMonth.from(effectiveDate).equals(period);
    }

    private boolean isTransactionInPeriod(Transaction txn, YearMonth period) {
        return txn.getTransactionDate() != null && YearMonth.from(txn.getTransactionDate()).equals(period);
    }

    private LocalDate invoiceEffectiveDate(Invoice invoice) {
        if (invoice.getIssueDate() != null) {
            return invoice.getIssueDate();
        }
        LocalDateTime createdAt = invoice.getCreatedAt();
        return createdAt != null ? createdAt.toLocalDate() : null;
    }

    private boolean isWithinFinancialYear(LocalDate date, FinancialYearRange financialYear) {
        return date != null && !date.isBefore(financialYear.start()) && !date.isAfter(financialYear.end());
    }

    private String normalizeCategory(String category) {
        return complianceMetadataService.normalizeCategory(category);
    }

    private BigDecimal invoiceGstAmount(Invoice invoice) {
        if (invoice.getGstTotal() != null) {
            return scale(invoice.getGstTotal());
        }
        BigDecimal total = defaultAmount(invoice.getTotalAmount());
        return total.compareTo(BigDecimal.ZERO) > 0
                ? scale(total.multiply(BigDecimal.valueOf(18)).divide(BigDecimal.valueOf(118), 2, RoundingMode.HALF_UP))
                : BigDecimal.ZERO;
    }

    private BigDecimal invoiceTaxableAmount(Invoice invoice) {
        if (invoice.getSubtotal() != null) {
            return scale(invoice.getSubtotal());
        }
        return scale(invoiceTotal(invoice).subtract(invoiceGstAmount(invoice)));
    }

    private BigDecimal invoiceTotal(Invoice invoice) {
        return scale(defaultAmount(invoice.getTotalAmount()));
    }

    private BigDecimal transactionGstAmount(Transaction txn) {
        return scale(defaultAmount(txn.getGstAmount()));
    }

    private BigDecimal estimatedExpenseGstAmount(Transaction txn) {
        return complianceMetadataService.deriveInclusiveGst(defaultAmount(txn.getAmount()));
    }

    private BigDecimal defaultAmount(BigDecimal value) {
        return value != null ? value : BigDecimal.ZERO;
    }

    private BigDecimal scale(BigDecimal value) {
        return (value != null ? value : BigDecimal.ZERO).setScale(2, RoundingMode.HALF_UP);
    }

    private List<Invoice> getInvoices(String orgId) {
        return orgId == null || orgId.isBlank() ? List.of() : invoiceRepository.findAllByOrgIdAndDeletedAtIsNull(orgId);
    }

    private List<Client> getClients(String orgId) {
        return orgId == null || orgId.isBlank() ? List.of() : clientRepository.findAllByOrgIdAndDeletedAtIsNull(orgId);
    }

    private List<MoneyOpsDocument> getDocuments(String orgId) {
        return orgId == null || orgId.isBlank() ? List.of() : documentRepository.findByOrgIdAndDeletedAtIsNull(orgId);
    }

    private List<Transaction> getTransactions(String orgId) {
        return orgId == null || orgId.isBlank() ? List.of() : transactionRepository.findAllByOrgIdAndDeletedAtIsNull(orgId);
    }

    private List<Transaction> expenseTransactions(List<Transaction> transactions) {
        return transactions.stream()
                .filter(txn -> txn.getType() == TransactionType.EXPENSE)
                .collect(Collectors.toList());
    }

    private BusinessOrganization getBusiness(String orgId) {
        return orgId == null || orgId.isBlank()
                ? null
                : businessOrganizationRepository.findByIdAndDeletedAtIsNull(orgId).orElse(null);
    }

    private boolean hasBusinessGstin(BusinessOrganization business) {
        return complianceMetadataService.hasValidBusinessGstin(business);
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return "";
    }

    private List<String> invoiceNumbers(Collection<Invoice> invoices) {
        return invoices.stream()
                .map(invoice -> firstNonBlank(invoice.getInvoiceNumber(), invoice.getId(), "Invoice"))
                .collect(Collectors.toList());
    }

    private List<String> labelsForTransactions(Collection<Transaction> transactions) {
        return transactions.stream()
                .map(txn -> firstNonBlank(txn.getVendorName(), txn.getDescription(), txn.getId(), "Expense"))
                .collect(Collectors.toList());
    }

    private String priorityFor(long days) {
        if (days <= 3) return "high";
        if (days <= 7) return "medium";
        return "low";
    }

    private String statusForDeadline(long days) {
        if (days < 0) return "overdue";
        if (days <= 3) return "critical";
        if (days <= 7) return "warning";
        return "normal";
    }

    private long daysUntil(LocalDate dueDate) {
        return ChronoUnit.DAYS.between(LocalDate.now(), dueDate);
    }

    private String statusFor(int completion) {
        if (completion >= 85) return "pass";
        if (completion >= 60) return "warn";
        return "fail";
    }

    private int severityRank(ComplianceIssueDTO issue) {
        return switch (issue.getSeverity()) {
            case "CRITICAL" -> 0;
            case "HIGH" -> 1;
            case "MEDIUM" -> 2;
            default -> 3;
        };
    }

    private LocalDate nextAdvanceTaxDeadline(LocalDate today) {
        List<LocalDate> deadlines = List.of(
                LocalDate.of(today.getYear(), 6, 15),
                LocalDate.of(today.getYear(), 9, 15),
                LocalDate.of(today.getYear(), 12, 15),
                LocalDate.of(today.getYear() + 1, 3, 15)
        );
        return deadlines.stream()
                .filter(date -> !date.isBefore(today))
                .findFirst()
                .orElse(LocalDate.of(today.getYear() + 1, 6, 15));
    }

    private LocalDate annualReturnDeadline(LocalDate today) {
        LocalDate julyDeadline = LocalDate.of(today.getYear(), 7, 31);
        return today.isAfter(julyDeadline) ? LocalDate.of(today.getYear() + 1, 7, 31) : julyDeadline;
    }

    private LocalDate nextTdsReturnDeadline(LocalDate today) {
        List<LocalDate> deadlines = List.of(
                LocalDate.of(today.getYear(), 7, 31),
                LocalDate.of(today.getYear(), 10, 31),
                LocalDate.of(today.getYear() + 1, 1, 31),
                LocalDate.of(today.getYear() + 1, 5, 31)
        );
        return deadlines.stream()
                .filter(date -> !date.isBefore(today))
                .findFirst()
                .orElse(LocalDate.of(today.getYear() + 1, 7, 31));
    }

    private YearMonth resolveActivePeriod(List<Invoice> invoices, List<Transaction> expenses, String requestedPeriod) {
        if (requestedPeriod != null && !requestedPeriod.isBlank()) {
            return YearMonth.parse(requestedPeriod);
        }

        YearMonth current = YearMonth.now();
        boolean hasCurrentInvoiceActivity = invoices.stream().anyMatch(invoice -> isInvoiceInPeriod(invoice, current));
        boolean hasCurrentExpenseActivity = expenses.stream().anyMatch(txn -> isTransactionInPeriod(txn, current));
        if (hasCurrentInvoiceActivity || hasCurrentExpenseActivity) {
            return current;
        }

        List<YearMonth> periods = new ArrayList<>();
        invoices.stream()
                .map(this::invoiceEffectiveDate)
                .filter(date -> date != null)
                .map(YearMonth::from)
                .forEach(periods::add);
        expenses.stream()
                .map(Transaction::getTransactionDate)
                .filter(date -> date != null)
                .map(YearMonth::from)
                .forEach(periods::add);

        return periods.stream().max(Comparator.naturalOrder()).orElse(current);
    }

    private FinancialYearRange parseFinancialYear(String financialYear) {
        if (financialYear == null || financialYear.isBlank()) {
            return currentFinancialYear(LocalDate.now());
        }
        String[] parts = financialYear.split("-");
        int startYear = Integer.parseInt(parts[0]);
        int endYear = parts.length > 1 && parts[1].length() == 2
                ? (startYear / 100) * 100 + Integer.parseInt(parts[1])
                : startYear + 1;
        return new FinancialYearRange(
                LocalDate.of(startYear, 4, 1),
                LocalDate.of(endYear, 3, 31),
                financialYear
        );
    }

    private FinancialYearRange currentFinancialYear(LocalDate today) {
        int startYear = today.getMonthValue() >= 4 ? today.getYear() : today.getYear() - 1;
        int endYear = startYear + 1;
        return new FinancialYearRange(
                LocalDate.of(startYear, 4, 1),
                LocalDate.of(endYear, 3, 31),
                startYear + "-" + String.format(Locale.US, "%02d", endYear % 100)
        );
    }

    private record FinancialYearRange(LocalDate start, LocalDate end, String label) {}
}
