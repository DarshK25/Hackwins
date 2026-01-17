// src/main/java/com/ledgertalk/invoices/repository/InvoiceItemRepository.java
package com.ledgertalk.invoices.repository;

import com.ledgertalk.invoices.entity.InvoiceItem;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface InvoiceItemRepository extends JpaRepository<InvoiceItem, UUID> {

    List<InvoiceItem> findByInvoiceId(UUID invoiceId);

    void deleteByInvoiceId(UUID invoiceId);
}