package com.moneyops.budgets.controller;

import com.moneyops.budgets.dto.BudgetAnalysisDTO;
import com.moneyops.budgets.dto.BudgetDTO;
import com.moneyops.budgets.service.BudgetService;
import com.moneyops.shared.utils.OrgContext;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/budgets")
@RequiredArgsConstructor
public class BudgetController {

    private final BudgetService budgetService;

    @PostMapping
    public ResponseEntity<BudgetDTO> createBudget(@RequestBody BudgetDTO request) {
        String orgId = resolveOrgId(request.getOrgId());
        if (orgId == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }

        BudgetDTO created = budgetService.createBudget(request, orgId, OrgContext.getUserId());
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @GetMapping
    public ResponseEntity<List<BudgetDTO>> listBudgets(@RequestParam(required = false) String orgId) {
        String resolvedOrgId = resolveOrgId(orgId);
        if (resolvedOrgId == null) {
            return ResponseEntity.ok(List.of());
        }

        return ResponseEntity.ok(budgetService.listBudgets(resolvedOrgId));
    }

    @GetMapping("/{id}")
    public ResponseEntity<BudgetDTO> getBudget(@PathVariable String id,
                                               @RequestParam(required = false) String orgId) {
        String resolvedOrgId = resolveOrgId(orgId);
        if (resolvedOrgId == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }

        return ResponseEntity.ok(budgetService.getBudgetById(id, resolvedOrgId));
    }

    @PutMapping("/{id}")
    public ResponseEntity<BudgetDTO> updateBudget(@PathVariable String id,
                                                  @RequestBody BudgetDTO request,
                                                  @RequestParam(required = false) String orgId) {
        String resolvedOrgId = resolveOrgId(orgId != null ? orgId : request.getOrgId());
        if (resolvedOrgId == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }

        return ResponseEntity.ok(budgetService.updateBudget(id, request, resolvedOrgId, OrgContext.getUserId()));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteBudget(@PathVariable String id,
                                             @RequestParam(required = false) String orgId) {
        String resolvedOrgId = resolveOrgId(orgId);
        if (resolvedOrgId == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }

        budgetService.deleteBudget(id, resolvedOrgId);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/{id}/analysis")
    public ResponseEntity<BudgetAnalysisDTO> getBudgetAnalysis(@PathVariable String id,
                                                               @RequestParam(required = false) String orgId) {
        String resolvedOrgId = resolveOrgId(orgId);
        if (resolvedOrgId == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }

        return ResponseEntity.ok(budgetService.getBudgetAnalysis(id, resolvedOrgId));
    }

    private String resolveOrgId(String fallbackOrgId) {
        return OrgContext.getOrgId() != null ? OrgContext.getOrgId() : fallbackOrgId;
    }
}
