package com.moneyops.budgets.entity;

import lombok.Data;
import org.springframework.data.annotation.CreatedBy;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.LastModifiedBy;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Document(collection = "budgets")
@CompoundIndex(name = "org_deleted_idx", def = "{'orgId': 1, 'deletedAt': 1}")
@Data
public class Budget {

    @Id
    private String id;

    @Indexed
    private String orgId;

    private String name;
    private String period;
    private LocalDate startDate;
    private LocalDate endDate;
    private List<BudgetCategory> categories = new ArrayList<>();

    @CreatedDate
    private LocalDateTime createdAt;

    @LastModifiedDate
    private LocalDateTime updatedAt;

    @CreatedBy
    private String createdBy;

    @LastModifiedBy
    private String updatedBy;

    private LocalDateTime deletedAt;

    @Data
    public static class BudgetCategory {
        private String name;
        private BigDecimal limit = BigDecimal.ZERO;
    }
}
