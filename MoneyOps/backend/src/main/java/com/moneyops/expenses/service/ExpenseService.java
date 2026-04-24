package com.moneyops.expenses.service;

import com.moneyops.expenses.dto.ExpenseDTO;
import com.moneyops.expenses.dto.ExpenseSummaryDTO;
import com.moneyops.security.team.TeamActionAuthorizationService;
import com.moneyops.shared.dto.PageResponse;
import com.moneyops.shared.exceptions.NotFoundException;
import com.moneyops.shared.exceptions.UnauthorizedException;
import com.moneyops.shared.exceptions.ValidationException;
import com.moneyops.transactions.entity.Transaction;
import com.moneyops.transactions.entity.TransactionType;
import com.moneyops.transactions.repository.TransactionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.Month;
import java.time.format.TextStyle;
import java.time.temporal.ChronoUnit;
import java.time.temporal.IsoFields;
import java.time.temporal.TemporalAdjusters;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Transactional
public class ExpenseService {

    private static final List<String> DEFAULT_CATEGORIES = List.of(
            "Office",
            "Marketing",
            "Salaries",
            "Utilities",
            "Travel",
            "Software",
            "Hardware",
            "Legal",
            "Taxes",
            "Other"
    );

    private final MongoTemplate mongoTemplate;
    private final TransactionRepository transactionRepository;
    private final TeamActionAuthorizationService teamActionAuthorizationService;

    public PageResponse<ExpenseDTO> getExpenses(
            String orgId,
            int page,
            int size,
            String category,
            LocalDate dateFrom,
            LocalDate dateTo
    ) {
        Query query = buildExpenseQuery(requireOrgId(orgId), category, dateFrom, dateTo);
        query.with(Sort.by(Sort.Direction.DESC, "transactionDate").and(Sort.by(Sort.Direction.DESC, "createdAt")));

        long total = mongoTemplate.count(query, Transaction.class);
        query.skip((long) page * size).limit(size);

        List<ExpenseDTO> content = mongoTemplate.find(query, Transaction.class).stream()
                .map(this::toExpenseDto)
                .toList();

        return PageResponse.from(new PageImpl<>(content, PageRequest.of(page, size), total));
    }

    public ExpenseDTO createExpense(ExpenseDTO request, String orgId, String userId) {
        validateExpenseRequest(request, false);
        teamActionAuthorizationService.assertUserCanCreateSensitiveAction(
                requireOrgId(orgId),
                userId,
                request.getTeamActionCode()
        );

        Transaction transaction = new Transaction();
        transaction.setId(UUID.randomUUID().toString());
        transaction.setOrgId(requireOrgId(orgId));
        transaction.setType(TransactionType.EXPENSE);
        transaction.setStatus(firstNonBlank(request.getStatus(), "COMPLETED"));
        applyRequest(transaction, request);

        return toExpenseDto(transactionRepository.save(transaction));
    }

    public ExpenseDTO updateExpense(String id, ExpenseDTO request, String orgId) {
        validateExpenseRequest(request, true);

        Transaction transaction = getExpenseTransaction(id, orgId);
        applyRequest(transaction, request);
        if (request.getStatus() != null && !request.getStatus().isBlank()) {
            transaction.setStatus(request.getStatus().trim().toUpperCase(Locale.ROOT));
        }

        return toExpenseDto(transactionRepository.save(transaction));
    }

    public void deleteExpense(String id, String orgId) {
        Transaction transaction = getExpenseTransaction(id, orgId);
        transaction.setDeletedAt(java.time.LocalDateTime.now());
        transactionRepository.save(transaction);
    }

