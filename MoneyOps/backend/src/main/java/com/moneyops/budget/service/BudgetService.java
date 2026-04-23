package com.moneyops.budget.service;

import com.moneyops.budget.entity.Budget;
import com.moneyops.budget.repository.BudgetRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

@Service
public class BudgetService {

    @Autowired
    private BudgetRepository budgetRepository;

    public List<Budget> getBudgetsForMonth(String orgId, int year, int month) {
        return budgetRepository.findByOrgIdAndYearAndMonth(orgId, year, month);
    }

    public List<Budget> getBudgetsForYear(String orgId, int year) {
        return budgetRepository.findByOrgIdAndYear(orgId, year);
    }

    public List<Budget> getAllBudgets(String orgId) {
        return budgetRepository.findByOrgId(orgId);
    }

    public Budget createOrUpdateBudget(String orgId, int year, int month, String category, BigDecimal amount, String notes) {
        List<Budget> existing = budgetRepository.findByOrgIdAndYearAndMonth(orgId, year, month);
        Optional<Budget> matching = existing.stream()
            .filter(b -> b.getCategory().equalsIgnoreCase(category))
            .findFirst();

        if (matching.isPresent()) {
            Budget budget = matching.get();
            budget.setAmount(amount);
            budget.setNotes(notes);
            return budgetRepository.save(budget);
        } else {
            Budget budget = new Budget();
            budget.setOrgId(orgId);
            budget.setYear(year);
            budget.setMonth(month);
            budget.setCategory(category);
            budget.setAmount(amount);
            budget.setNotes(notes);
            return budgetRepository.save(budget);
        }
    }

    public void deleteBudget(String orgId, int year, int month, String category) {
        budgetRepository.deleteByOrgIdAndYearAndMonthAndCategory(orgId, year, month, category);
    }

    public Optional<Budget> getBudgetById(String id) {
        return budgetRepository.findById(id);
    }

    public void deleteBudgetById(String id) {
        budgetRepository.deleteById(id);
    }
}