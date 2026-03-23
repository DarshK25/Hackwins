// src/main/java/com/moneyops/moneyopsApplication.java
package com.moneyops;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import org.springframework.data.mongodb.config.EnableMongoAuditing;

@SpringBootApplication
@EnableMongoAuditing
public class MoneyOpsApplication {
    public static void main(String[] args) {
        SpringApplication.run(MoneyOpsApplication.class, args);
    }
}