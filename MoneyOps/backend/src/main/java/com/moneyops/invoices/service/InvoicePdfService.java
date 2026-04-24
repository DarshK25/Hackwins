package com.moneyops.invoices.service;

import com.lowagie.text.*;
import com.lowagie.text.pdf.*;
import com.moneyops.invoices.entity.Invoice;
import com.moneyops.invoices.entity.InvoiceItem;
import com.moneyops.invoices.entity.InvoiceStatus;
import com.moneyops.invoices.repository.InvoiceRepository;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

@Service
@RequiredArgsConstructor
@Slf4j
public class InvoicePdfService {

    private final InvoiceRepository invoiceRepository;
    private final BusinessOrganizationRepository orgRepository;

    private static final Font TITLE_FONT = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 24, Color.BLACK);
    private static final Font HEADER_FONT = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 12, Color.DARK_GRAY);
    private static final Font NORMAL_FONT = FontFactory.getFont(FontFactory.HELVETICA, 10, Color.BLACK);
    private static final Font BOLD_FONT = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 10, Color.BLACK);
    private static final Font TH_FONT = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 10, Color.WHITE);
    private static final Color PRIMARY_COLOR = new Color(26, 26, 26); // Dark color for headers
    private static final Color ACCENT_COLOR = new Color(76, 187, 23); // MoneyOps Green

    public byte[] getPdfBytes(String invoiceId, String orgId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(invoiceId, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));

        BusinessOrganization org = orgRepository.findByIdAndDeletedAtIsNull(orgId).orElse(null);

        try (ByteArrayOutputStream outputStream = new ByteArrayOutputStream()) {
            Document document = new Document(PageSize.A4, 40, 40, 50, 50);
            PdfWriter writer = PdfWriter.getInstance(document, outputStream);

            // Add PAID Watermark if applicable
            if (invoice.getStatus() == InvoiceStatus.PAID) {
                writer.setPageEvent(new WatermarkPageEvent("PAID"));
            }

            document.open();

            // ── Header Section ───────────────────────────────────────────────
            PdfPTable headerTable = new PdfPTable(2);
            headerTable.setWidthPercentage(100);
            headerTable.setWidths(new float[]{1f, 1f});

            // Company Info (Left)
            PdfPCell companyCell = new PdfPCell();
            companyCell.setBorder(Rectangle.NO_BORDER);
            String orgName = org != null && org.getLegalName() != null ? org.getLegalName() : "MoneyOps";
            companyCell.addElement(new Paragraph(orgName, FontFactory.getFont(FontFactory.HELVETICA_BOLD, 16)));
            if (org != null) {
                if (safe(org.getRegisteredAddress()).length() > 0) {
                    companyCell.addElement(new Paragraph(org.getRegisteredAddress(), NORMAL_FONT));
                }
                if (safe(org.getPrimaryEmail()).length() > 0) {
                    companyCell.addElement(new Paragraph("Email: " + org.getPrimaryEmail(), NORMAL_FONT));
                }
                if (safe(org.getGstin()).length() > 0) {
                    companyCell.addElement(new Paragraph("GSTIN: " + org.getGstin(), BOLD_FONT));
                }
            }
            headerTable.addCell(companyCell);

            // Invoice Title (Right)
            PdfPCell titleCell = new PdfPCell();
            titleCell.setBorder(Rectangle.NO_BORDER);
            titleCell.setHorizontalAlignment(Element.ALIGN_RIGHT);
            Paragraph title = new Paragraph("INVOICE", TITLE_FONT);
            title.setAlignment(Element.ALIGN_RIGHT);
            titleCell.addElement(title);
            Paragraph invNum = new Paragraph("# " + invoice.getInvoiceNumber(), BOLD_FONT);
            invNum.setAlignment(Element.ALIGN_RIGHT);
            titleCell.addElement(invNum);
            headerTable.addCell(titleCell);

            document.add(headerTable);
            document.add(new Paragraph(" "));
            document.add(new Paragraph(" "));

            // ── Invoice Details & Client Info ────────────────────────────────
            PdfPTable detailsTable = new PdfPTable(2);
            detailsTable.setWidthPercentage(100);
            detailsTable.setWidths(new float[]{1f, 1f});

            // Bill To
            PdfPCell billToCell = new PdfPCell();
            billToCell.setBorder(Rectangle.NO_BORDER);
            billToCell.addElement(new Paragraph("BILL TO:", HEADER_FONT));
            billToCell.addElement(new Paragraph(safe(invoice.getClientName()), BOLD_FONT));
            if (safe(invoice.getClientCompany()).length() > 0) {
                billToCell.addElement(new Paragraph(invoice.getClientCompany(), NORMAL_FONT));
            }
            if (safe(invoice.getClientEmail()).length() > 0) {
                billToCell.addElement(new Paragraph(invoice.getClientEmail(), NORMAL_FONT));
            }
            if (safe(invoice.getClientPhone()).length() > 0) {
                billToCell.addElement(new Paragraph(invoice.getClientPhone(), NORMAL_FONT));
            }
            detailsTable.addCell(billToCell);

            // Dates
            PdfPCell datesCell = new PdfPCell();
            datesCell.setBorder(Rectangle.NO_BORDER);
            datesCell.setHorizontalAlignment(Element.ALIGN_RIGHT);

            PdfPTable datesInnerTable = new PdfPTable(2);
            datesInnerTable.setWidthPercentage(60);
            datesInnerTable.setHorizontalAlignment(Element.ALIGN_RIGHT);
            datesInnerTable.setWidths(new float[]{1f, 1f});
            
            datesInnerTable.addCell(buildBorderlessRightCell("Issue Date:", BOLD_FONT));
            datesInnerTable.addCell(buildBorderlessRightCell(formatDate(invoice.getIssueDate()), NORMAL_FONT));
            
            datesInnerTable.addCell(buildBorderlessRightCell("Due Date:", BOLD_FONT));
            datesInnerTable.addCell(buildBorderlessRightCell(formatDate(invoice.getDueDate()), NORMAL_FONT));
            
            datesInnerTable.addCell(buildBorderlessRightCell("Status:", BOLD_FONT));
            datesInnerTable.addCell(buildBorderlessRightCell(invoice.getStatus().name(), NORMAL_FONT));

            datesCell.addElement(datesInnerTable);
            detailsTable.addCell(datesCell);

            document.add(detailsTable);
            document.add(new Paragraph(" "));
            document.add(new Paragraph(" "));

            // ── Line Items Table ─────────────────────────────────────────────
            PdfPTable itemsTable = new PdfPTable(5);
            itemsTable.setWidthPercentage(100);
            itemsTable.setWidths(new float[]{4f, 1f, 1.5f, 1.5f, 2f});
            itemsTable.setSpacingBefore(10f);
            itemsTable.setSpacingAfter(10f);

            // Table Header
            String[] headers = {"Description", "Qty", "Rate", "GST %", "Amount"};
            for (int i = 0; i < headers.length; i++) {
                PdfPCell cell = new PdfPCell(new Phrase(headers[i], TH_FONT));
                cell.setBackgroundColor(PRIMARY_COLOR);
                cell.setPadding(8);
                cell.setHorizontalAlignment(i == 0 ? Element.ALIGN_LEFT : Element.ALIGN_RIGHT);
                itemsTable.addCell(cell);
            }

            // Table Body
            if (invoice.getItems() != null && !invoice.getItems().isEmpty()) {
                boolean alternate = false;
                for (InvoiceItem item : invoice.getItems()) {
                    Color bgColor = alternate ? new Color(245, 245, 245) : Color.WHITE;
                    
                    itemsTable.addCell(buildItemCell(safe(item.getDescription()), Element.ALIGN_LEFT, bgColor));
                    itemsTable.addCell(buildItemCell(String.valueOf(item.getQuantity()), Element.ALIGN_RIGHT, bgColor));
                    itemsTable.addCell(buildItemCell(formatMoney(item.getRate(), invoice.getCurrency()), Element.ALIGN_RIGHT, bgColor));
                    itemsTable.addCell(buildItemCell(item.getGstPercent() + "%", Element.ALIGN_RIGHT, bgColor));
                    itemsTable.addCell(buildItemCell(formatMoney(item.getLineTotal(), invoice.getCurrency()), Element.ALIGN_RIGHT, bgColor));
                    
                    alternate = !alternate;
                }
            } else {
                PdfPCell emptyCell = new PdfPCell(new Phrase("No line items", NORMAL_FONT));
                emptyCell.setColspan(5);
                emptyCell.setPadding(8);
                emptyCell.setHorizontalAlignment(Element.ALIGN_CENTER);
                itemsTable.addCell(emptyCell);
            }
            document.add(itemsTable);

            // ── Totals Section ───────────────────────────────────────────────
            PdfPTable totalsTable = new PdfPTable(2);
            totalsTable.setHorizontalAlignment(Element.ALIGN_RIGHT);
            totalsTable.setWidthPercentage(40);
            totalsTable.setWidths(new float[]{1.5f, 1f});

            totalsTable.addCell(buildTotalsCell("Subtotal:", BOLD_FONT, false));
            totalsTable.addCell(buildTotalsCell(formatMoney(invoice.getSubtotal(), invoice.getCurrency()), NORMAL_FONT, true));

            totalsTable.addCell(buildTotalsCell("GST Total:", BOLD_FONT, false));
            totalsTable.addCell(buildTotalsCell(formatMoney(invoice.getGstTotal(), invoice.getCurrency()), NORMAL_FONT, true));

            PdfPCell grandTotalLbl = buildTotalsCell("Grand Total:", TH_FONT, false);
            grandTotalLbl.setBackgroundColor(ACCENT_COLOR);
            PdfPCell grandTotalVal = buildTotalsCell(formatMoney(invoice.getTotalAmount(), invoice.getCurrency()), TH_FONT, true);
            grandTotalVal.setBackgroundColor(ACCENT_COLOR);
            
            totalsTable.addCell(grandTotalLbl);
            totalsTable.addCell(grandTotalVal);

            if (invoice.getAmountPaid() != null && invoice.getAmountPaid().compareTo(BigDecimal.ZERO) > 0) {
                totalsTable.addCell(buildTotalsCell("Amount Paid:", BOLD_FONT, false));
                totalsTable.addCell(buildTotalsCell(formatMoney(invoice.getAmountPaid(), invoice.getCurrency()), NORMAL_FONT, true));
                
                totalsTable.addCell(buildTotalsCell("Balance Due:", BOLD_FONT, false));
                totalsTable.addCell(buildTotalsCell(formatMoney(invoice.getBalanceDue(), invoice.getCurrency()), BOLD_FONT, true));
            }

            document.add(totalsTable);
            document.add(new Paragraph(" "));

            // ── Notes & Terms ────────────────────────────────────────────────
            if (safe(invoice.getNotes()).length() > 0) {
                document.add(new Paragraph("Notes:", HEADER_FONT));
                document.add(new Paragraph(invoice.getNotes(), NORMAL_FONT));
                document.add(new Paragraph(" "));
            }

            if (safe(invoice.getTermsAndConditions()).length() > 0) {
                document.add(new Paragraph("Terms & Conditions:", HEADER_FONT));
                document.add(new Paragraph(invoice.getTermsAndConditions(), NORMAL_FONT));
            }

            document.close();
            return outputStream.toByteArray();

        } catch (DocumentException | java.io.IOException ex) {
            log.error("Failed to generate PDF", ex);
            throw new RuntimeException("Failed to generate invoice PDF", ex);
        }
    }

    private PdfPCell buildBorderlessRightCell(String text, Font font) {
        PdfPCell cell = new PdfPCell(new Phrase(text, font));
        cell.setBorder(Rectangle.NO_BORDER);
        cell.setHorizontalAlignment(Element.ALIGN_RIGHT);
        cell.setPadding(2);
        return cell;
    }

    private PdfPCell buildItemCell(String text, int alignment, Color bgColor) {
        PdfPCell cell = new PdfPCell(new Phrase(text, NORMAL_FONT));
        cell.setHorizontalAlignment(alignment);
        cell.setVerticalAlignment(Element.ALIGN_MIDDLE);
        cell.setPadding(8);
        cell.setBorderColor(new Color(220, 220, 220));
        cell.setBackgroundColor(bgColor);
        return cell;
    }

    private PdfPCell buildTotalsCell(String text, Font font, boolean isValue) {
        PdfPCell cell = new PdfPCell(new Phrase(text, font));
        cell.setBorder(Rectangle.NO_BORDER);
        cell.setHorizontalAlignment(isValue ? Element.ALIGN_RIGHT : Element.ALIGN_LEFT);
        cell.setPadding(6);
        return cell;
    }

    private String safe(String val) {
        return val == null ? "" : val.trim();
    }

    private String formatDate(LocalDate date) {
        return date == null ? "N/A" : date.format(DateTimeFormatter.ofPattern("dd MMM yyyy"));
    }

    private String formatMoney(BigDecimal amount, String currency) {
        if (amount == null) amount = BigDecimal.ZERO;
        String cur = currency != null ? currency + " " : "";
        return cur + amount.setScale(2, java.math.RoundingMode.HALF_UP).toString();
    }

    // ── Watermark Inner Class ────────────────────────────────────────────────
    static class WatermarkPageEvent extends PdfPageEventHelper {
        private final String watermarkText;

        public WatermarkPageEvent(String watermarkText) {
            this.watermarkText = watermarkText;
        }

        @Override
        public void onEndPage(PdfWriter writer, Document document) {
            PdfContentByte canvas = writer.getDirectContentUnder();
            Phrase watermark = new Phrase(watermarkText, FontFactory.getFont(FontFactory.HELVETICA_BOLD, 120, new Color(200, 200, 200, 100)));
            ColumnText.showTextAligned(canvas, Element.ALIGN_CENTER, watermark, 297.5f, 421, 45);
        }
    }
}
