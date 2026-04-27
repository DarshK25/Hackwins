package com.moneyops.compliance;

import com.moneyops.shared.utils.OrgContext;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
public class ComplianceController {

    @Autowired
    private ComplianceService complianceService;

    @GetMapping("/compliance/status")
    public ResponseEntity<ComplianceService.ComplianceStatusResponse> getComplianceStatus(
            @RequestParam(required = false) String businessId,
            @RequestParam(required = false) String userId) {
        String orgId = OrgContext.getOrgId();
        return ResponseEntity.ok(complianceService.getComplianceStatus(orgId, businessId, userId));
    }

    @GetMapping("/compliance/gst/summary")
    public ResponseEntity<ComplianceService.GstSummaryResponse> getGstSummary(
            @RequestParam(required = false) String period) {
        String orgId = OrgContext.getOrgId();
        return ResponseEntity.ok(complianceService.getGstSummary(orgId, period));
    }

    @GetMapping("/compliance/tds/obligations")
    public ResponseEntity<ComplianceService.TdsObligationsResponse> getTdsObligations(
            @RequestParam(required = false) String fy) {
        String orgId = OrgContext.getOrgId();
        return ResponseEntity.ok(complianceService.getTdsObligations(orgId, fy));
    }

    @GetMapping("/compliance/audit/readiness")
    public ResponseEntity<ComplianceService.AuditReadinessResponse> getAuditReadiness() {
        String orgId = OrgContext.getOrgId();
        return ResponseEntity.ok(complianceService.getAuditReadiness(orgId));
    }

    @GetMapping("/compliance/issues")
    public ResponseEntity<?> getComplianceIssues(@RequestParam(required = false) String period) {
        String orgId = OrgContext.getOrgId();
        return ResponseEntity.ok(complianceService.getComplianceIssues(orgId, period));
    }

    @GetMapping("/deadlines")
    public ResponseEntity<ComplianceService.DeadlinesResponse> getDeadlines(@RequestParam(required = false) String businessId) {
        String orgId = OrgContext.getOrgId();
        return ResponseEntity.ok(complianceService.getDeadlines(orgId, businessId));
    }

    @PostMapping("/tds/calc")
    public ResponseEntity<ComplianceService.TdsCalculationResponse> calculateTds(@RequestBody ComplianceService.TdsCalcRequest request) {
        return ResponseEntity.ok(complianceService.calculateTds(request));
    }
}
