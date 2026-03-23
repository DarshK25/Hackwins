package com.moneyops.invoices.repository;

import com.moneyops.invoices.entity.Invoice;
import com.moneyops.invoices.entity.InvoiceStatus;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface InvoiceRepository extends MongoRepository<Invoice, String> {

    Optional<Invoice> findByIdAndOrgIdAndDeletedAtIsNull(String id, String orgId);

    List<Invoice> findAllByOrgIdAndDeletedAtIsNull(String orgId);

    boolean existsByIdAndOrgIdAndDeletedAtIsNull(String id, String orgId);

    Optional<Invoice> findByOrgIdAndInvoiceNumberAndDeletedAtIsNull(String orgId, String invoiceNumber);

    List<Invoice> findByOrgIdAndStatusAndDeletedAtIsNull(String orgId, InvoiceStatus status);

    List<Invoice> findAllByOrgIdAndClientIdAndDeletedAtIsNull(String orgId, String clientId);

    @org.springframework.data.mongodb.repository.Query("{ 'orgId': ?0, 'deletedAt': null, 'dueDate': { $lt: ?1 }, 'status': { $nin: ['PAID', 'DRAFT'] } }")
    List<Invoice> findOverdueByOrgId(String orgId, java.time.LocalDate now);
}