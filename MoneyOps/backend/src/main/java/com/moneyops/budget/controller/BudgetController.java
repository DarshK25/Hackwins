package com.moneyops.budget.controller;

import com.moneyops.budget.entity.Budget;
import com.moneyops.budget.service.BudgetService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/budgets")
public class BudgetController {

    @Autowired
    private BudgetService budgetService;

    @GetMapping
    public ResponseEntity<List<Budget>> getBudgets(
            @RequestParam String orgId,
            @RequestParam(required = false) Integer year,
            @RequestParam(required = false) Integer month) {
        List<Budget> budgets;
        if (year != null && month != null) {
            budgets = budgetService.getBudgetsForMonth(orgId, year, month);
        } else if (year != null) {
            budgets = budgetService.getBudgetsForYear(orgId, year);
        } else {
            budgets = budgetService.getAllBudgets(orgId);
        }
        return ResponseEntity.ok(budgets);
    }

    @PostMapping
    public ResponseEntity<Budget> createOrUpdateBudget(@RequestBody Map<String, Object> payload) {
        String orgId = (String) payload.get("orgId");
        int year = ((Number) payload.get("year")).intValue();
        int month = ((Number) payload.get("month")).intValue();
        String category = (String) payload.get("category");
        BigDecimal amount = new BigDecimal(payload.get("amount").toString());
        String notes = (String) payload.getOrDefault("notes", "");

        Budget budget = budgetService.createOrUpdateBudget(orgId, year, month, category, amount, notes);
        return ResponseEntity.ok(budget);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteBudget(@PathVariable String id) {
        budgetService.deleteBudgetById(id);
        return ResponseEntity.noContent().build();
    }

    @DeleteMapping
    public ResponseEntity<Void> deleteBudgetByCategory(@RequestParam String orgId,
                                                        @RequestParam int year,
                                                        @RequestParam int month,
                                                        @RequestParam String category) {
        budgetService.deleteBudget(orgId, year, month, category);
        return ResponseEntity.noContent().build();
    }
}