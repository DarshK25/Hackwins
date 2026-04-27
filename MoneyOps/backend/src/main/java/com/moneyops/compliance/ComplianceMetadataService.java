package com.moneyops.compliance;

import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.transactions.entity.Transaction;
import com.moneyops.transactions.entity.TransactionType;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Locale;
import java.util.Set;

@Component
public class ComplianceMetadataService {

    private static final BigDecimal STANDARD_GST_RATE = new BigDecimal("0.18");

    private static final Set<String> BLOCKED_ITC_CATEGORIES = Set.of("SALARIES", "SALARY", "FUEL", "PERSONAL");
    private static final Set<String> POTENTIAL_GST_CATEGORIES = Set.of(
            "HARDWARE",
            "SOFTWARE",
            "UTILITIES",
            "MARKETING",
            "PROFESSIONAL",
            "PROFESSIONAL_FEES",
            "CONSULTING",
            "CONTRACTOR",
            "SUBCONTRACTOR"
    );

    private static final Set<String> AUTO_ITC_CATEGORIES = Set.of(
            "HARDWARE",
            "SOFTWARE",
            "UTILITIES",
            "MARKETING",
            "PROFESSIONAL",
            "PROFESSIONAL_FEES",
            "CONSULTING",
            "CONTRACTOR",
            "SUBCONTRACTOR"
    );

    public void normalizeTransaction(Transaction transaction) {
        if (transaction == null || transaction.getType() != TransactionType.EXPENSE) {
            return;
        }

        BigDecimal amount = defaultAmount(transaction.getAmount());
        if (amount.compareTo(BigDecimal.ZERO) <= 0) {
            return;
        }

        String normalizedCategory = normalizeCategory(transaction.getCategory());
        boolean gstBearing = isPotentialGstBearingCategory(normalizedCategory);

        if (transaction.getGstAmount() == null) {
            if (gstBearing) {
                BigDecimal derivedGst = deriveInclusiveGst(amount);
                transaction.setGstAmount(scale(derivedGst));
                transaction.setTaxableAmount(scale(amount.subtract(derivedGst)));
            } else if (isBlockedItcCategory(normalizedCategory)) {
                transaction.setGstAmount(BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP));
                transaction.setTaxableAmount(scale(amount));
            }
        } else if (transaction.getTaxableAmount() == null) {
            BigDecimal gstAmount = scale(transaction.getGstAmount());
            BigDecimal taxable = amount.subtract(gstAmount);
            transaction.setTaxableAmount(scale(taxable.max(BigDecimal.ZERO)));
        }

        if (transaction.getItcEligible() == null) {
            boolean hasMeaningfulGst = defaultAmount(transaction.getGstAmount()).compareTo(BigDecimal.ZERO) > 0;
            transaction.setItcEligible(isAutoItcCategory(normalizedCategory) && hasMeaningfulGst && !isBlockedItcCategory(normalizedCategory));
        }

        if (transaction.getHasReceipt() == null) {
            transaction.setHasReceipt(false);
        }
    }

    public boolean requiresBusinessGstin(BusinessOrganization business) {
        return business == null || Boolean.TRUE.equals(business.getGstRegistered());
    }

    public boolean hasValidBusinessGstin(BusinessOrganization business) {
        return business != null
                && business.getGstin() != null
                && business.getGstin().trim().length() == 15;
    }

    public boolean isBlockedItcCategory(String category) {
        return BLOCKED_ITC_CATEGORIES.contains(normalizeCategory(category));
    }

    public boolean isPotentialGstBearingCategory(String category) {
        return POTENTIAL_GST_CATEGORIES.contains(normalizeCategory(category));
    }

    public boolean isAutoItcCategory(String category) {
        return AUTO_ITC_CATEGORIES.contains(normalizeCategory(category));
    }

    public BigDecimal deriveInclusiveGst(BigDecimal grossAmount) {
        if (grossAmount == null || grossAmount.compareTo(BigDecimal.ZERO) <= 0) {
            return BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);
        }
        return scale(grossAmount.multiply(STANDARD_GST_RATE).divide(BigDecimal.ONE.add(STANDARD_GST_RATE), 2, RoundingMode.HALF_UP));
    }

    public String normalizeCategory(String category) {
        return category == null ? "" : category.trim().toUpperCase(Locale.ROOT);
    }

    private BigDecimal defaultAmount(BigDecimal value) {
        return value != null ? value : BigDecimal.ZERO;
    }

    private BigDecimal scale(BigDecimal value) {
        return (value != null ? value : BigDecimal.ZERO).setScale(2, RoundingMode.HALF_UP);
    }
}
