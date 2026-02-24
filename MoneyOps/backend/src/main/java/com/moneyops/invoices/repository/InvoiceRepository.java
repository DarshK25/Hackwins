package com.moneyops.invoices.repository;

import com.moneyops.invoices.entity.Invoice;
import com.moneyops.invoices.entity.InvoiceStatus;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface InvoiceRepository extends MongoRepository<Invoice, String> {

    Optional<Invoice> findByIdAndOrgId(String id, UUID orgId);

    List<Invoice> findAllByOrgId(UUID orgId);

    boolean existsByIdAndOrgId(String id, UUID orgId);

    Optional<Invoice> findByOrgIdAndInvoiceNumber(UUID orgId, String invoiceNumber);

    List<Invoice> findByOrgIdAndStatus(UUID orgId, InvoiceStatus status);

    List<Invoice> findAllByOrgIdAndClientId(UUID orgId, UUID clientId);

    void deleteByIdAndOrgId(String id, UUID orgId);

    @org.springframework.data.mongodb.repository.Query("{ 'orgId': ?0, 'dueDate': { $lt: ?1 }, 'status': { $nin: ['PAID', 'DRAFT'] } }")
    List<Invoice> findOverdueByOrgId(UUID orgId, java.time.LocalDate now);
}