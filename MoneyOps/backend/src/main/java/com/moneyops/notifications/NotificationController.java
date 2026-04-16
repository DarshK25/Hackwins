package com.moneyops.notifications;

import com.moneyops.invites.EmailService;
import com.moneyops.notifications.dto.EmailRequest;
import com.moneyops.shared.dto.ApiResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/notifications")
@RequiredArgsConstructor
@Slf4j
public class NotificationController {

    private final EmailService emailService;

    @PostMapping("/email")
    public ResponseEntity<ApiResponse<Map<String, Object>>> sendEmail(@RequestBody EmailRequest request) {
        try {
            Map<String, Object> templateData = request.getTemplateData() == null ? Map.of() : request.getTemplateData();
            String type = request.getType() == null ? "GENERAL" : request.getType().trim().toUpperCase();

            if ("PAYMENT_REMINDER".equals(type)) {
                emailService.sendInvoiceFollowUp(
                        request.getRecipientEmail(),
                        String.valueOf(templateData.getOrDefault("invoiceNumber", "")),
                        request.getRecipientName(),
                        String.valueOf(templateData.getOrDefault("businessName", "MoneyOps")),
                        String.valueOf(templateData.getOrDefault("dueDate", "")),
                        String.valueOf(templateData.getOrDefault("amount", "0"))
                );
            } else {
                String subject = String.valueOf(templateData.getOrDefault("subject", "MoneyOps notification"));
                String html = String.valueOf(templateData.getOrDefault("html", "<p>Your MoneyOps notification is ready.</p>"));
                emailService.sendInvoiceEmail(request.getRecipientEmail(), subject, html);
            }

            return ResponseEntity.ok(ApiResponse.success("Email sent", Map.of(
                    "recipientEmail", request.getRecipientEmail(),
                    "type", type
            )));
        } catch (Exception e) {
            log.error("Email send failed", e);
            return ResponseEntity.internalServerError().body(ApiResponse.error(e.getMessage()));
        }
    }
}
