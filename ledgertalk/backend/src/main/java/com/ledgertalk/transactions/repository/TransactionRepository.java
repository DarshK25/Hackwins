// src/main/java/com/ledgertalk/transactions/repository/TransactionRepository.java
package com.ledgertalk.transactions.repository;

import com.ledgertalk.transactions.entity.Transaction;
import com.ledgertalk.transactions.entity.TransactionType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface TransactionRepository extends JpaRepository<Transaction, UUID> {

    Optional<Transaction> findByIdAndOrgId(UUID id, UUID orgId);

    List<Transaction> findAllByOrgId(UUID orgId);

    void deleteByIdAndOrgId(UUID id, UUID orgId);

    boolean existsByIdAndOrgId(UUID id, UUID orgId);

    @Query("SELECT t FROM Transaction t WHERE t.orgId = :orgId AND t.clientId = :clientId")
    List<Transaction> findByOrgIdAndClientId(@Param("orgId") UUID orgId, @Param("clientId") UUID clientId);

    @Query("SELECT t FROM Transaction t WHERE t.orgId = :orgId AND t.transactionDate BETWEEN :startDate AND :endDate")
    List<Transaction> findByOrgIdAndDateRange(@Param("orgId") UUID orgId,
                                              @Param("startDate") LocalDate startDate,
                                              @Param("endDate") LocalDate endDate);

    @Query("SELECT SUM(t.amount) FROM Transaction t WHERE t.orgId = :orgId AND t.type = :type")
    BigDecimal getTotalByOrgIdAndType(@Param("orgId") UUID orgId, @Param("type") TransactionType type);

    // Search with filters
    @Query("SELECT t FROM Transaction t WHERE t.orgId = :orgId " +
           "AND (:clientId IS NULL OR t.clientId = :clientId) " +
           "AND (:type IS NULL OR t.type = :type) " +
           "AND (:category IS NULL OR t.category = :category) " +
           "AND (:startDate IS NULL OR t.transactionDate >= :startDate) " +
           "AND (:endDate IS NULL OR t.transactionDate <= :endDate)")
    List<Transaction> searchByOrgIdWithFilters(@Param("orgId") UUID orgId,
                                               @Param("clientId") UUID clientId,
                                               @Param("type") TransactionType type,
                                               @Param("category") String category,
                                               @Param("startDate") LocalDate startDate,
                                               @Param("endDate") LocalDate endDate);
}