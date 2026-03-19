package com.moneyops.config;

import com.moneyops.clients.entity.Client;
import com.moneyops.clients.repository.ClientRepository;
import com.moneyops.invoices.entity.Invoice;
import com.moneyops.invoices.entity.InvoiceStatus;
import com.moneyops.invoices.repository.InvoiceRepository;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.transactions.entity.Transaction;
import com.moneyops.transactions.entity.TransactionType;
import com.moneyops.transactions.repository.TransactionRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

@Component
public class DemoDataSeeder implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(DemoDataSeeder.class);

    @Autowired
    private ClientRepository clientRepository;
    @Autowired
    private InvoiceRepository invoiceRepository;
    @Autowired
    private TransactionRepository transactionRepository;
    @Autowired
    private MongoTemplate mongoTemplate;

    private Client client1, client2, client3, client4;

    @Override
    public void run(String... args) {
        log.info("[SEEDER] Seeder is disabled as per user request to start accounts from zero.");
        return;
        
        // log.info("[SEEDER] Starting robust demo data seeding via MongoTemplate...");
        
        List<BusinessOrganization> allOrgs;
        try {
            // Use MongoTemplate directly to avoid any potential repository mapping quirks
            allOrgs = mongoTemplate.findAll(BusinessOrganization.class);
            log.info("[SEEDER] Found {} organizations via MongoTemplate.", allOrgs.size());
        } catch (Exception e) {
            log.error("[SEEDER] ❌ Failed to fetch organizations via MongoTemplate: {}", e.getMessage());
            return;
        }

        if (allOrgs.isEmpty()) {
            log.warn("[SEEDER] No organizations found. If this is a fresh DB, the seeder has nothing to do yet.");
            return;
        }

        for (BusinessOrganization org : allOrgs) {
            UUID orgId = org.getId();
            log.info("[SEEDER] Checking Org ID: {} ({}) createdBy: {}", orgId, org.getLegalName(), org.getCreatedBy());
            String orgName = org.getLegalName() != null ? org.getLegalName() : "Unknown Org (" + orgId + ")";
            
            // Re-check for existing transactions using MongoTemplate to be super safe
            boolean hasData = transactionRepository.findAllByOrgId(orgId).size() > 0;
            
            if (hasData) {
                log.info("[SEEDER] Org '{}' already has transaction data, skipping.", orgName);
                continue;
            }

            try {
                log.info("[SEEDER] Seeding demo data for org '{}' ({})", orgName, orgId);
                seedClients(orgId);
                seedInvoices(orgId);
                seedTransactions(orgId);
                log.info("[SEEDER] ✅ Successfully seeded org '{}'!", orgName);
            } catch (Exception e) {
                log.error("[SEEDER] ❌ Failed to seed org '{}': {}", orgName, e.getMessage());
            }
        }
    }

    private void seedClients(UUID orgId) {
        Client c1 = new Client();
        c1.setOrgId(orgId);
        c1.setName("Acme Technologies Pvt Ltd");
        c1.setEmail("billing@acmetech.in");
        c1.setPhoneNumber("9876543210");
        c1.setCompany("Acme Technologies");
        c1.setStatus(Client.Status.ACTIVE);
        client1 = mongoTemplate.save(c1);

        Client c2 = new Client();
        c2.setOrgId(orgId);
        c2.setName("BuildRight Constructions");
        c2.setEmail("accounts@buildright.co");
        c2.setPhoneNumber("9845021345");
        c2.setCompany("BuildRight Corp");
        c2.setStatus(Client.Status.ACTIVE);
        client2 = mongoTemplate.save(c2);

        Client c3 = new Client();
        c3.setOrgId(orgId);
        c3.setName("TechStart Solutions");
        c3.setEmail("finance@techstart.io");
        c3.setPhoneNumber("9967123456");
        c3.setCompany("TechStart Solutions");
        c3.setStatus(Client.Status.ACTIVE);
        client3 = mongoTemplate.save(c3);

        Client c4 = new Client();
        c4.setOrgId(orgId);
        c4.setName("GreenField Exports");
        c4.setEmail("gf.exports@gmail.com");
        c4.setPhoneNumber("9811234567");
        c4.setCompany("GreenField Exports Ltd");
        c4.setStatus(Client.Status.ACTIVE);
        client4 = mongoTemplate.save(c4);
    }

    private void seedInvoices(UUID orgId) {
        LocalDate today = LocalDate.now();
        saveInvoice(orgId, "INV-001", client1, "85000", InvoiceStatus.PAID, today.minusDays(60), today.minusDays(45));
        saveInvoice(orgId, "INV-002", client2, "120000", InvoiceStatus.PAID, today.minusDays(42), today.minusDays(21));
        saveInvoice(orgId, "INV-003", client3, "45000", InvoiceStatus.PAID, today.minusDays(35), today.minusDays(14));
        saveInvoice(orgId, "INV-004", client4, "67500", InvoiceStatus.OVERDUE, today.minusDays(42), today.minusDays(14));
        saveInvoice(orgId, "INV-005", client1, "95000", InvoiceStatus.OVERDUE, today.minusDays(28), today.minusDays(7));
        saveInvoice(orgId, "INV-006", client2, "55000", InvoiceStatus.SENT, today.minusDays(10), today.plusDays(20));
        saveInvoice(orgId, "INV-007", client3, "38000", InvoiceStatus.SENT, today.minusDays(5), today.plusDays(25));
        saveInvoice(orgId, "INV-008", client4, "72000", InvoiceStatus.DRAFT, today, today.plusDays(30));
    }

    private void saveInvoice(UUID orgId, String num, Client client, String amount, InvoiceStatus status, LocalDate issue, LocalDate due) {
        Invoice inv = new Invoice();
        inv.setOrgId(orgId);
        inv.setInvoiceNumber(num);
        inv.setClientId(UUID.fromString(client.getId()));
        inv.setClientName(client.getName());
        inv.setTotalAmount(new BigDecimal(amount));
        inv.setStatus(status);
        inv.setIssueDate(issue);
        inv.setDueDate(due);
        inv.setNotes("Demo Invoice " + num);
        mongoTemplate.save(inv);
    }

    private void seedTransactions(UUID orgId) {
        LocalDate today = LocalDate.now();
        saveTransaction(orgId, TransactionType.INCOME, "85000", "Payment received - Acme Tech INV-001", "REVENUE", today.minusDays(40));
        saveTransaction(orgId, TransactionType.INCOME, "120000", "Payment received - BuildRight INV-002", "REVENUE", today.minusDays(21));
        saveTransaction(orgId, TransactionType.INCOME, "45000", "Payment received - TechStart INV-003", "REVENUE", today.minusDays(10));
        saveTransaction(orgId, TransactionType.INCOME, "15000", "Consulting bonus - High Performance", "REVENUE", today.minusDays(15));
        saveTransaction(orgId, TransactionType.EXPENSE, "25000", "AWS Cloud Infrastructure", "OPERATIONS", today.minusDays(30));
        saveTransaction(orgId, TransactionType.EXPENSE, "18000", "Office Rent", "RENT", today.minusDays(32));
        saveTransaction(orgId, TransactionType.EXPENSE, "8500", "Team Development & Meals", "MEALS", today.minusDays(25));
        saveTransaction(orgId, TransactionType.EXPENSE, "12000", "Legal retainer", "LEGAL", today.minusDays(20));
        saveTransaction(orgId, TransactionType.EXPENSE, "5500", "Software subscriptions", "SOFTWARE", today.minusDays(18));
        saveTransaction(orgId, TransactionType.EXPENSE, "9800", "Travel", "TRAVEL", today.minusDays(14));
        saveTransaction(orgId, TransactionType.EXPENSE, "22000", "Contractor payment", "CONTRACTOR", today.minusDays(8));
        saveTransaction(orgId, TransactionType.EXPENSE, "3200", "Office supplies", "OFFICE", today.minusDays(4));
    }

    private void saveTransaction(UUID orgId, TransactionType type, String amount, String description, String category, LocalDate date) {
        Transaction t = new Transaction();
        t.setOrgId(orgId);
        t.setType(type);
        t.setAmount(new BigDecimal(amount));
        t.setDescription(description);
        t.setCategory(category);
        t.setTransactionDate(date);
        mongoTemplate.save(t);
    }
}
