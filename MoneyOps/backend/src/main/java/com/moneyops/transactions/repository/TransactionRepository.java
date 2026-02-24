package com.moneyops.transactions.repository;

import com.moneyops.transactions.entity.Transaction;
import com.moneyops.transactions.entity.TransactionType;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface TransactionRepository extends MongoRepository<Transaction, UUID> {

    Optional<Transaction> findByIdAndOrgId(UUID id, UUID orgId);

    List<Transaction> findAllByOrgId(UUID orgId);

    boolean existsByIdAndOrgId(UUID id, UUID orgId);

    List<Transaction> findByOrgIdAndClientId(UUID orgId, UUID clientId);

    List<Transaction> findByOrgIdAndType(UUID orgId, TransactionType type);

    List<Transaction> findByOrgIdAndTransactionDateBetween(UUID orgId, LocalDate startDate, LocalDate endDate);

    void deleteByIdAndOrgId(UUID id, UUID orgId);

    @org.springframework.data.mongodb.repository.Aggregation(pipeline = {
        "{ $match: { 'orgId': ?0, 'type': ?1 } }",
        "{ $group: { _id: null, total: { $sum: '$amount' } } }"
    })
    TotalResult getTotalByOrgIdAndType(UUID orgId, TransactionType type);

    record TotalResult(Double total) {}
}