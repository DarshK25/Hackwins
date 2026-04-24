package com.moneyops.budgets.service;

import com.moneyops.budgets.dto.BudgetAnalysisDTO;
import com.moneyops.budgets.dto.BudgetDTO;
import com.moneyops.budgets.entity.Budget;
import com.moneyops.budgets.repository.BudgetRepository;
import com.moneyops.shared.exceptions.NotFoundException;
import com.moneyops.shared.exceptions.UnauthorizedException;
import com.moneyops.shared.exceptions.ValidationException;
import com.moneyops.transactions.entity.Transaction;
import com.moneyops.transactions.entity.TransactionType;
import com.moneyops.transactions.repository.TransactionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.TemporalAdjusters;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional
public class BudgetService {

    private static final BigDecimal WARNING_THRESHOLD = BigDecimal.valueOf(80);
    private static final BigDecimal HUNDRED = BigDecimal.valueOf(100);

    private final BudgetRepository budgetRepository;
    private final TransactionRepository transactionRepository;

    public BudgetDTO createBudget(BudgetDTO request, String orgId, String userId) {
        if (orgId == null || orgId.isBlank()) {
            throw new UnauthorizedException("Missing organization context");
        }

        Budget budget = new Budget();
        budget.setId(UUID.randomUUID().toString());
        applyRequestToBudget(budget, request, orgId);
        if (userId != null && !userId.isBlank()) {
            budget.setCreatedBy(userId);
            budget.setUpdatedBy(userId);
        }

        Budget saved = budgetRepository.save(budget);
        return toBudgetDto(saved, calculateMetrics(saved, false));
    }

    public List<BudgetDTO> listBudgets(String orgId) {
        if (orgId == null || orgId.isBlank()) {
            return List.of();
        }

        return budgetRepository.findAllByOrgIdAndDeletedAtIsNullOrderByCreatedAtDesc(orgId).stream()
                .map(budget -> toBudgetDto(budget, calculateMetrics(budget, false)))
                .collect(Collectors.toList());
    }

    public BudgetDTO getBudgetById(String id, String orgId) {
        Budget budget = getActiveBudget(id, orgId);
        return toBudgetDto(budget, calculateMetrics(budget, false));
    }

    public BudgetDTO updateBudget(String id, BudgetDTO request, String orgId, String userId) {
        Budget budget = getActiveBudget(id, orgId);
        applyRequestToBudget(budget, request, orgId);
        if (userId != null && !userId.isBlank()) {
            budget.setUpdatedBy(userId);
        }

        Budget saved = budgetRepository.save(budget);
        return toBudgetDto(saved, calculateMetrics(saved, false));
    }

    public void deleteBudget(String id, String orgId) {
        Budget budget = getActiveBudget(id, orgId);
        budget.setDeletedAt(LocalDateTime.now());
        budgetRepository.save(budget);
    }

    public BudgetAnalysisDTO getBudgetAnalysis(String id, String orgId) {
        Budget budget = getActiveBudget(id, orgId);
        BudgetMetrics metrics = calculateMetrics(budget, true);
        return toBudgetAnalysisDto(budget, metrics);
    }

