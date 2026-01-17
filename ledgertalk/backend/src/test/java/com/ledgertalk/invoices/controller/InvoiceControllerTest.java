// src/test/java/com/ledgertalk/invoices/controller/InvoiceControllerTest.java
package com.ledgertalk.invoices.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ledgertalk.invoices.dto.InvoiceDto;
import com.ledgertalk.invoices.service.InvoiceService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Arrays;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.ledgertalk.auth.security.AuthEntryPoint;
import com.ledgertalk.auth.security.JwtFilter;
import com.ledgertalk.auth.security.OAuth2SuccessHandler;

import org.springframework.security.test.context.support.WithMockUser;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;

import com.ledgertalk.auth.security.JwtProvider;

@WebMvcTest(InvoiceController.class)
@WithMockUser
public class InvoiceControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private InvoiceService invoiceService;

    @MockBean
    private JwtProvider jwtProvider;

    @MockBean
    private AuthEntryPoint authEntryPoint;

    @MockBean
    private OAuth2SuccessHandler oAuth2SuccessHandler;

    @MockBean
    private org.springframework.security.core.userdetails.UserDetailsService userDetailsService;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    public void testCreateInvoice() throws Exception {
        UUID orgId = UUID.randomUUID();
        UUID userId = UUID.randomUUID();
        InvoiceDto dto = new InvoiceDto();
        dto.setInvoiceNumber("INV-001");
        dto.setClientId(UUID.randomUUID());
        dto.setIssueDate(LocalDate.now());
        dto.setDueDate(LocalDate.now().plusDays(30));
        dto.setStatus("DRAFT");
        dto.setSubtotal(BigDecimal.valueOf(100));
        dto.setGstTotal(BigDecimal.valueOf(18));
        dto.setTotalAmount(BigDecimal.valueOf(118));
        dto.setCurrency("INR");

        when(invoiceService.createInvoice(any(InvoiceDto.class), eq(orgId), eq(userId))).thenReturn(dto);

        mockMvc.perform(post("/api/invoices")
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(dto))
                .header("X-Org-Id", orgId.toString())
                .header("X-User-Id", userId.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.invoiceNumber").value("INV-001"));
    }

    @Test
    public void testGetInvoice() throws Exception {
        UUID id = UUID.randomUUID();
        UUID orgId = UUID.randomUUID();
        InvoiceDto dto = new InvoiceDto();
        dto.setId(id);
        dto.setInvoiceNumber("INV-001");

        when(invoiceService.getInvoiceById(id, orgId)).thenReturn(dto);

        mockMvc.perform(get("/api/invoices/{id}", id)
                .header("X-Org-Id", orgId.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(id.toString()));
    }

    @Test
    public void testGetAllInvoices() throws Exception {
        UUID orgId = UUID.randomUUID();
        InvoiceDto dto1 = new InvoiceDto();
        dto1.setInvoiceNumber("INV-001");
        InvoiceDto dto2 = new InvoiceDto();
        dto2.setInvoiceNumber("INV-002");

        when(invoiceService.getAllInvoices(orgId)).thenReturn(Arrays.asList(dto1, dto2));

        mockMvc.perform(get("/api/invoices")
                .header("X-Org-Id", orgId.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2));
    }
}