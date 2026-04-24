package com.moneyops.expenses.controller;

import com.moneyops.expenses.dto.ExpenseDTO;
import com.moneyops.expenses.dto.ExpenseSummaryDTO;
import com.moneyops.expenses.service.ExpenseService;
import com.moneyops.shared.dto.ApiResponse;
import com.moneyops.shared.dto.PageResponse;
import com.moneyops.shared.utils.OrgContext;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
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
import org.springframework.web.bind.annotation.RequestHeader;

import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api/expenses")
@RequiredArgsConstructor
public class ExpenseController {

    private final ExpenseService expenseService;

    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<ExpenseDTO>>> getExpenses(
            @RequestParam(required = false) String orgId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateFrom,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateTo
    ) {
        return ResponseEntity.ok(ApiResponse.success(
                expenseService.getExpenses(resolveOrgId(orgId), page, size, category, dateFrom, dateTo)
        ));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<ExpenseDTO>> createExpense(
            @RequestBody ExpenseDTO request,
            @RequestHeader(value = "X-User-Id", required = false) String userIdHeader) {
        String userId = OrgContext.getUserId();
        if (userId == null || userId.isBlank()) {
            userId = userIdHeader;
        }
        ExpenseDTO created = expenseService.createExpense(request, resolveOrgId(request.getOrgId()), userId);
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.success("Expense recorded successfully", created));
    }

    @PutMapping("/{id}")
    public ResponseEntity<ApiResponse<ExpenseDTO>> updateExpense(
            @PathVariable String id,
            @RequestBody ExpenseDTO request,
            @RequestParam(required = false) String orgId
    ) {
        return ResponseEntity.ok(ApiResponse.success(
                "Expense updated successfully",
                expenseService.updateExpense(id, request, resolveOrgId(orgId != null ? orgId : request.getOrgId()))
        ));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<ApiResponse<Void>> deleteExpense(
            @PathVariable String id,
            @RequestParam(required = false) String orgId
    ) {
        expenseService.deleteExpense(id, resolveOrgId(orgId));
        return ResponseEntity.ok(ApiResponse.success("Expense deleted successfully", null));
    }

    @GetMapping("/summary")
    public ResponseEntity<ApiResponse<ExpenseSummaryDTO>> getSummary(
            @RequestParam(required = false) String orgId,
            @RequestParam(defaultValue = "monthly") String period,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateFrom,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateTo
    ) {
        return ResponseEntity.ok(ApiResponse.success(
                expenseService.getSummary(resolveOrgId(orgId), period, category, dateFrom, dateTo)
        ));
    }

    @GetMapping("/categories")
    public ResponseEntity<ApiResponse<List<String>>> getCategories() {
        return ResponseEntity.ok(ApiResponse.success(expenseService.getAvailableCategories()));
    }

    private String resolveOrgId(String fallbackOrgId) {
        return OrgContext.getOrgId() != null ? OrgContext.getOrgId() : fallbackOrgId;
    }
}
