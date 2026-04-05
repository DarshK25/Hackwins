package com.moneyops.invites;

import com.resend.Resend;
import com.resend.core.exception.ResendException;
import com.resend.services.emails.model.CreateEmailOptions;
import com.resend.services.emails.model.CreateEmailResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import jakarta.annotation.PostConstruct;

@Service
@Slf4j
public class EmailService {

    @Value("${RESEND_API_KEY}")
    private String resendApiKey;

    @Value("${VITE_FRONTEND_URL:http://localhost:5173}")
    private String frontendUrl;

    @Value("${RESEND_FROM_EMAIL:onboarding@resend.dev}")
    private String fromEmail;

    private Resend resend;

    @PostConstruct
    public void init() {
        if (resendApiKey == null || resendApiKey.isEmpty()) {
            log.error("RESEND_API_KEY is missing from environment variables!");
        }
        this.resend = new Resend(resendApiKey);
    }

    public void sendInviteEmail(String toEmail, String token, String orgName, String role) {
        String inviteLink = frontendUrl + "/invite/" + token;
        
        log.info("Attempting to send invite email to {} using sender {}", toEmail, fromEmail);
        
        CreateEmailOptions params = CreateEmailOptions.builder()
                .from(fromEmail)
                .to(toEmail)
                .subject("You're invited to " + (orgName != null ? orgName : "MoneyOps") + " 🚀")
                    .html("<div style='font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;'>" +
                          "  <h2 style='color: #4CBB17;'>You've been invited to " + (orgName != null ? orgName : "MoneyOps") + "</h2>" +
                          "  <p>You have been added as a <strong>" + (role != null ? role : "MEMBER") + "</strong>.</p>" +
                          "  <p>Your workspace owner will share the team security code with you directly.</p>" +
                          "  <p>Accept your invitation by clicking the button below:</p>" +
                          "  <a href='" + inviteLink + "' style='display:inline-block; padding: 12px 24px; background-color: #4CBB17; color: white; text-decoration: none; border-radius: 6px; font-weight: bold;'>Accept Invitation</a>" +
                          "  <p style='margin-top: 20px; font-size: 12px; color: #999;'>If the button doesn't work, copy and paste this link: " + inviteLink + "</p>" +
                          "</div>")
                    .build();

        try {
            CreateEmailResponse data = resend.emails().send(params);
            if (data != null && data.getId() != null) {
                log.info("Invite email sent successfully. ID: {}", data.getId());
            } else {
                log.error("Resend API returned a success but no ID was provided. Check API dashboard.");
                throw new RuntimeException("Email response missing ID");
            }
        } catch (ResendException e) {
            log.error("RESEND API ERROR: Failed to send invite email to {}. Details: {}", toEmail, e.getMessage());
            log.error("Resend error name: {}, message: {}", e.getClass().getSimpleName(), e.getMessage());
            throw new RuntimeException("Failed to send email to " + toEmail + ": " + e.getMessage(), e);
        } catch (Exception e) {
            log.error("UNEXPECTED ERROR: during email sending:", e);
            throw e;
        }
    }

    /**
     * Sends a notification email to members when the team security code is changed.
     * This method is called when the team owner updates the security code.
     */
    public void sendSecurityCodeChangeEmail(String toEmail, String subject, String htmlContent) {
        log.info("Attempting to send security code change notification to {} using sender {}", toEmail, fromEmail);
        
        CreateEmailOptions params = CreateEmailOptions.builder()
                .from(fromEmail)
                .to(toEmail)
                .subject(subject)
                .html(htmlContent)
                .build();

        try {
            CreateEmailResponse data = resend.emails().send(params);
            if (data != null && data.getId() != null) {
                log.info("Security code change notification sent successfully to {}. ID: {}", toEmail, data.getId());
            } else {
                log.error("Resend API returned a success but no ID was provided for email to {}. Check API dashboard.", toEmail);
                throw new RuntimeException("Email response missing ID");
            }
        } catch (ResendException e) {
            log.error("RESEND API ERROR: Failed to send security code change email to {}. Details: {}", toEmail, e.getMessage());
            log.error("Resend error name: {}, message: {}", e.getClass().getSimpleName(), e.getMessage());
            throw new RuntimeException("Failed to send email to " + toEmail + ": " + e.getMessage(), e);
        } catch (Exception e) {
            log.error("UNEXPECTED ERROR: during security code change email sending:", e);
            throw e;
        }
    }

