package com.moneyops.intelligence;

import com.moneyops.shared.utils.OrgContext;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/finance-intelligence")
public class FinanceIntelligenceController {

    @Autowired
    private FinanceIntelligenceService financeIntelligenceService;

    @Autowired
    private AnalyticsReportExportService analyticsReportExportService;

    @GetMapping("/metrics")
    public ResponseEntity<FinanceIntelligenceService.MetricsDTO> getMetrics(@RequestParam String businessId) {
        return ResponseEntity.ok(financeIntelligenceService.getMetrics(businessId));
    }

    @GetMapping("/budget")
    public ResponseEntity<FinanceIntelligenceService.BudgetDTO> getBudget(@RequestParam String businessId) {
        return ResponseEntity.ok(financeIntelligenceService.getBudget(businessId));
    }

    @GetMapping("/insights")
    public ResponseEntity<FinanceIntelligenceService.InsightsDTO> getInsights(@RequestParam String businessId) {
        return ResponseEntity.ok(financeIntelligenceService.getInsights(businessId));
    }

    @GetMapping("/ledger")
    public ResponseEntity<FinanceIntelligenceService.LedgerDTO> getLedger(
            @RequestParam String businessId,
            @RequestParam(defaultValue = "20") int limit) {
        return ResponseEntity.ok(financeIntelligenceService.getLedger(businessId, limit));
    }

    @GetMapping("/client-revenue-summary")
    public ResponseEntity<FinanceIntelligenceService.ClientRevenueSummaryDTO> getClientRevenueSummary(
            @RequestParam String businessId,
            @RequestParam(defaultValue = "5") int limit) {
        return ResponseEntity.ok(financeIntelligenceService.getClientRevenueSummary(businessId, limit));
    }

    @GetMapping("/client-revenue/{clientId}")
    public ResponseEntity<FinanceIntelligenceService.ClientRevenueItemDTO> getClientRevenueDetails(
            @PathVariable String clientId,
            @RequestParam String businessId) {
        return ResponseEntity.ok(financeIntelligenceService.getClientRevenueDetails(businessId, clientId));
    }

    @GetMapping(value = "/report", produces = MediaType.APPLICATION_PDF_VALUE)
    public ResponseEntity<ByteArrayResource> downloadOverviewReport(@RequestParam String businessId) {
        String orgId = OrgContext.getOrgId();
        byte[] pdf = analyticsReportExportService.generateOverviewReport(businessId, orgId);
        String filename = analyticsReportExportService.buildOverviewReportFilename(orgId);

        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_PDF)
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
                .contentLength(pdf.length)
                .body(new ByteArrayResource(pdf));
    }
}
