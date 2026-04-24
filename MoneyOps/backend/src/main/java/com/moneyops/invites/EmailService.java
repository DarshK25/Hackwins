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

    @Value("${RESEND_TO_EMAIL_OVERRIDE:}")
    private String emailRecipientOverride;

    @Value("${RESEND_DEV_MODE_INVOICE_EMAIL:tanushjain0610@gmail.com}")
    private String resendDevModeInvoiceEmail;

    @Value("${EMAIL_DELIVERY_FAIL_OPEN:true}")
    private boolean emailDeliveryFailOpen;

    private Resend resend;

    @PostConstruct
    public void init() {
        if (resendApiKey == null || resendApiKey.isEmpty()) {
            log.error("RESEND_API_KEY is missing from environment variables!");
            if (emailDeliveryFailOpen) {
                return;
            }
        }
        this.resend = new Resend(resendApiKey);
    }

    public void sendInviteEmail(String toEmail, String token, String orgName, String role, String teamActionCode) {
        String inviteLink = frontendUrl + "/invite/" + token;
        String effectiveToEmail = resolveToEmail(toEmail);
        String recipientNotice = buildRecipientOverrideNotice(toEmail);
        
        log.info("Attempting to send invite email to {} using sender {}", effectiveToEmail, fromEmail);
        
        CreateEmailOptions params = CreateEmailOptions.builder()
                .from(fromEmail)
                .to(effectiveToEmail)
                .subject("You're invited to " + (orgName != null ? orgName : "MoneyOps") + " 🚀")
                    .html("<div style='font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;'>" +
                          recipientNotice +
                          "  <h2 style='color: #4CBB17;'>You've been invited to " + (orgName != null ? orgName : "MoneyOps") + "</h2>" +
                          "  <p>You have been added as a <strong>" + (role != null ? role : "MEMBER") + "</strong>.</p>" +
                          "  <p>Your team security code (required to create invoices/clients) is:</p>" +
                          "  <div style='background-color: #f9f9f9; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center;'>" +
                          "    <h1 style='margin: 10px 0; letter-spacing: 3px; color: #333;'>" + teamActionCode + "</h1>" +
                          "  </div>" +
                          "  <p>You can also join by clicking the button below:</p>" +
                          "  <a href='" + inviteLink + "' style='display:inline-block; padding: 12px 24px; background-color: #4CBB17; color: white; text-decoration: none; border-radius: 6px; font-weight: bold;'>Accept Invitation</a>" +
                          "  <p style='margin-top: 20px; font-size: 12px; color: #999;'>If the button doesn't work, copy and paste this link: " + inviteLink + "</p>" +
                          "  <p style='margin-top: 20px; font-size: 12px; color: #999;'>For security, only team members can use this code to create clients and invoices.</p>" +
                          "</div>")
                    .build();

        try {
            CreateEmailResponse data = sendEmail(params, "invite", effectiveToEmail);
            if (data != null && data.getId() != null) {
                log.info("Invite email sent successfully. ID: {}", data.getId());
            } else {
                log.error("Resend API returned a success but no ID was provided. Check API dashboard.");
                handleEmailFailure("invite", effectiveToEmail, new RuntimeException("Email response missing ID"));
            }
        } catch (ResendException e) {
            log.error("RESEND API ERROR: Failed to send invite email to {}. Details: {}", effectiveToEmail, e.getMessage());
            log.error("Resend error name: {}, message: {}", e.getClass().getSimpleName(), e.getMessage());
            handleEmailFailure("invite", effectiveToEmail, e);
        } catch (Exception e) {
            log.error("UNEXPECTED ERROR: during email sending:", e);
            handleEmailFailure("invite", effectiveToEmail, e);
        }
    }

    public void sendTeamInviteEmail(String toEmail, String token, String orgName, String role) {
        String inviteLink = frontendUrl + "/invite/" + token;
        String effectiveToEmail = resolveToEmail(toEmail);
        String recipientNotice = buildRecipientOverrideNotice(toEmail);

        log.info("Attempting to send workspace invite email to {} using sender {}", effectiveToEmail, fromEmail);

        CreateEmailOptions params = CreateEmailOptions.builder()
                .from(fromEmail)
                .to(effectiveToEmail)
                .subject("Invitation to join " + (orgName != null ? orgName : "MoneyOps"))
                .html("<div style='font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;'>" +
                        recipientNotice +
                        "  <h2 style='color: #4CBB17;'>Join " + (orgName != null ? orgName : "MoneyOps") + "</h2>" +
                        "  <p>You have been invited to join the workspace as <strong>" + (role != null ? role : "STAFF") + "</strong>.</p>" +
                        "  <p>Use the secure link below to accept the invitation:</p>" +
                        "  <a href='" + inviteLink + "' style='display:inline-block; padding: 12px 24px; background-color: #4CBB17; color: white; text-decoration: none; border-radius: 6px; font-weight: bold;'>Accept Invitation</a>" +
                        "  <p style='margin-top: 20px; font-size: 12px; color: #999;'>If the button does not work, copy and paste this link: " + inviteLink + "</p>" +
                        "</div>")
                .build();

        try {
            CreateEmailResponse data = sendEmail(params, "workspace invite", effectiveToEmail);
            if (data != null && data.getId() != null) {
                log.info("Workspace invite email sent successfully. ID: {}", data.getId());
            } else {
                handleEmailFailure("workspace invite", effectiveToEmail, new RuntimeException("Email response missing ID"));
            }
        } catch (ResendException e) {
            log.error("Failed to send workspace invite email to {}. Details: {}", effectiveToEmail, e.getMessage());
            handleEmailFailure("workspace invite", effectiveToEmail, e);
        } catch (Exception e) {
            handleEmailFailure("workspace invite", effectiveToEmail, e);
        }
    }

    /**
     * Sends a notification email to members when the team security code is changed.
     * This method is called when the team owner updates the security code.
     */
    public void sendSecurityCodeChangeEmail(String toEmail, String subject, String htmlContent) {
        String effectiveToEmail = resolveToEmail(toEmail);
        String recipientNotice = buildRecipientOverrideNotice(toEmail);

        log.info("Attempting to send security code change notification to {} using sender {}", effectiveToEmail, fromEmail);
        
        CreateEmailOptions params = CreateEmailOptions.builder()
                .from(fromEmail)
                .to(effectiveToEmail)
                .subject(subject)
                .html(injectRecipientNotice(htmlContent, recipientNotice))
                .build();

        try {
            CreateEmailResponse data = sendEmail(params, "security code change", effectiveToEmail);
            if (data != null && data.getId() != null) {
                log.info("Security code change notification sent successfully to {}. ID: {}", toEmail, data.getId());
            } else {
                log.error("Resend API returned a success but no ID was provided for email to {}. Check API dashboard.", toEmail);
                handleEmailFailure("security code change", effectiveToEmail, new RuntimeException("Email response missing ID"));
            }
        } catch (ResendException e) {
            log.error("RESEND API ERROR: Failed to send security code change email to {}. Details: {}", effectiveToEmail, e.getMessage());
            log.error("Resend error name: {}, message: {}", e.getClass().getSimpleName(), e.getMessage());
            handleEmailFailure("security code change", effectiveToEmail, e);
        } catch (Exception e) {
            log.error("UNEXPECTED ERROR: during security code change email sending:", e);
            handleEmailFailure("security code change", effectiveToEmail, e);
        }
    }

    public void sendInvoiceEmail(String toEmail, String subject, String htmlContent) {
        String effectiveToEmail = resolveInvoiceToEmail(toEmail);

        log.info("Attempting to send invoice email to {} using sender {}", effectiveToEmail, fromEmail);

        CreateEmailOptions params = buildInvoiceEmailOptions(toEmail, effectiveToEmail, subject, htmlContent);

        try {
            CreateEmailResponse data = sendEmail(params, "invoice", effectiveToEmail);
            if (data != null && data.getId() != null) {
                log.info("Invoice email sent successfully to {}. ID: {}", toEmail, data.getId());
            } else {
                log.error("Resend API returned a success but no ID was provided for invoice email to {}. Check API dashboard.", toEmail);
                handleEmailFailure("invoice", effectiveToEmail, new RuntimeException("Email response missing ID"));
            }
        } catch (ResendException e) {
            if (shouldRetryInvoiceInDevMode(e, effectiveToEmail)) {
                retryInvoiceEmailInDevMode(toEmail, subject, htmlContent, e);
                return;
            }
            log.error("RESEND API ERROR: Failed to send invoice email to {}. Details: {}", effectiveToEmail, e.getMessage());
            log.error("Resend error name: {}, message: {}", e.getClass().getSimpleName(), e.getMessage());
            handleEmailFailure("invoice", effectiveToEmail, e);
        } catch (Exception e) {
            log.error("UNEXPECTED ERROR: during invoice email sending:", e);
            handleEmailFailure("invoice", effectiveToEmail, e);
        }
    }

    private CreateEmailResponse sendEmail(CreateEmailOptions params, String emailType, String effectiveToEmail)
            throws ResendException {
        if (resend == null) {
            handleEmailFailure(emailType, effectiveToEmail, new IllegalStateException("Resend client is not configured"));
            return null;
        }
        return resend.emails().send(params);
    }

    private void handleEmailFailure(String emailType, String effectiveToEmail, Exception e) {
        if (emailDeliveryFailOpen) {
            log.warn(
                    "{} email delivery to {} failed, but EMAIL_DELIVERY_FAIL_OPEN=true so the app flow will continue. Reason: {}",
                    emailType,
                    effectiveToEmail,
                    e.getMessage()
            );
            return;
        }

        throw new RuntimeException(
                "Failed to send " + emailType + " email to " + effectiveToEmail + ": " + e.getMessage(),
                e
        );
    }

    private String resolveToEmail(String requestedToEmail) {
        String override = trimToNull(emailRecipientOverride);
        if (override == null) {
            return requestedToEmail;
        }

        if (!override.equalsIgnoreCase(requestedToEmail)) {
            log.warn("Email recipient override enabled. Original recipient {} will be routed to {}", requestedToEmail, override);
        }
        return override;
    }

    private String resolveInvoiceToEmail(String requestedToEmail) {
        String override = trimToNull(emailRecipientOverride);
        if (override != null) {
            if (!override.equalsIgnoreCase(requestedToEmail)) {
                log.warn("Email recipient override enabled. Original recipient {} will be routed to {}", requestedToEmail, override);
            }
            return override;
        }

        String devInvoiceEmail = trimToNull(resendDevModeInvoiceEmail);
        if (devInvoiceEmail != null && isUsingResendDevSender() && !devInvoiceEmail.equalsIgnoreCase(requestedToEmail)) {
            log.warn("Resend dev mode detected. Invoice recipient {} will be routed to {}", requestedToEmail, devInvoiceEmail);
            return devInvoiceEmail;
        }

        return requestedToEmail;
    }

    private CreateEmailOptions buildInvoiceEmailOptions(String requestedToEmail, String effectiveToEmail, String subject, String htmlContent) {
        String recipientNotice = buildRecipientOverrideNotice(requestedToEmail, effectiveToEmail);

        return CreateEmailOptions.builder()
                .from(fromEmail)
                .to(effectiveToEmail)
                .subject(subject)
                .html(injectRecipientNotice(htmlContent, recipientNotice))
                .build();
    }

    private boolean shouldRetryInvoiceInDevMode(ResendException exception, String effectiveToEmail) {
        String devInvoiceEmail = trimToNull(resendDevModeInvoiceEmail);
        if (devInvoiceEmail == null || devInvoiceEmail.equalsIgnoreCase(effectiveToEmail)) {
            return false;
        }

        String message = exception != null ? exception.getMessage() : null;
        if (message == null || message.isBlank()) {
            return false;
        }

        String normalizedMessage = message.toLowerCase();
        return normalizedMessage.contains("you can only send testing emails to your own email address")
                || (normalizedMessage.contains("validation_error") && normalizedMessage.contains("verify a domain"));
    }

    private void retryInvoiceEmailInDevMode(String requestedToEmail, String subject, String htmlContent, ResendException originalException) {
        String devInvoiceEmail = trimToNull(resendDevModeInvoiceEmail);
        if (devInvoiceEmail == null) {
            handleEmailFailure("invoice", requestedToEmail, originalException);
            return;
        }

        log.warn(
                "Resend dev mode blocked invoice delivery to {}. Retrying with development recipient {}",
                requestedToEmail,
                devInvoiceEmail
        );

        CreateEmailOptions retryParams = buildInvoiceEmailOptions(requestedToEmail, devInvoiceEmail, subject, htmlContent);
        try {
            CreateEmailResponse retryData = sendEmail(retryParams, "invoice", devInvoiceEmail);
            if (retryData != null && retryData.getId() != null) {
                log.info("Invoice email sent successfully to development recipient {}. ID: {}", devInvoiceEmail, retryData.getId());
                return;
            }

            handleEmailFailure("invoice", devInvoiceEmail, new RuntimeException("Email response missing ID after dev-mode retry"));
        } catch (ResendException retryException) {
            log.error("RESEND API ERROR: Failed to retry invoice email to {}. Details: {}", devInvoiceEmail, retryException.getMessage());
            handleEmailFailure("invoice", devInvoiceEmail, retryException);
        } catch (Exception retryException) {
            log.error("UNEXPECTED ERROR: during invoice email retry:", retryException);
            handleEmailFailure("invoice", devInvoiceEmail, retryException);
        }
    }

    private String buildRecipientOverrideNotice(String requestedToEmail) {
        return buildRecipientOverrideNotice(requestedToEmail, resolveToEmail(requestedToEmail));
    }

    private String buildRecipientOverrideNotice(String requestedToEmail, String effectiveToEmail) {
        if (effectiveToEmail == null || effectiveToEmail.equalsIgnoreCase(requestedToEmail)) {
            return "";
        }

        return "<div style='background:#fff8e1;border:1px solid #ffe082;border-radius:8px;padding:12px;margin-bottom:16px;color:#6d4c00;font-size:13px;'>" +
                "<strong>Development email override:</strong> This email was originally addressed to " +
                escapeHtml(requestedToEmail) + ".</div>";
    }

    private boolean isUsingResendDevSender() {
        String normalizedFromEmail = extractEmailAddress(fromEmail);
        return normalizedFromEmail != null && normalizedFromEmail.toLowerCase().endsWith("@resend.dev");
    }

    private String injectRecipientNotice(String htmlContent, String recipientNotice) {
        if (recipientNotice == null || recipientNotice.isBlank()) {
            return htmlContent;
        }

        return recipientNotice + htmlContent;
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }

        String trimmed = value.trim();
        return trimmed.isBlank() ? null : trimmed;
    }

    private String extractEmailAddress(String value) {
        String trimmed = trimToNull(value);
        if (trimmed == null) {
            return null;
        }

        int start = trimmed.indexOf('<');
        int end = trimmed.indexOf('>');
        if (start >= 0 && end > start) {
            return trimToNull(trimmed.substring(start + 1, end));
        }

        return trimmed;
    }

    private String escapeHtml(String value) {
        if (value == null) {
            return "";
        }

        return value
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;")
                .replace("'", "&#39;");
    }
}