    private Budget getActiveBudget(String id, String orgId) {
        if (orgId == null || orgId.isBlank()) {
            throw new UnauthorizedException("Missing organization context");
        }

        return budgetRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new NotFoundException("Budget", id));
    }

    private void applyRequestToBudget(Budget budget, BudgetDTO request, String orgId) {
        validateRequest(request);

        DateRange dateRange = resolveDateRange(request.getPeriod(), request.getStartDate(), request.getEndDate());

        budget.setOrgId(orgId);
        budget.setName(request.getName().trim());
        budget.setPeriod(normalizePeriod(request.getPeriod()));
        budget.setStartDate(dateRange.startDate());
        budget.setEndDate(dateRange.endDate());
        budget.setCategories(request.getCategories().stream()
                .map(this::toBudgetCategory)
                .collect(Collectors.toCollection(ArrayList::new)));
    }

    private void validateRequest(BudgetDTO request) {
        List<String> errors = new ArrayList<>();
        if (request == null) {
            throw new ValidationException(List.of("Budget payload is required"));
        }
        if (request.getName() == null || request.getName().isBlank()) {
            errors.add("Budget name is required");
        }
        if (request.getPeriod() == null || request.getPeriod().isBlank()) {
            errors.add("Budget period is required");
        }
        if (request.getCategories() == null || request.getCategories().isEmpty()) {
            errors.add("At least one budget category is required");
        } else {
            Map<String, Integer> seen = new HashMap<>();
            for (int index = 0; index < request.getCategories().size(); index++) {
                BudgetDTO.CategoryDTO category = request.getCategories().get(index);
                int itemNumber = index + 1;
                if (category == null) {
                    errors.add("Category " + itemNumber + " is invalid");
                    continue;
                }
                if (category.getName() == null || category.getName().isBlank()) {
                    errors.add("Category " + itemNumber + " name is required");
                }
                BigDecimal limit = category.getLimit();
                if (limit == null) {
                    errors.add("Category " + itemNumber + " limit is required");
                } else if (limit.compareTo(BigDecimal.ZERO) < 0) {
                    errors.add("Category " + itemNumber + " limit must be zero or greater");
                }
                String normalizedName = normalizeCategory(category.getName());
                if (!normalizedName.isBlank()) {
                    seen.merge(normalizedName, 1, Integer::sum);
                }
            }
            seen.forEach((name, count) -> {
                if (count > 1) {
                    errors.add("Duplicate budget category: " + name);
                }
            });
        }

        if (request.getStartDate() != null && request.getEndDate() != null && request.getEndDate().isBefore(request.getStartDate())) {
            errors.add("Budget end date must be on or after the start date");
        }

        if (!errors.isEmpty()) {
            throw new ValidationException(errors);
        }
    }

    private Budget.BudgetCategory toBudgetCategory(BudgetDTO.CategoryDTO categoryDTO) {
        Budget.BudgetCategory category = new Budget.BudgetCategory();
        category.setName(categoryDTO.getName().trim());
        category.setLimit(defaultAmount(categoryDTO.getLimit()));
        return category;
    }

    private BudgetDTO toBudgetDto(Budget budget, BudgetMetrics metrics) {
        BudgetDTO dto = new BudgetDTO();
        dto.setId(budget.getId());
        dto.setOrgId(budget.getOrgId());
        dto.setName(budget.getName());
        dto.setPeriod(budget.getPeriod());
        dto.setStartDate(budget.getStartDate());
        dto.setEndDate(budget.getEndDate());
        dto.setCreatedAt(budget.getCreatedAt());
        dto.setUpdatedAt(budget.getUpdatedAt());
        dto.setTotalBudget(metrics.totalBudget());
        dto.setTotalSpent(metrics.totalSpent());
        dto.setRemaining(metrics.remaining());
        dto.setUtilizationPercent(metrics.utilizationPercent());

        List<BudgetDTO.CategoryDTO> categories = new ArrayList<>();
        for (Budget.BudgetCategory category : budget.getCategories()) {
            BudgetDTO.CategoryDTO categoryDTO = new BudgetDTO.CategoryDTO();
            String categoryKey = normalizeCategory(category.getName());
            CategoryMetrics categoryMetrics = metrics.categories().getOrDefault(categoryKey, CategoryMetrics.empty());
            BigDecimal limit = defaultAmount(category.getLimit());

            categoryDTO.setName(category.getName());
            categoryDTO.setLimit(limit);
            categoryDTO.setActual(categoryMetrics.actual());
            categoryDTO.setRemaining(limit.subtract(categoryMetrics.actual()));
            categoryDTO.setStatus(resolveStatus(limit, categoryMetrics.actual()));
            categories.add(categoryDTO);
        }
        dto.setCategories(categories);
        return dto;
    }

    private BudgetAnalysisDTO toBudgetAnalysisDto(Budget budget, BudgetMetrics metrics) {
        BudgetAnalysisDTO dto = new BudgetAnalysisDTO();
        dto.setBudgetId(budget.getId());
        dto.setOrgId(budget.getOrgId());
        dto.setName(budget.getName());
        dto.setPeriod(budget.getPeriod());
        dto.setStartDate(budget.getStartDate());
        dto.setEndDate(budget.getEndDate());
        dto.setTotalBudget(metrics.totalBudget());
        dto.setTotalSpent(metrics.totalSpent());
        dto.setRemaining(metrics.remaining());
        dto.setUtilizationPercent(metrics.utilizationPercent());

        List<BudgetAnalysisDTO.CategoryAnalysisDTO> categoryDtos = new ArrayList<>();
        for (Budget.BudgetCategory category : budget.getCategories()) {
            String categoryKey = normalizeCategory(category.getName());
            CategoryMetrics categoryMetrics = metrics.categories().getOrDefault(categoryKey, CategoryMetrics.empty());
            BigDecimal budgeted = defaultAmount(category.getLimit());

            BudgetAnalysisDTO.CategoryAnalysisDTO categoryDTO = new BudgetAnalysisDTO.CategoryAnalysisDTO();
            categoryDTO.setName(category.getName());
            categoryDTO.setBudgeted(budgeted);
            categoryDTO.setActual(categoryMetrics.actual());
            categoryDTO.setRemaining(budgeted.subtract(categoryMetrics.actual()));
            categoryDTO.setStatus(resolveStatus(budgeted, categoryMetrics.actual()));
            categoryDTO.setTransactions(categoryMetrics.transactions().stream()
                    .sorted(Comparator.comparing(Transaction::getTransactionDate, Comparator.nullsLast(Comparator.naturalOrder())).reversed())
                    .map(this::toTransactionSummary)
                    .collect(Collectors.toList()));
            categoryDtos.add(categoryDTO);
        }
        dto.setCategories(categoryDtos);
        return dto;
    }

    private BudgetAnalysisDTO.TransactionSummaryDTO toTransactionSummary(Transaction transaction) {
        BudgetAnalysisDTO.TransactionSummaryDTO dto = new BudgetAnalysisDTO.TransactionSummaryDTO();
        dto.setId(transaction.getId());
        dto.setTransactionDate(transaction.getTransactionDate());
        dto.setDescription(transaction.getDescription());
        dto.setAmount(defaultAmount(transaction.getAmount()).abs());
        dto.setCategory(transaction.getCategory());
        dto.setReferenceNumber(transaction.getReferenceNumber());
        return dto;
    }

    private BudgetMetrics calculateMetrics(Budget budget, boolean includeTransactions) {
        List<Transaction> transactions = transactionRepository
                .findByOrgIdAndTypeAndTransactionDateBetweenAndDeletedAtIsNull(
                        budget.getOrgId(),
                        TransactionType.EXPENSE,
                        budget.getStartDate(),
                        budget.getEndDate()
                );

        Map<String, CategoryMetrics> metricsByCategory = new LinkedHashMap<>();
        for (Budget.BudgetCategory category : budget.getCategories()) {
            metricsByCategory.put(normalizeCategory(category.getName()), CategoryMetrics.empty());
        }

        for (Transaction transaction : transactions) {
            String categoryKey = normalizeCategory(transaction.getCategory());
            if (!metricsByCategory.containsKey(categoryKey)) {
                continue;
            }

            CategoryMetrics current = metricsByCategory.get(categoryKey);
            List<Transaction> categoryTransactions = includeTransactions
                    ? new ArrayList<>(current.transactions())
                    : List.of();
            if (includeTransactions) {
                categoryTransactions.add(transaction);
            }

            metricsByCategory.put(
                    categoryKey,
                    new CategoryMetrics(
                            current.actual().add(defaultAmount(transaction.getAmount()).abs()),
                            categoryTransactions
                    )
            );
        }

        BigDecimal totalBudget = budget.getCategories().stream()
                .map(Budget.BudgetCategory::getLimit)
                .map(this::defaultAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        BigDecimal totalSpent = metricsByCategory.values().stream()
                .map(CategoryMetrics::actual)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        BigDecimal remaining = totalBudget.subtract(totalSpent);
        BigDecimal utilizationPercent = calculatePercent(totalSpent, totalBudget);

        return new BudgetMetrics(totalBudget, totalSpent, remaining, utilizationPercent, metricsByCategory);
    }

    private String resolveStatus(BigDecimal budgeted, BigDecimal actual) {
        BigDecimal normalizedBudget = defaultAmount(budgeted);
        BigDecimal normalizedActual = defaultAmount(actual);
        if (normalizedBudget.compareTo(BigDecimal.ZERO) <= 0) {
            return normalizedActual.compareTo(BigDecimal.ZERO) > 0 ? "EXCEEDED" : "ON_TRACK";
        }

        BigDecimal percent = calculatePercent(normalizedActual, normalizedBudget);
        if (normalizedActual.compareTo(normalizedBudget) > 0) {
            return "EXCEEDED";
        }
        if (percent.compareTo(WARNING_THRESHOLD) > 0) {
            return "WARNING";
        }
        return "ON_TRACK";
    }

    private BigDecimal calculatePercent(BigDecimal actual, BigDecimal total) {
        BigDecimal normalizedTotal = defaultAmount(total);
        if (normalizedTotal.compareTo(BigDecimal.ZERO) <= 0) {
            return BigDecimal.ZERO;
        }
        return defaultAmount(actual)
                .multiply(HUNDRED)
                .divide(normalizedTotal, 2, RoundingMode.HALF_UP);
    }

    private BigDecimal defaultAmount(BigDecimal value) {
        return value == null ? BigDecimal.ZERO : value;
    }

    private String normalizePeriod(String period) {
        return period == null ? "CUSTOM" : period.trim().toUpperCase(Locale.ROOT);
    }

    private String normalizeCategory(String name) {
        if (name == null || name.isBlank()) {
            return "UNCATEGORIZED";
        }
        return name.trim().toUpperCase(Locale.ROOT);
    }

    private DateRange resolveDateRange(String period, LocalDate startDate, LocalDate endDate) {
        LocalDate resolvedStart = startDate != null ? startDate : LocalDate.now().withDayOfMonth(1);
        String normalizedPeriod = normalizePeriod(period);

        LocalDate resolvedEnd = endDate;
        if (resolvedEnd == null) {
            resolvedEnd = switch (normalizedPeriod) {
                case "MONTHLY" -> resolvedStart.with(TemporalAdjusters.lastDayOfMonth());
                case "QUARTERLY" -> resolvedStart.plusMonths(3).minusDays(1);
                case "YEARLY" -> resolvedStart.plusYears(1).minusDays(1);
                default -> resolvedStart;
            };
        }

        if (resolvedEnd.isBefore(resolvedStart)) {
            throw new ValidationException(List.of("Budget end date must be on or after the start date"));
        }

        return new DateRange(resolvedStart, resolvedEnd);
    }

    private record DateRange(LocalDate startDate, LocalDate endDate) {
    }

    private record BudgetMetrics(
            BigDecimal totalBudget,
            BigDecimal totalSpent,
            BigDecimal remaining,
            BigDecimal utilizationPercent,
            Map<String, CategoryMetrics> categories
    ) {
    }

    private record CategoryMetrics(BigDecimal actual, List<Transaction> transactions) {
        private static CategoryMetrics empty() {
            return new CategoryMetrics(BigDecimal.ZERO, List.of());
        }
    }
}
