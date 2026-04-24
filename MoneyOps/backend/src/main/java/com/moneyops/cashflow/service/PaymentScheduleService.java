package com.moneyops.cashflow.service;

import com.moneyops.cashflow.dto.SchedulePaymentDto;
import com.moneyops.transactions.dto.TransactionDto;
import com.moneyops.transactions.service.TransactionService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.UUID;

@Service
@RequiredArgsConstructor
public class PaymentScheduleService {

    private final TransactionService transactionService;

    public TransactionDto schedulePayment(SchedulePaymentDto dto, String userId) {
        TransactionDto transactionDto = new TransactionDto();
        transactionDto.setOrgId(dto.getOrgId());
        transactionDto.setInvoiceId(dto.getInvoiceId());
        transactionDto.setAmount(dto.getAmount());
        transactionDto.setTransactionDate(dto.getScheduledDate());
        transactionDto.setPaymentMethod(dto.getPaymentMethod());
        transactionDto.setDescription(dto.getNotes() != null ? dto.getNotes() : "Scheduled Payment");
        transactionDto.setType("EXPENSE"); // Default to expense for outgoing scheduled payments
        transactionDto.setCategory("Scheduled Payment");
        transactionDto.setStatus("SCHEDULED");
        transactionDto.setIdempotencyKey(UUID.randomUUID().toString());

        return transactionService.createTransaction(transactionDto, dto.getOrgId(), userId);
    }
}
