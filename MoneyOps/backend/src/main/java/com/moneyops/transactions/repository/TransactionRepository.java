package com.moneyops.transactions.repository;

import com.moneyops.transactions.entity.Transaction;
import com.moneyops.transactions.entity.TransactionType;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface TransactionRepository extends MongoRepository<Transaction, String> {

    Optional<Transaction> findByIdAndOrgIdAndDeletedAtIsNull(String id, String orgId);

    List<Transaction> findAllByOrgIdAndDeletedAtIsNull(String orgId);

    boolean existsByIdAndOrgIdAndDeletedAtIsNull(String id, String orgId);

    List<Transaction> findByOrgIdAndClientIdAndDeletedAtIsNull(String orgId, String clientId);
    
    List<Transaction> findByOrgIdAndInvoiceIdAndDeletedAtIsNull(String orgId, String invoiceId);

    List<Transaction> findByOrgIdAndTypeAndDeletedAtIsNull(String orgId, TransactionType type);

    List<Transaction> findByOrgIdAndTransactionDateBetweenAndDeletedAtIsNull(String orgId, LocalDate startDate, LocalDate endDate);

    @org.springframework.data.mongodb.repository.Aggregation(pipeline = {
        "{ $match: { 'orgId': ?0, 'type': ?1, 'deletedAt': null } }",
        "{ $group: { _id: null, total: { $sum: '$amount' } } }"
    })
    TotalResult getTotalByOrgIdAndType(String orgId, TransactionType type);

    record TotalResult(Double total) {}
}