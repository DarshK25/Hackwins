package com.moneyops.budget.repository;

import com.moneyops.budget.entity.Budget;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface BudgetRepository extends MongoRepository<Budget, String> {
    List<Budget> findByOrgIdAndYearAndMonth(String orgId, int year, int month);
    List<Budget> findByOrgIdAndYear(String orgId, int year);
    List<Budget> findByOrgId(String orgId);
    void deleteByOrgIdAndYearAndMonthAndCategory(String orgId, int year, int month, String category);
}