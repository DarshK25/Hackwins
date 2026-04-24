package com.moneyops.compliance;

import com.moneyops.shared.utils.OrgContext;
import com.moneyops.compliance.dto.ComplianceSummaryDTO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;

@RestController
@RequestMapping("/api")
public class ComplianceController {

    @Autowired
    private ComplianceService complianceService;
    
    @Autowired
    private CompliancePdfService compliancePdfService;

    @GetMapping("/compliance/status")
    public ResponseEntity<ComplianceService.ComplianceStatusResponse> getComplianceStatus(
            @RequestParam(required = false) String businessId,
            @RequestParam(required = false) String userId) {
        String orgId = OrgContext.getOrgId();
        return ResponseEntity.ok(complianceService.getComplianceStatus(orgId, businessId, userId));
    }

    @GetMapping("/deadlines")
    public ResponseEntity<ComplianceService.DeadlinesResponse> getDeadlines(@RequestParam(required = false) String businessId) {
        return ResponseEntity.ok(complianceService.getDeadlines(businessId));
    }

    @PostMapping("/tds/calc")
    public ResponseEntity<ComplianceService.TdsCalculationResponse> calculateTds(@RequestBody ComplianceService.TdsCalcRequest request) {
        return ResponseEntity.ok(complianceService.calculateTds(request));
    }

    @GetMapping("/compliance/summary")
    public ResponseEntity<ComplianceSummaryDTO> getComplianceSummary(@RequestParam(required = false) String orgId) {
        String resolvedOrgId = OrgContext.getOrgId() != null ? OrgContext.getOrgId() : orgId;
        if (resolvedOrgId == null) return ResponseEntity.status(org.springframework.http.HttpStatus.UNAUTHORIZED).build();
        return ResponseEntity.ok(complianceService.getComplianceSummary(resolvedOrgId));
    }

    public static class ComplianceExportRequest {
        public String orgId;
        public String reportType;
        public LocalDate dateFrom;
        public LocalDate dateTo;
    }

    @PostMapping("/compliance/export/pdf")
    public ResponseEntity<ByteArrayResource> exportCompliancePdf(@RequestBody ComplianceExportRequest request) {
        String resolvedOrgId = OrgContext.getOrgId() != null ? OrgContext.getOrgId() : request.orgId;
        if (resolvedOrgId == null) return ResponseEntity.status(org.springframework.http.HttpStatus.UNAUTHORIZED).build();

        byte[] pdf = compliancePdfService.generateCompliancePdf(resolvedOrgId, request.reportType, request.dateFrom, request.dateTo);
        ByteArrayResource resource = new ByteArrayResource(pdf);

        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_PDF)
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"compliance-report.pdf\"")
                .contentLength(pdf.length)
                .body(resource);
    }
}
