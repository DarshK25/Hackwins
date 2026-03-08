package com.moneyops.intelligence;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/finance-intelligence")
public class FinanceIntelligenceController {

    @Autowired
    private FinanceIntelligenceService financeIntelligenceService;

    @GetMapping("/metrics")
    public ResponseEntity<FinanceIntelligenceService.MetricsDTO> getMetrics(@RequestParam Long businessId) {
        return ResponseEntity.ok(financeIntelligenceService.getMetrics(businessId));
    }

    @GetMapping("/budget")
    public ResponseEntity<FinanceIntelligenceService.BudgetDTO> getBudget(@RequestParam Long businessId) {
        return ResponseEntity.ok(financeIntelligenceService.getBudget(businessId));
    }

    @GetMapping("/insights")
    public ResponseEntity<FinanceIntelligenceService.InsightsDTO> getInsights(@RequestParam Long businessId) {
        return ResponseEntity.ok(financeIntelligenceService.getInsights(businessId));
    }

    @GetMapping("/ledger")
    public ResponseEntity<FinanceIntelligenceService.LedgerDTO> getLedger(
            @RequestParam Long businessId,
            @RequestParam(defaultValue = "20") int limit) {
        return ResponseEntity.ok(financeIntelligenceService.getLedger(businessId, limit));
    }
}