    public ExpenseSummaryDTO getSummary(
            String orgId,
            String period,
            String category,
            LocalDate dateFrom,
            LocalDate dateTo
    ) {
        String resolvedOrgId = requireOrgId(orgId);
        DateRange range = resolveSummaryRange(period, dateFrom, dateTo);
        List<Transaction> expenses = loadExpenses(resolvedOrgId, category, range.startDate(), range.endDate());

        BigDecimal totalExpenses = expenses.stream()
                .map(Transaction::getAmount)
                .map(this::absAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        ExpenseSummaryDTO summary = new ExpenseSummaryDTO();
        summary.setTotalExpenses(totalExpenses);
        summary.setByCategory(buildCategorySummary(expenses, totalExpenses));
        summary.setTrend(buildTrend(resolvedOrgId, period, category, range));
        summary.setTopExpense(buildTopExpense(expenses));
        summary.setAvgMonthly(calculateAvgMonthly(expenses, range));
        return summary;
    }

    public List<String> getAvailableCategories() {
        return DEFAULT_CATEGORIES;
    }

    private Query buildExpenseQuery(String orgId, String category, LocalDate dateFrom, LocalDate dateTo) {
        List<Criteria> criteria = new ArrayList<>();
        criteria.add(Criteria.where("orgId").is(orgId));
        criteria.add(Criteria.where("type").is(TransactionType.EXPENSE));
        criteria.add(Criteria.where("deletedAt").is(null));

        if (category != null && !category.isBlank()) {
            criteria.add(Criteria.where("category").regex("^" + java.util.regex.Pattern.quote(category.trim()) + "$", "i"));
        }

        if (dateFrom != null || dateTo != null) {
            Criteria dateCriteria = Criteria.where("transactionDate");
            if (dateFrom != null) {
                dateCriteria = dateCriteria.gte(dateFrom);
            }
            if (dateTo != null) {
                dateCriteria = dateCriteria.lte(dateTo);
            }
            criteria.add(dateCriteria);
        }

        return new Query(new Criteria().andOperator(criteria.toArray(new Criteria[0])));
    }

    private List<Transaction> loadExpenses(String orgId, String category, LocalDate dateFrom, LocalDate dateTo) {
        Query query = buildExpenseQuery(orgId, category, dateFrom, dateTo);
        query.with(Sort.by(Sort.Direction.DESC, "transactionDate").and(Sort.by(Sort.Direction.DESC, "createdAt")));
        return mongoTemplate.find(query, Transaction.class);
    }

    private List<ExpenseSummaryDTO.CategorySummaryDTO> buildCategorySummary(List<Transaction> expenses, BigDecimal totalExpenses) {
        Map<String, CategoryAggregate> totals = new LinkedHashMap<>();
        for (Transaction expense : expenses) {
            String category = firstNonBlank(expense.getCategory(), "Other");
            CategoryAggregate aggregate = totals.computeIfAbsent(category, ignored -> new CategoryAggregate());
            aggregate.total = aggregate.total.add(absAmount(expense.getAmount()));
            aggregate.count += 1;
        }

        return totals.entrySet().stream()
                .sorted((left, right) -> right.getValue().total.compareTo(left.getValue().total))
                .map(entry -> {
                    ExpenseSummaryDTO.CategorySummaryDTO dto = new ExpenseSummaryDTO.CategorySummaryDTO();
                    dto.setCategory(entry.getKey());
                    dto.setTotal(entry.getValue().total);
                    dto.setCount(entry.getValue().count);
                    dto.setPercent(calculatePercent(entry.getValue().total, totalExpenses));
                    return dto;
                })
                .toList();
    }

    private List<ExpenseSummaryDTO.TrendPointDTO> buildTrend(String orgId, String period, String category, DateRange range) {
        String normalizedPeriod = normalizePeriod(period);
        LocalDate trendStart = switch (normalizedPeriod) {
            case "YEARLY" -> range.endDate().minusYears(4).with(TemporalAdjusters.firstDayOfYear());
            case "QUARTERLY" -> range.endDate().minusMonths(9).withDayOfMonth(1);
            default -> range.endDate().minusMonths(5).withDayOfMonth(1);
        };

        List<Transaction> expenses = loadExpenses(orgId, category, trendStart, range.endDate());
        Map<String, BigDecimal> totals = new LinkedHashMap<>();

        if ("YEARLY".equals(normalizedPeriod)) {
            for (int offset = 4; offset >= 0; offset--) {
                LocalDate point = range.endDate().minusYears(offset);
                totals.put(String.valueOf(point.getYear()), BigDecimal.ZERO);
            }
            for (Transaction expense : expenses) {
                if (expense.getTransactionDate() == null) {
                    continue;
                }
                String key = String.valueOf(expense.getTransactionDate().getYear());
                if (totals.containsKey(key)) {
                    totals.put(key, totals.get(key).add(absAmount(expense.getAmount())));
                }
            }
        } else if ("QUARTERLY".equals(normalizedPeriod)) {
            LocalDate firstQuarter = range.endDate().minusMonths(9).withDayOfMonth(1);
            for (int index = 0; index < 4; index++) {
                LocalDate point = firstQuarter.plusMonths(index * 3L);
                totals.put(formatQuarter(point), BigDecimal.ZERO);
            }
            for (Transaction expense : expenses) {
                if (expense.getTransactionDate() == null) {
                    continue;
                }
                String key = formatQuarter(expense.getTransactionDate());
                if (totals.containsKey(key)) {
                    totals.put(key, totals.get(key).add(absAmount(expense.getAmount())));
                }
            }
        } else {
            LocalDate firstMonth = range.endDate().minusMonths(5).withDayOfMonth(1);
            for (int index = 0; index < 6; index++) {
                LocalDate point = firstMonth.plusMonths(index);
                totals.put(formatMonth(point), BigDecimal.ZERO);
            }
            for (Transaction expense : expenses) {
                if (expense.getTransactionDate() == null) {
                    continue;
                }
                String key = formatMonth(expense.getTransactionDate());
                if (totals.containsKey(key)) {
                    totals.put(key, totals.get(key).add(absAmount(expense.getAmount())));
                }
            }
        }

        return totals.entrySet().stream().map(entry -> {
            ExpenseSummaryDTO.TrendPointDTO dto = new ExpenseSummaryDTO.TrendPointDTO();
            dto.setMonth(entry.getKey());
            dto.setTotal(entry.getValue());
            return dto;
        }).toList();
    }

    private ExpenseSummaryDTO.TopExpenseDTO buildTopExpense(List<Transaction> expenses) {
        Transaction topExpense = expenses.stream()
                .max((left, right) -> absAmount(left.getAmount()).compareTo(absAmount(right.getAmount())))
                .orElse(null);

        if (topExpense == null) {
            return null;
        }

        ExpenseSummaryDTO.TopExpenseDTO dto = new ExpenseSummaryDTO.TopExpenseDTO();
        dto.setDescription(firstNonBlank(topExpense.getDescription(), firstNonBlank(topExpense.getCategory(), "Expense")));
        dto.setAmount(absAmount(topExpense.getAmount()));
        dto.setDate(topExpense.getTransactionDate());
        return dto;
    }

    private BigDecimal calculateAvgMonthly(List<Transaction> expenses, DateRange range) {
        long months = Math.max(1, ChronoUnit.MONTHS.between(
                range.startDate().withDayOfMonth(1),
                range.endDate().withDayOfMonth(1)
        ) + 1);
        BigDecimal total = expenses.stream()
                .map(Transaction::getAmount)
                .map(this::absAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        return total.divide(BigDecimal.valueOf(months), 2, RoundingMode.HALF_UP);
    }

    private void applyRequest(Transaction transaction, ExpenseDTO request) {
        transaction.setAmount(absAmount(request.getAmount()));
        transaction.setCategory(firstNonBlank(request.getCategory(), "Other"));
        transaction.setDescription(trimToNull(request.getDescription()));
        transaction.setTransactionDate(request.getDate() != null ? request.getDate() : LocalDate.now());
        transaction.setPaymentMethod(trimToNull(request.getPaymentMethod()));
        transaction.setReceiptUrl(trimToNull(request.getReceiptUrl()));
        transaction.setVoiceContext(request.getVoiceContext());
        if (transaction.getCurrency() == null) {
            transaction.setCurrency("INR");
        }
    }

    private void validateExpenseRequest(ExpenseDTO request, boolean update) {
        if (request == null) {
            throw new ValidationException(List.of("Expense payload is required"));
        }

        List<String> errors = new ArrayList<>();
        if (request.getAmount() == null || request.getAmount().compareTo(BigDecimal.ZERO) <= 0) {
            errors.add("Expense amount must be greater than zero");
        }
        if (!update && request.getDate() == null) {
            errors.add("Expense date is required");
        }
        if (request.getReceiptUrl() != null && !request.getReceiptUrl().isBlank()) {
            String receiptUrl = request.getReceiptUrl().trim().toLowerCase(Locale.ROOT);
            if (!(receiptUrl.startsWith("http://") || receiptUrl.startsWith("https://"))) {
                errors.add("Receipt URL must start with http:// or https://");
            }
        }

        if (!errors.isEmpty()) {
            throw new ValidationException(errors);
        }
    }

    private Transaction getExpenseTransaction(String id, String orgId) {
        Transaction transaction = transactionRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, requireOrgId(orgId))
                .orElseThrow(() -> new NotFoundException("Expense", id));
        if (transaction.getType() != TransactionType.EXPENSE) {
            throw new NotFoundException("Expense", id);
        }
        return transaction;
    }

    private ExpenseDTO toExpenseDto(Transaction transaction) {
        ExpenseDTO dto = new ExpenseDTO();
        dto.setId(transaction.getId());
        dto.setOrgId(transaction.getOrgId());
        dto.setAmount(absAmount(transaction.getAmount()));
        dto.setCategory(transaction.getCategory());
        dto.setDescription(transaction.getDescription());
        dto.setDate(transaction.getTransactionDate());
        dto.setPaymentMethod(transaction.getPaymentMethod());
        dto.setReceiptUrl(transaction.getReceiptUrl());
        dto.setStatus(transaction.getStatus());
        dto.setCreatedAt(transaction.getCreatedAt());
        dto.setUpdatedAt(transaction.getUpdatedAt());
        dto.setVoiceContext(transaction.getVoiceContext());
        return dto;
    }

    private String requireOrgId(String orgId) {
        if (orgId == null || orgId.isBlank()) {
            throw new UnauthorizedException("Missing organization context");
        }
        return orgId;
    }

    private String normalizePeriod(String period) {
        return period == null ? "MONTHLY" : period.trim().toUpperCase(Locale.ROOT);
    }

    private DateRange resolveSummaryRange(String period, LocalDate dateFrom, LocalDate dateTo) {
        if (dateFrom != null || dateTo != null) {
            LocalDate start = dateFrom != null ? dateFrom : LocalDate.now().withDayOfMonth(1);
            LocalDate end = dateTo != null ? dateTo : start.with(TemporalAdjusters.lastDayOfMonth());
            return new DateRange(start, end);
        }

        LocalDate today = LocalDate.now();
        return switch (normalizePeriod(period)) {
            case "YEARLY" -> new DateRange(
                    today.with(TemporalAdjusters.firstDayOfYear()),
                    today.with(TemporalAdjusters.lastDayOfYear())
            );
            case "QUARTERLY" -> {
                int quarter = today.get(IsoFields.QUARTER_OF_YEAR);
                Month firstMonth = Month.of(((quarter - 1) * 3) + 1);
                LocalDate start = LocalDate.of(today.getYear(), firstMonth, 1);
                yield new DateRange(start, start.plusMonths(2).with(TemporalAdjusters.lastDayOfMonth()));
            }
            default -> new DateRange(
                    today.withDayOfMonth(1),
                    today.with(TemporalAdjusters.lastDayOfMonth())
            );
        };
    }

    private BigDecimal absAmount(BigDecimal value) {
        return value == null ? BigDecimal.ZERO : value.abs();
    }

    private BigDecimal calculatePercent(BigDecimal numerator, BigDecimal denominator) {
        if (denominator == null || denominator.compareTo(BigDecimal.ZERO) <= 0) {
            return BigDecimal.ZERO;
        }
        return numerator.multiply(BigDecimal.valueOf(100))
                .divide(denominator, 2, RoundingMode.HALF_UP);
    }

    private String formatMonth(LocalDate date) {
        return date.getMonth().getDisplayName(TextStyle.SHORT, Locale.ENGLISH) + " " + date.getYear();
    }

    private String formatQuarter(LocalDate date) {
        return "Q" + date.get(IsoFields.QUARTER_OF_YEAR) + " " + date.getYear();
    }

    private String firstNonBlank(String primary, String fallback) {
        String value = trimToNull(primary);
        return value != null ? value : fallback;
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isBlank() ? null : trimmed;
    }

    private record DateRange(LocalDate startDate, LocalDate endDate) {
    }

    private static class CategoryAggregate {
        private BigDecimal total = BigDecimal.ZERO;
        private long count = 0;
    }
}
