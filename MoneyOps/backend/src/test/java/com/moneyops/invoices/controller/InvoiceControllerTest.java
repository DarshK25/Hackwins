// src/test/java/com/moneyops/invoices/controller/InvoiceControllerTest.java
package com.moneyops.invoices.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.moneyops.invoices.dto.InvoiceDto;
import com.moneyops.invoices.service.InvoiceService;
import com.moneyops.shared.utils.OrgContext;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
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
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.moneyops.auth.security.AuthEntryPoint;
import com.moneyops.auth.security.JwtFilter;
import com.moneyops.auth.security.OAuth2SuccessHandler;
import com.moneyops.auth.security.ServiceTokenFilter;

import org.springframework.security.test.context.support.WithMockUser;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;

import com.moneyops.auth.security.JwtProvider;

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
    private ServiceTokenFilter serviceTokenFilter;

    @MockBean
    private JwtFilter jwtFilter;

    @MockBean
    private org.springframework.security.core.userdetails.UserDetailsService userDetailsService;

    @Autowired
    private ObjectMapper objectMapper;

    private String orgId;
    private String userId;

    @BeforeEach
    public void setup() {
        orgId = UUID.randomUUID().toString();
        userId = UUID.randomUUID().toString();
        OrgContext.setOrgId(orgId);
        OrgContext.setUserId(userId);
    }

    @AfterEach
    public void tearDown() {
        OrgContext.clear();
    }

    @Test
    public void testCreateInvoice() throws Exception {
        InvoiceDto dto = new InvoiceDto();
        dto.setInvoiceNumber("INV-001");
        dto.setClientId(UUID.randomUUID().toString());
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
                .content(objectMapper.writeValueAsString(dto)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.invoiceNumber").value("INV-001"));
    }

    @Test
    public void testGetInvoice() throws Exception {
        String id = UUID.randomUUID().toString();
        InvoiceDto dto = new InvoiceDto();
        dto.setId(id);
        dto.setInvoiceNumber("INV-001");

        when(invoiceService.getInvoiceById(id, orgId)).thenReturn(dto);

        mockMvc.perform(get("/api/invoices/{id}", id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(id));
    }

    @Test
    public void testGetAllInvoices() throws Exception {
        InvoiceDto dto1 = new InvoiceDto();
        dto1.setInvoiceNumber("INV-001");
        InvoiceDto dto2 = new InvoiceDto();
        dto2.setInvoiceNumber("INV-002");

        when(invoiceService.searchInvoices(eq(orgId), anyString(), anyString(), anyString(), anyInt())).thenReturn(Arrays.asList(dto1, dto2));

        mockMvc.perform(get("/api/invoices"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2));
    }
}