    public void sendInvoiceEmail(String toEmail, String subject, String htmlContent) {
        log.info("Attempting to send invoice email to {} using sender {}", toEmail, fromEmail);

        CreateEmailOptions params = CreateEmailOptions.builder()
                .from(fromEmail)
                .to(toEmail)
                .subject(subject)
                .html(htmlContent)
                .build();

        try {
            CreateEmailResponse data = resend.emails().send(params);
            if (data != null && data.getId() != null) {
                log.info("Invoice email sent successfully to {}. ID: {}", toEmail, data.getId());
            } else {
                log.error("Resend API returned a success but no ID was provided for invoice email to {}. Check API dashboard.", toEmail);
                throw new RuntimeException("Email response missing ID");
            }
        } catch (ResendException e) {
            log.error("RESEND API ERROR: Failed to send invoice email to {}. Details: {}", toEmail, e.getMessage());
            log.error("Resend error name: {}, message: {}", e.getClass().getSimpleName(), e.getMessage());
            throw new RuntimeException("Failed to send email to " + toEmail + ": " + e.getMessage(), e);
        } catch (Exception e) {
            log.error("UNEXPECTED ERROR: during invoice email sending:", e);
            throw e;
        }
    }

    public void sendInvoiceFollowUp(String toEmail, String invoiceNumber, String clientName,
                                     String orgName, String dueDate, String amount) {
        String safeClientName = clientName != null ? clientName : "there";
        String safeOrgName = orgName != null ? orgName : "MoneyOps";
        String formattedAmount = formatInr(amount);

        log.info("Sending follow-up email for invoice {} to {}", invoiceNumber, toEmail);

        String subject = "Reminder: Invoice " + invoiceNumber + " is overdue";
        String html = "<div style='font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;'>" +
            "  <h2 style='color: #E53E3E;'>Payment Reminder</h2>" +
            "  <p>Dear " + safeClientName + ",</p>" +
            "  <p>This is a friendly reminder that your invoice <strong>" + invoiceNumber + "</strong> from " + safeOrgName + " is past its due date.</p>" +
            "  <div style='background-color: #f9f9f9; padding: 16px; border-radius: 8px; margin: 20px 0;'>" +
            "    <p style='margin: 0 0 8px; color: #666;'>Invoice Number: <strong style='color: #111;'>" + invoiceNumber + "</strong></p>" +
            "    <p style='margin: 0 0 8px; color: #666;'>Due Date: <strong style='color: #111;'>" + (dueDate != null ? dueDate : "N/A") + "</strong></p>" +
            "    <p style='margin: 0; color: #666;'>Amount Due: <strong style='color: #111; font-size: 18px;'>" + formattedAmount + "</strong></p>" +
            "  </div>" +
            "  <p>Please arrange payment at your earliest convenience. If you have already paid, kindly disregard this message or reply to confirm.</p>" +
            "  <p style='margin-top: 24px;'>Thank you,<br/>" + safeOrgName + "</p>" +
            "  <p style='margin-top: 24px; font-size: 12px; color: #999;'>Sent via MoneyOps</p>" +
            "</div>";

        CreateEmailOptions params = CreateEmailOptions.builder()
                .from(fromEmail)
                .to(toEmail)
                .subject(subject)
                .html(html)
                .build();

        try {
            CreateEmailResponse data = resend.emails().send(params);
            if (data != null && data.getId() != null) {
                log.info("Follow-up email sent for invoice {} to {}. ID: {}", invoiceNumber, toEmail, data.getId());
            } else {
                log.error("Resend API returned success but no ID for follow-up email to {}", toEmail);
                throw new RuntimeException("Email response missing ID");
            }
        } catch (ResendException e) {
            log.error("RESEND API ERROR: Failed to send follow-up email for invoice {} to {}. Details: {}", invoiceNumber, toEmail, e.getMessage());
            throw new RuntimeException("Failed to send follow-up email: " + e.getMessage(), e);
        } catch (Exception e) {
            log.error("UNEXPECTED ERROR: during follow-up email sending:", e);
            throw e;
        }
    }

    private String formatInr(String amount) {
        try {
            double val = Double.parseDouble(amount.replace(",", "").trim());
            return "INR " + String.format("%,.2f", val);
        } catch (Exception e) {
            return "INR " + amount;
        }
    }
}
