package com.moneyops.budgets.service;

import com.moneyops.budgets.dto.BudgetAnalysisDTO;
import com.moneyops.budgets.dto.BudgetDTO;
import com.moneyops.budgets.entity.Budget;
import com.moneyops.budgets.repository.BudgetRepository;
import com.moneyops.transactions.entity.Transaction;
import com.moneyops.transactions.entity.TransactionType;
import com.moneyops.transactions.repository.TransactionRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class BudgetServiceTest {

    @Mock
    private BudgetRepository budgetRepository;

    @Mock
    private TransactionRepository transactionRepository;

    @InjectMocks
    private BudgetService budgetService;

    @Test
    void createBudgetDerivesSummaryFieldsFromExpenseTransactions() {
        BudgetDTO request = new BudgetDTO();
        request.setName("April Budget");
        request.setPeriod("MONTHLY");
        request.setStartDate(LocalDate.of(2026, 4, 1));

        BudgetDTO.CategoryDTO category = new BudgetDTO.CategoryDTO();
        category.setName("Marketing");
        category.setLimit(BigDecimal.valueOf(1000));
        request.setCategories(List.of(category));

        when(budgetRepository.save(any(Budget.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(transactionRepository.findByOrgIdAndTypeAndTransactionDateBetweenAndDeletedAtIsNull(
                any(),
                any(),
                any(),
                any()
        )).thenReturn(List.of());

        BudgetDTO created = budgetService.createBudget(request, "org-1", "user-1");

        assertNotNull(created.getId());
        assertEquals("org-1", created.getOrgId());
        assertEquals(LocalDate.of(2026, 4, 30), created.getEndDate());
        assertEquals(BigDecimal.valueOf(1000), created.getTotalBudget());
    }

    @Test
    void getBudgetAnalysisAggregatesMatchingTransactionsAndFlagsThresholds() {
        Budget budget = new Budget();
        budget.setId("budget-1");
        budget.setOrgId("org-1");
        budget.setName("Q2 Budget");
        budget.setPeriod("QUARTERLY");
        budget.setStartDate(LocalDate.of(2026, 4, 1));
        budget.setEndDate(LocalDate.of(2026, 6, 30));

        Budget.BudgetCategory marketing = new Budget.BudgetCategory();
        marketing.setName("Marketing");
        marketing.setLimit(BigDecimal.valueOf(100));

        Budget.BudgetCategory operations = new Budget.BudgetCategory();
        operations.setName("Operations");
        operations.setLimit(BigDecimal.valueOf(50));

        budget.setCategories(List.of(marketing, operations));

        Transaction marketingTxn = new Transaction();
        marketingTxn.setId("txn-1");
        marketingTxn.setType(TransactionType.EXPENSE);
        marketingTxn.setTransactionDate(LocalDate.of(2026, 4, 15));
        marketingTxn.setCategory("marketing");
        marketingTxn.setDescription("Ad spend");
        marketingTxn.setAmount(BigDecimal.valueOf(90));

        Transaction operationsTxn = new Transaction();
        operationsTxn.setId("txn-2");
        operationsTxn.setType(TransactionType.EXPENSE);
        operationsTxn.setTransactionDate(LocalDate.of(2026, 4, 18));
        operationsTxn.setCategory("Operations");
        operationsTxn.setDescription("Tools");
        operationsTxn.setAmount(BigDecimal.valueOf(60));

        Transaction ignoredTxn = new Transaction();
        ignoredTxn.setId("txn-3");
        ignoredTxn.setType(TransactionType.EXPENSE);
        ignoredTxn.setTransactionDate(LocalDate.of(2026, 4, 20));
        ignoredTxn.setCategory("Travel");
        ignoredTxn.setDescription("Taxi");
        ignoredTxn.setAmount(BigDecimal.valueOf(25));

        when(budgetRepository.findByIdAndOrgIdAndDeletedAtIsNull("budget-1", "org-1")).thenReturn(Optional.of(budget));
        when(transactionRepository.findByOrgIdAndTypeAndTransactionDateBetweenAndDeletedAtIsNull(
                "org-1",
                TransactionType.EXPENSE,
                LocalDate.of(2026, 4, 1),
                LocalDate.of(2026, 6, 30)
        )).thenReturn(List.of(marketingTxn, operationsTxn, ignoredTxn));

        BudgetAnalysisDTO analysis = budgetService.getBudgetAnalysis("budget-1", "org-1");

        assertEquals(BigDecimal.valueOf(150), analysis.getTotalBudget());
        assertEquals(BigDecimal.valueOf(150), analysis.getTotalSpent());
        assertEquals(BigDecimal.ZERO.setScale(0), analysis.getRemaining());
        assertEquals(2, analysis.getCategories().size());

        BudgetAnalysisDTO.CategoryAnalysisDTO marketingResult = analysis.getCategories().get(0);
        BudgetAnalysisDTO.CategoryAnalysisDTO operationsResult = analysis.getCategories().get(1);

        assertEquals("WARNING", marketingResult.getStatus());
        assertEquals(BigDecimal.valueOf(90), marketingResult.getActual());
        assertEquals(1, marketingResult.getTransactions().size());

        assertEquals("EXCEEDED", operationsResult.getStatus());
        assertEquals(BigDecimal.valueOf(60), operationsResult.getActual());
        assertEquals(1, operationsResult.getTransactions().size());

        verify(budgetRepository).findByIdAndOrgIdAndDeletedAtIsNull("budget-1", "org-1");
    }
}
