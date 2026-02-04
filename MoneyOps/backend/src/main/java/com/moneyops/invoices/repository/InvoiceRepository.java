// src/main/java/com/moneyops/invoices/repository/InvoiceRepository.java
package com.moneyops.invoices.repository;

import com.moneyops.invoices.entity.Invoice;
import com.moneyops.invoices.entity.InvoiceStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface InvoiceRepository extends JpaRepository<Invoice, UUID> {

    Optional<Invoice> findByIdAndOrgId(UUID id, UUID orgId);

    List<Invoice> findAllByOrgId(UUID orgId);

    void deleteByIdAndOrgId(UUID id, UUID orgId);

    boolean existsByIdAndOrgId(UUID id, UUID orgId);

    @Query("SELECT i FROM Invoice i WHERE i.orgId = :orgId AND i.invoiceNumber = :invoiceNumber")
    Optional<Invoice> findByOrgIdAndInvoiceNumber(@Param("orgId") UUID orgId, @Param("invoiceNumber") String invoiceNumber);

    @Query("SELECT i FROM Invoice i WHERE i.orgId = :orgId AND i.status = :status")
    List<Invoice> findByOrgIdAndStatus(@Param("orgId") UUID orgId, @Param("status") InvoiceStatus status);

    @Query("SELECT i FROM Invoice i WHERE i.orgId = :orgId AND i.dueDate < :date AND i.status NOT IN ('PAID')")
    List<Invoice> findOverdueByOrgId(@Param("orgId") UUID orgId, @Param("date") LocalDate date);

    // Search with filters
    @Query("SELECT i FROM Invoice i WHERE i.orgId = :orgId " +
           "AND (:clientId IS NULL OR i.clientId = :clientId) " +
           "AND (:status IS NULL OR i.status = :status) " +
           "AND (:startDate IS NULL OR i.issueDate >= :startDate) " +
           "AND (:endDate IS NULL OR i.issueDate <= :endDate)")
    List<Invoice> searchByOrgIdWithFilters(@Param("orgId") UUID orgId,
                                           @Param("clientId") UUID clientId,
                                           @Param("status") InvoiceStatus status,
                                           @Param("startDate") LocalDate startDate,
                                           @Param("endDate") LocalDate endDate);
}