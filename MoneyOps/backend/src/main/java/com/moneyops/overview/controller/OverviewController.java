package com.moneyops.overview.controller;

import com.moneyops.overview.dto.OverviewMetricsDTO;
import com.moneyops.overview.service.OverviewReportService;
import com.moneyops.shared.utils.OrgContext;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/overview")
@RequiredArgsConstructor
public class OverviewController {

    private final OverviewReportService overviewReportService;

    @GetMapping("/metrics")
    public ResponseEntity<OverviewMetricsDTO> getMetrics(
            @RequestParam(required = false) String orgId,
            @RequestParam(defaultValue = "monthly") String period
    ) {
        String resolvedOrgId = resolveOrgId(orgId);
        return ResponseEntity.ok(overviewReportService.getMetrics(resolvedOrgId, period));
    }

    @GetMapping(value = "/export/pdf", produces = MediaType.APPLICATION_PDF_VALUE)
    public ResponseEntity<ByteArrayResource> exportOverviewPdf(
            @RequestParam(required = false) String orgId,
            @RequestParam(defaultValue = "monthly") String period
    ) {
        String resolvedOrgId = resolveOrgId(orgId);
        byte[] pdf = overviewReportService.generateOverviewPdf(resolvedOrgId, period);
        String filename = overviewReportService.buildFilename(resolvedOrgId, period);

        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_PDF)
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
                .contentLength(pdf.length)
                .body(new ByteArrayResource(pdf));
    }

    private String resolveOrgId(String fallbackOrgId) {
        return OrgContext.getOrgId() != null ? OrgContext.getOrgId() : fallbackOrgId;
    }
}
