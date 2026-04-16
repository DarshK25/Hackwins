package com.moneyops.invites;

import jakarta.mail.internet.MimeMessage;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Service;

@Service
@Slf4j
@RequiredArgsConstructor
public class EmailService {

    private final JavaMailSender mailSender;

    @Value("${VITE_FRONTEND_URL:http://localhost:5173}")
    private String frontendUrl;

    @Value("${app.mail.from-address:no-reply@moneyops.local}")
    private String fromEmail;

    @Value("${app.mail.from-name:MoneyOps}")
    private String fromName;

    public void sendInviteEmail(String toEmail, String token, String orgName, String role) {
        String inviteLink = frontendUrl + "/invite/" + token;
        String safeOrgName = orgName != null ? orgName : "MoneyOps";
        String safeRole = role != null ? role : "MEMBER";

        String subject = "You're invited to " + safeOrgName;
        String html = "<div style='font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;'>"
                + "<h2 style='color: #4CBB17;'>You've been invited to " + safeOrgName + "</h2>"
                + "<p>You have been added as a <strong>" + safeRole + "</strong>.</p>"
                + "<p>Your workspace owner will share the team security code with you directly.</p>"
                + "<p>Accept your invitation by clicking the button below:</p>"
                + "<a href='" + inviteLink + "' style='display:inline-block; padding: 12px 24px; background-color: #4CBB17; color: white; text-decoration: none; border-radius: 6px; font-weight: bold;'>Accept Invitation</a>"
                + "<p style='margin-top: 20px; font-size: 12px; color: #999;'>If the button doesn't work, copy and paste this link: " + inviteLink + "</p>"
                + "</div>";

        sendHtmlEmail(toEmail, subject, html);
    }

    public void sendSecurityCodeChangeEmail(String toEmail, String subject, String htmlContent) {
        sendHtmlEmail(toEmail, subject, htmlContent);
    }

    public void sendInvoiceEmail(String toEmail, String subject, String htmlContent) {
        sendHtmlEmail(toEmail, subject, htmlContent);
    }

    public void sendInvoiceFollowUp(String toEmail, String invoiceNumber, String clientName,
                                    String orgName, String dueDate, String amount) {
        String safeClientName = clientName != null ? clientName : "there";
        String safeOrgName = orgName != null ? orgName : "MoneyOps";
        String formattedAmount = formatInr(amount);

        String subject = "Reminder: Invoice " + invoiceNumber + " is overdue";
        String html = "<div style='font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;'>"
                + "<h2 style='color: #E53E3E;'>Payment Reminder</h2>"
                + "<p>Dear " + safeClientName + ",</p>"
                + "<p>This is a friendly reminder that your invoice <strong>" + invoiceNumber + "</strong> from " + safeOrgName + " is past its due date.</p>"
                + "<div style='background-color: #f9f9f9; padding: 16px; border-radius: 8px; margin: 20px 0;'>"
                + "<p style='margin: 0 0 8px; color: #666;'>Invoice Number: <strong style='color: #111;'>" + invoiceNumber + "</strong></p>"
                + "<p style='margin: 0 0 8px; color: #666;'>Due Date: <strong style='color: #111;'>" + (dueDate != null ? dueDate : "N/A") + "</strong></p>"
                + "<p style='margin: 0; color: #666;'>Amount Due: <strong style='color: #111; font-size: 18px;'>" + formattedAmount + "</strong></p>"
                + "</div>"
                + "<p>Please arrange payment at your earliest convenience. If you have already paid, kindly disregard this message or reply to confirm.</p>"
                + "<p style='margin-top: 24px;'>Thank you,<br/>" + safeOrgName + "</p>"
                + "<p style='margin-top: 24px; font-size: 12px; color: #999;'>Sent via MoneyOps</p>"
                + "</div>";

        sendHtmlEmail(toEmail, subject, html);
    }

    private void sendHtmlEmail(String toEmail, String subject, String htmlContent) {
        try {
            MimeMessage mimeMessage = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(mimeMessage, "UTF-8");
            helper.setFrom(fromEmail, fromName);
            helper.setTo(toEmail);
            helper.setSubject(subject);
            helper.setText(htmlContent, true);
            mailSender.send(mimeMessage);
            log.info("SMTP email sent to {} with subject {}", toEmail, subject);
        } catch (Exception e) {
            log.error("SMTP email send failed for {}", toEmail, e);
            throw new RuntimeException("Failed to send email to " + toEmail + ": " + e.getMessage(), e);
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
