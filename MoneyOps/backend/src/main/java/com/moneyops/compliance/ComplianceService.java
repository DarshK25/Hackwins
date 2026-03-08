package com.moneyops.compliance;

import org.springframework.stereotype.Service;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

@Service
public class ComplianceService {

    @Data
    public static class DeadlineDTO {
        private String id;
        private String title;
        private String dueDate;
        private String type;
        private String priority;

        public DeadlineDTO(String id, String title, String dueDate, String type, String priority) {
            this.id = id;
            this.title = title;
            this.dueDate = dueDate;
            this.type = type;
            this.priority = priority;
        }
    }

    @Data
    public static class DeadlinesResponse {
        private List<DeadlineDTO> deadlines = new ArrayList<>();
    }

    @Data
    public static class TdsCalcRequest {
        private BigDecimal amount;
        private String category;
        private Boolean isIndividual;
    }

    @Data
    public static class TdsCalculationResponse {
        private String section;
        private double rate;
        private String deductible;
    }

    public DeadlinesResponse getDeadlines(Long businessId) {
        // Build mock deadlines matching UI expectations
        DeadlinesResponse response = new DeadlinesResponse();
        int currentYear = LocalDate.now().getYear();
        int nextMonth = LocalDate.now().getMonthValue() == 12 ? 1 : LocalDate.now().getMonthValue() + 1;
        int deadlineYear = LocalDate.now().getMonthValue() == 12 ? currentYear + 1 : currentYear;
        
        String monthFormatted = String.format("%02d", nextMonth);
        
        response.getDeadlines().add(new DeadlineDTO(
            "1", 
            "GST Filing (Current Month)", 
            deadlineYear + "-" + monthFormatted + "-20", 
            "GST", 
            "high"
        ));
        
        response.getDeadlines().add(new DeadlineDTO(
            "2", 
            "TDS Payment", 
            deadlineYear + "-" + monthFormatted + "-07", 
            "TDS", 
            "high"
        ));
        
        response.getDeadlines().add(new DeadlineDTO(
            "3", 
            "Quarterly Advance Tax", 
            currentYear + "-03-15", 
            "TAX", 
            "medium"
        ));
        
        return response;
    }

    public TdsCalculationResponse calculateTds(TdsCalcRequest request) {
        TdsCalculationResponse response = new TdsCalculationResponse();
        BigDecimal amount = request.getAmount() != null ? request.getAmount() : BigDecimal.ZERO;

        String category = request.getCategory() != null ? request.getCategory().toLowerCase() : "professional";
        boolean isInd = request.getIsIndividual() != null ? request.getIsIndividual() : true;
        
        double rate = 10.0;
        String section = "194J";

        // Implement logic syncing directly with standard Indian Tax protocols
        switch (category) {
            case "professional":
                rate = 10.0;
                section = "194J";
                break;
            case "contract":
                rate = isInd ? 1.0 : 2.0;
                section = "194C";
                break;
            case "rent":
                rate = 10.0;
                section = "194I";
                break;
            case "commission":
                rate = 5.0;
                section = "194H";
                break;
            default:
                rate = 10.0;
                section = "194J";
        }

        response.setRate(rate);
        response.setSection(section);
        
        BigDecimal deductible = amount.multiply(BigDecimal.valueOf(rate)).divide(BigDecimal.valueOf(100));
        response.setDeductible(String.format(Locale.US, "%.2f", deductible.doubleValue()));

        return response;
    }
}
