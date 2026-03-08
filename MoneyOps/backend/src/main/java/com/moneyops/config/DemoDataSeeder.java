package com.moneyops.config;

import com.moneyops.clients.entity.Client;
import com.moneyops.clients.repository.ClientRepository;
import com.moneyops.invoices.entity.Invoice;
import com.moneyops.invoices.entity.InvoiceStatus;
import com.moneyops.invoices.repository.InvoiceRepository;
import com.moneyops.transactions.entity.Transaction;
import com.moneyops.transactions.entity.TransactionType;
import com.moneyops.transactions.repository.TransactionRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Component
public class DemoDataSeeder implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(DemoDataSeeder.class);

    // Use this exact org ID - it's the real one in the DB
    private static final String ORG_ID = "9d48137e-db96-3b9f-16d6-c3dbec18a4a5";

    // Inject all repositories
    @Autowired
    private ClientRepository clientRepository;
    @Autowired
    private InvoiceRepository invoiceRepository;
    @Autowired
    private TransactionRepository transactionRepository;

    private Client client1;
    private Client client2;
    private Client client3;
    private Client client4;

    @Override
    public void run(String... args) {
        UUID orgId = UUID.fromString(ORG_ID);
        // SKIP if data already exists for this org
        if (!transactionRepository.findAllByOrgId(orgId).isEmpty()) {
            log.info("[SEEDER] Data exists for demo org, skipping.");
            return;
        }

        try {
            seedClients();
            seedInvoices();
            seedTransactions();
            log.info("[SEEDER] ✅ Demo data seeded!");
        } catch (Exception e) {
            log.error("[SEEDER] ❌ Failed: " + e.getMessage());
            e.printStackTrace();
        }
    }

    private void seedClients() {
        UUID orgId = UUID.fromString(ORG_ID);

        Client c1 = new Client();
        c1.setOrgId(orgId);
        c1.setName("Acme Technologies Pvt Ltd");
        c1.setEmail("billing@acmetech.in");
        c1.setPhoneNumber("9876543210");
        client1 = clientRepository.save(c1);

        Client c2 = new Client();
        c2.setOrgId(orgId);
        c2.setName("BuildRight Constructions");
        c2.setEmail("accounts@buildright.co");
        c2.setPhoneNumber("9845021345");
        client2 = clientRepository.save(c2);

        Client c3 = new Client();
        c3.setOrgId(orgId);
        c3.setName("TechStart Solutions");
        c3.setEmail("finance@techstart.io");
        c3.setPhoneNumber("9967123456");
        client3 = clientRepository.save(c3);

        Client c4 = new Client();
        c4.setOrgId(orgId);
        c4.setName("GreenField Exports");
        c4.setEmail("gf.exports@gmail.com");
        c4.setPhoneNumber("9811234567");
        client4 = clientRepository.save(c4);
    }

    private void seedInvoices() {
        UUID orgId = UUID.fromString(ORG_ID);
        LocalDate today = LocalDate.now();

        // INV-001
        Invoice inv1 = new Invoice();
        inv1.setOrgId(orgId);
        inv1.setInvoiceNumber("INV-001");
        inv1.setClientId(UUID.fromString(client1.getId()));
        inv1.setClientName(client1.getName());
        inv1.setTotalAmount(new BigDecimal("85000"));
        inv1.setStatus(InvoiceStatus.PAID);
        inv1.setIssueDate(today.minusDays(60));
        inv1.setDueDate(today.minusDays(45));
        inv1.setNotes("Software Development Services Oct 2024");
        invoiceRepository.save(inv1);

        // INV-002
        Invoice inv2 = new Invoice();
        inv2.setOrgId(orgId);
        inv2.setInvoiceNumber("INV-002");
        inv2.setClientId(UUID.fromString(client2.getId()));
        inv2.setClientName(client2.getName());
        inv2.setTotalAmount(new BigDecimal("120000"));
        inv2.setStatus(InvoiceStatus.PAID);
        inv2.setIssueDate(today.minusDays(42));
        inv2.setDueDate(today.minusDays(21));
        inv2.setNotes("Architecture Consultation Q3 2024");
        invoiceRepository.save(inv2);

        // INV-003
        Invoice inv3 = new Invoice();
        inv3.setOrgId(orgId);
        inv3.setInvoiceNumber("INV-003");
        inv3.setClientId(UUID.fromString(client3.getId()));
        inv3.setClientName(client3.getName());
        inv3.setTotalAmount(new BigDecimal("45000"));
        inv3.setStatus(InvoiceStatus.PAID);
        inv3.setIssueDate(today.minusDays(35));
        inv3.setDueDate(today.minusDays(14));
        inv3.setNotes("UI/UX Design Services");
        invoiceRepository.save(inv3);

        // INV-004
        Invoice inv4 = new Invoice();
        inv4.setOrgId(orgId);
        inv4.setInvoiceNumber("INV-004");
        inv4.setClientId(UUID.fromString(client4.getId()));
        inv4.setClientName(client4.getName());
        inv4.setTotalAmount(new BigDecimal("67500"));
        inv4.setStatus(InvoiceStatus.OVERDUE);
        inv4.setIssueDate(today.minusDays(42));
        inv4.setDueDate(today.minusDays(14));
        inv4.setNotes("Export Documentation Services");
        invoiceRepository.save(inv4);

        // INV-005
        Invoice inv5 = new Invoice();
        inv5.setOrgId(orgId);
        inv5.setInvoiceNumber("INV-005");
        inv5.setClientId(UUID.fromString(client1.getId()));
        inv5.setClientName(client1.getName());
        inv5.setTotalAmount(new BigDecimal("95000"));
        inv5.setStatus(InvoiceStatus.OVERDUE);
        inv5.setIssueDate(today.minusDays(28));
        inv5.setDueDate(today.minusDays(7));
        inv5.setNotes("Software Development Services Nov 2024");
        invoiceRepository.save(inv5);

        // INV-006
        Invoice inv6 = new Invoice();
        inv6.setOrgId(orgId);
        inv6.setInvoiceNumber("INV-006");
        inv6.setClientId(UUID.fromString(client2.getId()));
        inv6.setClientName(client2.getName());
        inv6.setTotalAmount(new BigDecimal("55000"));
        inv6.setStatus(InvoiceStatus.SENT);
        inv6.setIssueDate(today.minusDays(10));
        inv6.setDueDate(today.plusDays(20));
        inv6.setNotes("Project Management Consultation");
        invoiceRepository.save(inv6);

        // INV-007
        Invoice inv7 = new Invoice();
        inv7.setOrgId(orgId);
        inv7.setInvoiceNumber("INV-007");
        inv7.setClientId(UUID.fromString(client3.getId()));
        inv7.setClientName(client3.getName());
        inv7.setTotalAmount(new BigDecimal("38000"));
        inv7.setStatus(InvoiceStatus.SENT);
        inv7.setIssueDate(today.minusDays(5));
        inv7.setDueDate(today.plusDays(25));
        inv7.setNotes("Monthly Retainer December 2024");
        invoiceRepository.save(inv7);

        // INV-008
        Invoice inv8 = new Invoice();
        inv8.setOrgId(orgId);
        inv8.setInvoiceNumber("INV-008");
        inv8.setClientId(UUID.fromString(client4.getId()));
        inv8.setClientName(client4.getName());
        inv8.setTotalAmount(new BigDecimal("72000"));
        inv8.setStatus(InvoiceStatus.DRAFT);
        inv8.setIssueDate(today);
        inv8.setDueDate(today.plusDays(30));
        inv8.setNotes("Annual Compliance Documentation");
        invoiceRepository.save(inv8);
    }

    private void seedTransactions() {
        UUID orgId = UUID.fromString(ORG_ID);
        LocalDate today = LocalDate.now();

        // TR-01
        Transaction t1 = new Transaction();
        t1.setOrgId(orgId);
        t1.setType(TransactionType.INCOME);
        t1.setAmount(new BigDecimal("85000"));
        t1.setDescription("Payment received - Acme Tech INV-001");
        t1.setCategory("REVENUE");
        t1.setTransactionDate(today.minusDays(40));
        transactionRepository.save(t1);

        // TR-02
        Transaction t2 = new Transaction();
        t2.setOrgId(orgId);
        t2.setType(TransactionType.INCOME);
        t2.setAmount(new BigDecimal("120000"));
        t2.setDescription("Payment received - BuildRight INV-002");
        t2.setCategory("REVENUE");
        t2.setTransactionDate(today.minusDays(21));
        transactionRepository.save(t2);

        // TR-03
        Transaction t3 = new Transaction();
        t3.setOrgId(orgId);
        t3.setType(TransactionType.INCOME);
        t3.setAmount(new BigDecimal("45000"));
        t3.setDescription("Payment received - TechStart INV-003");
        t3.setCategory("REVENUE");
        t3.setTransactionDate(today.minusDays(10));
        transactionRepository.save(t3);

        // TR-04
        Transaction t4 = new Transaction();
        t4.setOrgId(orgId);
        t4.setType(TransactionType.INCOME);
        t4.setAmount(new BigDecimal("15000"));
        t4.setDescription("Consulting bonus - Acme Tech");
        t4.setCategory("REVENUE");
        t4.setTransactionDate(today.minusDays(15));
        transactionRepository.save(t4);

        // TR-05
        Transaction t5 = new Transaction();
        t5.setOrgId(orgId);
        t5.setType(TransactionType.EXPENSE);
        t5.setAmount(new BigDecimal("25000"));
        t5.setDescription("AWS Cloud Infrastructure November");
        t5.setCategory("OPERATIONS");
        t5.setTransactionDate(today.minusDays(30));
        transactionRepository.save(t5);

        // TR-06
        Transaction t6 = new Transaction();
        t6.setOrgId(orgId);
        t6.setType(TransactionType.EXPENSE);
        t6.setAmount(new BigDecimal("18000"));
        t6.setDescription("Office Rent November 2024");
        t6.setCategory("RENT");
        t6.setTransactionDate(today.minusDays(32));
        transactionRepository.save(t6);

        // TR-07
        Transaction t7 = new Transaction();
        t7.setOrgId(orgId);
        t7.setType(TransactionType.EXPENSE);
        t7.setAmount(new BigDecimal("8500"));
        t7.setDescription("Team meals and refreshments");
        t7.setCategory("MEALS");
        t7.setTransactionDate(today.minusDays(25));
        transactionRepository.save(t7);

        // TR-08
        Transaction t8 = new Transaction();
        t8.setOrgId(orgId);
        t8.setType(TransactionType.EXPENSE);
        t8.setAmount(new BigDecimal("12000"));
        t8.setDescription("Legal retainer - Sharma Associates");
        t8.setCategory("LEGAL");
        t8.setTransactionDate(today.minusDays(20));
        transactionRepository.save(t8);

        // TR-09
        Transaction t9 = new Transaction();
        t9.setOrgId(orgId);
        t9.setType(TransactionType.EXPENSE);
        t9.setAmount(new BigDecimal("5500"));
        t9.setDescription("Software subscriptions Figma Notion");
        t9.setCategory("SOFTWARE");
        t9.setTransactionDate(today.minusDays(18));
        transactionRepository.save(t9);

        // TR-10
        Transaction t10 = new Transaction();
        t10.setOrgId(orgId);
        t10.setType(TransactionType.EXPENSE);
        t10.setAmount(new BigDecimal("9800"));
        t10.setDescription("Travel - Client meetings Mumbai");
        t10.setCategory("TRAVEL");
        t10.setTransactionDate(today.minusDays(14));
        transactionRepository.save(t10);

        // TR-11
        Transaction t11 = new Transaction();
        t11.setOrgId(orgId);
        t11.setType(TransactionType.EXPENSE);
        t11.setAmount(new BigDecimal("22000"));
        t11.setDescription("Freelancer payment UI Design");
        t11.setCategory("CONTRACTOR");
        t11.setTransactionDate(today.minusDays(8));
        transactionRepository.save(t11);

        // TR-12
        Transaction t12 = new Transaction();
        t12.setOrgId(orgId);
        t12.setType(TransactionType.EXPENSE);
        t12.setAmount(new BigDecimal("3200"));
        t12.setDescription("Office supplies and stationery");
        t12.setCategory("OFFICE"); // Assume OFFICE since it was cut off in prompt "category="<span..."
        t12.setTransactionDate(today.minusDays(4));
        transactionRepository.save(t12);
    }
}
