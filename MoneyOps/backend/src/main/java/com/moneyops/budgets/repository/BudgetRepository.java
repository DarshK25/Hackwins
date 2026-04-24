package com.moneyops.budgets.repository;

import com.moneyops.budgets.entity.Budget;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface BudgetRepository extends MongoRepository<Budget, String> {

    Optional<Budget> findByIdAndOrgIdAndDeletedAtIsNull(String id, String orgId);

    List<Budget> findAllByOrgIdAndDeletedAtIsNullOrderByCreatedAtDesc(String orgId);
}
