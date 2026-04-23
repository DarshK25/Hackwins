package com.moneyops.budget.entity;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.mapping.Document;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.mongodb.core.index.Indexed;

@Document(collection = "budgets")
@CompoundIndex(name = "org_year_month_idx", def = "{'orgId': 1, 'year': 1, 'month': 1}")
@Data
public class Budget {

    @Id
    private String id;

    @Indexed
    private String orgId;

    private int year;
    private int month;

    private String category;
    private BigDecimal amount;
    private String notes;

    @CreatedDate
    private LocalDateTime createdAt;

    @LastModifiedDate
    private LocalDateTime updatedAt;
}