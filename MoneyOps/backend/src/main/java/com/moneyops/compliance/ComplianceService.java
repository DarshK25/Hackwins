package com.moneyops.compliance;

import com.moneyops.clients.entity.Client;
import com.moneyops.clients.repository.ClientRepository;
import com.moneyops.documents.entity.MoneyOpsDocument;
import com.moneyops.documents.repository.DocumentRepository;
import com.moneyops.invoices.entity.Invoice;
import com.moneyops.invoices.entity.InvoiceStatus;
import com.moneyops.invoices.repository.InvoiceRepository;
import com.moneyops.transactions.entity.Transaction;
import com.moneyops.transactions.repository.TransactionRepository;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class ComplianceService {

    private final InvoiceRepository invoiceRepository;
    private final ClientRepository clientRepository;
    private final DocumentRepository documentRepository;
    private final TransactionRepository transactionRepository;

    @Data
    public static class DeadlineDTO {
        private String id;
        private String title;
        private String dueDate;
        private String type;
        private String priority;
        private String status;

        public DeadlineDTO(String id, String title, String dueDate, String type, String priority, String status) {
            this.id = id;
            this.title = title;
            this.dueDate = dueDate;
            this.type = type;
            this.priority = priority;
            this.status = status;
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
    public static class ComplianceStatusResponse {
        private int complianceScore;
        private String status;
        private int pendingFilings;
        private int riskAlerts;
        private DeadlineDTO nextDeadline;
        private List<DeadlineDTO> upcomingDeadlines = new ArrayList<>();
        private List<String> alerts = new ArrayList<>();
        private List<String> keyRequirements = new ArrayList<>();
        private AuditReadinessResponse auditReadiness;
        private String generatedAt;
    }

    public DeadlinesResponse getDeadlines(String businessId) {
        DeadlinesResponse response = new DeadlinesResponse();
        response.setDeadlines(buildDynamicDeadlines());
        return response;
    }

    public ComplianceStatusResponse getComplianceStatus(String orgId, String businessId, String userId) {
        List<Invoice> invoices = orgId == null || orgId.isBlank()
                ? List.of()
                : invoiceRepository.findAllByOrgIdAndDeletedAtIsNull(orgId);
        List<Client> clients = orgId == null || orgId.isBlank()
                ? List.of()
                : clientRepository.findAllByOrgIdAndDeletedAtIsNull(orgId);
        List<MoneyOpsDocument> documents = orgId == null || orgId.isBlank()
                ? List.of()
                : documentRepository.findByOrgIdAndDeletedAtIsNull(orgId);
        List<Transaction> transactions = orgId == null || orgId.isBlank()
                ? List.of()
                : transactionRepository.findAllByOrgIdAndDeletedAtIsNull(orgId);

        List<DeadlineDTO> deadlines = buildDynamicDeadlines();
        LocalDate today = LocalDate.now();
        List<DeadlineDTO> pendingDeadlines = deadlines.stream()
                .filter(d -> !LocalDate.parse(d.getDueDate()).isBefore(today))
                .sorted(Comparator.comparing(DeadlineDTO::getDueDate))
                .collect(Collectors.toList());

        long overdueInvoices = invoices.stream().filter(i -> i.getStatus() == InvoiceStatus.OVERDUE).count();
        long sentInvoices = invoices.stream().filter(i -> i.getStatus() == InvoiceStatus.SENT).count();
        long draftInvoices = invoices.stream().filter(i -> i.getStatus() == InvoiceStatus.DRAFT).count();
        long invoicesWithoutClientEmail = invoices.stream()
                .filter(i -> i.getClientEmail() == null || i.getClientEmail().isBlank())
                .count();
        BigDecimal pendingGst = invoices.stream()
                .filter(i -> i.getStatus() == InvoiceStatus.SENT || i.getStatus() == InvoiceStatus.OVERDUE)
                .map(i -> i.getGstTotal() != null ? i.getGstTotal() : BigDecimal.ZERO)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        List<String> alerts = new ArrayList<>();
        if (overdueInvoices > 0) {
            alerts.add(overdueInvoices + " overdue invoice(s) need follow-up before the next filing cycle.");
        }
        if (invoicesWithoutClientEmail > 0) {
            alerts.add(invoicesWithoutClientEmail + " invoice(s) are missing a client email, which blocks delivery and audit traceability.");
        }
        if (pendingGst.compareTo(BigDecimal.ZERO) > 0) {
            alerts.add("Pending GST exposure on unpaid invoices is INR " + pendingGst + ".");
        }
        if (draftInvoices > 0) {
            alerts.add(draftInvoices + " draft invoice(s) should be reviewed before month-end closing.");
        }
        if (alerts.isEmpty()) {
            alerts.add("No immediate compliance risks detected.");
        }

        List<String> keyRequirements = new ArrayList<>();
        keyRequirements.add("Review GST and TDS filing deadlines against current invoice activity.");
        keyRequirements.add("Ensure invoices and payment records stay linked for audit readiness.");
        keyRequirements.add("Maintain supporting documents for all high-value invoices and tax filings.");
        if (sentInvoices > 0) {
            keyRequirements.add("Follow up on " + sentInvoices + " sent invoice(s) to reduce payment and GST reconciliation risk.");
        }

        AuditReadinessResponse auditReadiness = buildAuditReadiness(invoices, clients, documents, transactions);

        int score = 100;
        score -= Math.min(30, (int) overdueInvoices * 12);
        score -= Math.min(12, (int) invoicesWithoutClientEmail * 4);
        score -= sentInvoices > 5 ? 8 : sentInvoices > 0 ? 4 : 0;
        score -= documents.isEmpty() && !invoices.isEmpty() ? 8 : 0;
        score -= auditReadiness.getAuditReadinessScore() < 80 ? 6 : 0;
        score = Math.max(0, score);

        ComplianceStatusResponse response = new ComplianceStatusResponse();
        response.setComplianceScore(score);
        response.setStatus(score >= 85 ? "compliant" : score >= 65 ? "attention" : "critical");
        response.setPendingFilings((int) pendingDeadlines.stream()
                .filter(d -> daysUntil(LocalDate.parse(d.getDueDate())) <= 30)
                .count());
        response.setRiskAlerts((int) alerts.stream().filter(a -> !a.startsWith("No immediate")).count());
        response.setUpcomingDeadlines(pendingDeadlines);
        response.setNextDeadline(pendingDeadlines.isEmpty() ? null : pendingDeadlines.get(0));
        response.setAlerts(alerts);
        response.setKeyRequirements(keyRequirements);
        response.setAuditReadiness(auditReadiness);
        response.setGeneratedAt(today.toString());
        return response;
    }

    public TdsCalculationResponse calculateTds(TdsCalcRequest request) {
        TdsCalculationResponse response = new TdsCalculationResponse();
        BigDecimal amount = request.getAmount() != null ? request.getAmount() : BigDecimal.ZERO;
        String category = request.getCategory() != null ? request.getCategory().toLowerCase() : "professional";
        boolean isInd = request.getIsIndividual() != null ? request.getIsIndividual() : true;

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
        BigDecimal deductible = amount.multiply(BigDecimal.valueOf(rate)).divide(BigDecimal.valueOf(100));
        response.setDeductible(String.format(Locale.US, "%.2f", deductible.doubleValue()));
        return response;
    }

    private AuditReadinessResponse buildAuditReadiness(
            List<Invoice> invoices,
            List<Client> clients,
            List<MoneyOpsDocument> documents,
            List<Transaction> transactions
    ) {
        AuditReadinessResponse response = new AuditReadinessResponse();
        int totalInvoices = invoices.size();
        int invoicesWithGst = (int) invoices.stream()
                .filter(i -> i.getGstTotal() != null && i.getGstTotal().compareTo(BigDecimal.ZERO) > 0)
                .count();
        int invoicesWithClient = (int) invoices.stream()
                .filter(i -> (i.getClientId() != null && !i.getClientId().isBlank()) || (i.getClientName() != null && !i.getClientName().isBlank()))
                .count();
        Set<String> paidInvoiceIds = transactions.stream()
                .map(Transaction::getInvoiceId)
                .filter(id -> id != null && !id.isBlank())
                .collect(Collectors.toSet());
        int paymentLinkedInvoices = (int) invoices.stream()
                .filter(i -> i.getStatus() == InvoiceStatus.PAID && paidInvoiceIds.contains(i.getId()))
                .count();
        int invoiceLinkedDocs = (int) documents.stream()
                .filter(d -> "INVOICE".equalsIgnoreCase(d.getLinkedEntityType()))
                .count();

        int gstCompletion = percentage(invoicesWithGst, totalInvoices);
        int clientCompletion = percentage(invoicesWithClient, totalInvoices);
        int paymentCompletion = percentage(paymentLinkedInvoices, (int) invoices.stream().filter(i -> i.getStatus() == InvoiceStatus.PAID).count());
        int docsCompletion = percentage(invoiceLinkedDocs, totalInvoices);

        List<ChecklistItem> checklist = new ArrayList<>();
        checklist.add(new ChecklistItem("GST captured on invoices", statusFor(gstCompletion), gstCompletion + "%"));
        checklist.add(new ChecklistItem("Client records linked to invoices", statusFor(clientCompletion), clientCompletion + "%"));
        checklist.add(new ChecklistItem("Payment records linked", statusFor(paymentCompletion), paymentCompletion + "%"));
        checklist.add(new ChecklistItem("Supporting documents uploaded", statusFor(docsCompletion), docsCompletion + "%"));
        checklist.add(new ChecklistItem("Active client base maintained", clients.isEmpty() ? "warn" : "pass", clients.isEmpty() ? "0%" : "100%"));

        int readinessScore = Math.round((gstCompletion + clientCompletion + paymentCompletion + docsCompletion + (clients.isEmpty() ? 0 : 100)) / 5.0f);
        response.setAuditReadinessScore(readinessScore);
        response.setStatus(readinessScore >= 85 ? "ready" : readinessScore >= 65 ? "attention" : "not_ready");
        response.setMessage(readinessScore >= 85
                ? "Audit records are in good shape."
                : "Audit readiness needs attention before the next review.");
        response.setChecklist(checklist);
        return response;
    }

    private List<DeadlineDTO> buildDynamicDeadlines() {
        LocalDate today = LocalDate.now();
        LocalDate nextGst = nextOccurrence(today, 20);
        LocalDate nextTdsPayment = nextOccurrence(today, 7);
        LocalDate nextAdvanceTax = nextAdvanceTaxDeadline(today);
        LocalDate nextAnnualReturn = annualReturnDeadline(today);

        List<DeadlineDTO> deadlines = new ArrayList<>();
        deadlines.add(new DeadlineDTO("gst-" + nextGst, "GST Filing", nextGst.toString(), "GST", priorityFor(nextGst), statusForDeadline(nextGst)));
        deadlines.add(new DeadlineDTO("tds-" + nextTdsPayment, "TDS Payment", nextTdsPayment.toString(), "TDS", priorityFor(nextTdsPayment), statusForDeadline(nextTdsPayment)));
        deadlines.add(new DeadlineDTO("advance-tax-" + nextAdvanceTax, "Advance Tax Installment", nextAdvanceTax.toString(), "TAX", priorityFor(nextAdvanceTax), statusForDeadline(nextAdvanceTax)));
        deadlines.add(new DeadlineDTO("itr-" + nextAnnualReturn, "Annual Income Tax Return", nextAnnualReturn.toString(), "ITR", priorityFor(nextAnnualReturn), statusForDeadline(nextAnnualReturn)));
        deadlines.sort(Comparator.comparing(DeadlineDTO::getDueDate));
        return deadlines;
    }

    private LocalDate nextOccurrence(LocalDate today, int dayOfMonth) {
        LocalDate candidate = today.withDayOfMonth(Math.min(dayOfMonth, today.lengthOfMonth()));
        if (!candidate.isAfter(today)) {
            LocalDate nextMonth = today.plusMonths(1);
            candidate = nextMonth.withDayOfMonth(Math.min(dayOfMonth, nextMonth.lengthOfMonth()));
        }
        return candidate;
    }

    private LocalDate nextAdvanceTaxDeadline(LocalDate today) {
        List<LocalDate> deadlines = List.of(
                LocalDate.of(today.getYear(), 6, 15),
                LocalDate.of(today.getYear(), 9, 15),
                LocalDate.of(today.getYear(), 12, 15),
                LocalDate.of(today.getYear() + 1, 3, 15)
        );
        return deadlines.stream().filter(d -> !d.isBefore(today)).findFirst()
                .orElse(LocalDate.of(today.getYear() + 1, 6, 15));
    }

    private LocalDate annualReturnDeadline(LocalDate today) {
        LocalDate julyDeadline = LocalDate.of(today.getYear(), 7, 31);
        return today.isAfter(julyDeadline) ? LocalDate.of(today.getYear() + 1, 7, 31) : julyDeadline;
    }

    private String priorityFor(LocalDate dueDate) {
        long days = daysUntil(dueDate);
        if (days <= 7) return "high";
        if (days <= 21) return "medium";
        return "low";
    }

    private String statusForDeadline(LocalDate dueDate) {
        long days = daysUntil(dueDate);
        if (days < 0) return "overdue";
        if (days <= 7) return "urgent";
        return "pending";
    }

    private long daysUntil(LocalDate dueDate) {
        return ChronoUnit.DAYS.between(LocalDate.now(), dueDate);
    }

    private int percentage(int numerator, int denominator) {
        if (denominator <= 0) return 100;
        return Math.max(0, Math.min(100, Math.round((numerator * 100f) / denominator)));
    }

    private String statusFor(int completion) {
        if (completion >= 85) return "pass";
        if (completion >= 60) return "warn";
        return "fail";
    }
}
