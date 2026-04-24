package com.moneyops.cashflow.service;

import com.moneyops.cashflow.dto.*;
import com.moneyops.invoices.entity.Invoice;
import com.moneyops.invoices.entity.InvoiceStatus;
import com.moneyops.invoices.repository.InvoiceRepository;
import com.moneyops.transactions.dto.TransactionDto;
import com.moneyops.transactions.service.TransactionService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class CashflowService {

    private final TransactionService transactionService;
    private final InvoiceRepository invoiceRepository;

    public CashflowSummaryDto getSummary(String orgId, int months) {
        LocalDate startDate = LocalDate.now().minusMonths(months).withDayOfMonth(1);
        LocalDate endDate = LocalDate.now().withDayOfMonth(LocalDate.now().lengthOfMonth());

        List<TransactionDto> transactions = transactionService.getTransactionsByDateRange(orgId, startDate, endDate);
        List<Invoice> invoices = invoiceRepository.findAllByOrgIdAndDeletedAtIsNull(orgId);

        BigDecimal totalIncome = BigDecimal.ZERO;
        BigDecimal totalExpense = BigDecimal.ZERO;

        Map<String, MonthlyCashflowDto> monthlyMap = new LinkedHashMap<>();
        DateTimeFormatter fmt = DateTimeFormatter.ofPattern("MMM yyyy");

        // Initialize last N months
        for (int i = months - 1; i >= 0; i--) {
            LocalDate d = LocalDate.now().minusMonths(i);
            String monthKey = d.format(fmt);
            monthlyMap.put(monthKey, new MonthlyCashflowDto(monthKey, BigDecimal.ZERO, BigDecimal.ZERO, BigDecimal.ZERO));
        }

        for (TransactionDto t : transactions) {
            String mKey = t.getTransactionDate().format(fmt);
            MonthlyCashflowDto monthDto = monthlyMap.getOrDefault(mKey, new MonthlyCashflowDto(mKey, BigDecimal.ZERO, BigDecimal.ZERO, BigDecimal.ZERO));
            
            if ("INCOME".equalsIgnoreCase(t.getType())) {
                monthDto.setIncome(monthDto.getIncome().add(t.getAmount()));
                totalIncome = totalIncome.add(t.getAmount());
            } else if ("EXPENSE".equalsIgnoreCase(t.getType())) {
                monthDto.setExpense(monthDto.getExpense().add(t.getAmount()));
                totalExpense = totalExpense.add(t.getAmount());
            }
            monthDto.setNet(monthDto.getIncome().subtract(monthDto.getExpense()));
            monthlyMap.put(mKey, monthDto);
        }

        BigDecimal pendingTotal = invoices.stream()
                .filter(i -> i.getStatus() == InvoiceStatus.DRAFT || i.getStatus() == InvoiceStatus.SENT)
                .map(Invoice::getBalanceDue)
                .filter(Objects::nonNull)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        BigDecimal overdueTotal = invoices.stream()
                .filter(i -> i.getStatus() == InvoiceStatus.OVERDUE)
                .map(Invoice::getBalanceDue)
                .filter(Objects::nonNull)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        // Simple running balance (total income - total expense)
        BigDecimal runningBalance = transactionService.getAllTransactions(orgId).stream()
                .map(t -> "INCOME".equalsIgnoreCase(t.getType()) ? t.getAmount() : t.getAmount().negate())
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        return CashflowSummaryDto.builder()
                .monthly(new ArrayList<>(monthlyMap.values()))
                .totalIncome(totalIncome)
                .totalExpense(totalExpense)
                .netCashflow(totalIncome.subtract(totalExpense))
                .pendingInvoicesTotal(pendingTotal)
                .overdueInvoicesTotal(overdueTotal)
                .runningBalance(runningBalance)
                .build();
    }

    public CashflowForecastDto getForecast(String orgId, int forecastMonths) {
        // Simple moving average using last 3 months
        LocalDate startDate = LocalDate.now().minusMonths(3).withDayOfMonth(1);
        LocalDate endDate = LocalDate.now().withDayOfMonth(LocalDate.now().lengthOfMonth());

        List<TransactionDto> transactions = transactionService.getTransactionsByDateRange(orgId, startDate, endDate);
        
        BigDecimal last3Income = BigDecimal.ZERO;
        BigDecimal last3Expense = BigDecimal.ZERO;

        for (TransactionDto t : transactions) {
            if ("INCOME".equalsIgnoreCase(t.getType())) last3Income = last3Income.add(t.getAmount());
            else if ("EXPENSE".equalsIgnoreCase(t.getType())) last3Expense = last3Expense.add(t.getAmount());
        }

        BigDecimal avgIncome = last3Income.divide(BigDecimal.valueOf(3), RoundingMode.HALF_UP);
        BigDecimal avgExpense = last3Expense.divide(BigDecimal.valueOf(3), RoundingMode.HALF_UP);

        List<Invoice> pendingInvoices = invoiceRepository.findAllByOrgIdAndDeletedAtIsNull(orgId).stream()
                .filter(i -> i.getStatus() == InvoiceStatus.SENT && i.getDueDate() != null && i.getDueDate().isAfter(LocalDate.now()))
                .collect(Collectors.toList());

        List<ForecastMonthDto> forecastList = new ArrayList<>();
        DateTimeFormatter fmt = DateTimeFormatter.ofPattern("MMM yyyy");

        for (int i = 1; i <= forecastMonths; i++) {
            LocalDate futureMonth = LocalDate.now().plusMonths(i);
            String mKey = futureMonth.format(fmt);
            
            // Add pending invoices to income if due in this future month
            BigDecimal invoicesDueThisMonth = pendingInvoices.stream()
                    .filter(inv -> inv.getDueDate().getYear() == futureMonth.getYear() && inv.getDueDate().getMonth() == futureMonth.getMonth())
                    .map(Invoice::getBalanceDue)
                    .filter(Objects::nonNull)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);

            BigDecimal predictedIncome = avgIncome.add(invoicesDueThisMonth);
            BigDecimal predictedExpense = avgExpense; // Static avg expense
            
            double confidence = Math.max(0.4, 0.9 - (i * 0.15)); // confidence drops over time

            forecastList.add(new ForecastMonthDto(mKey, predictedIncome, predictedExpense, confidence));
        }

        return CashflowForecastDto.builder().forecast(forecastList).build();
    }
}
