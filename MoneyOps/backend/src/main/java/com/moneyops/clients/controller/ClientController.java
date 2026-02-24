// src/main/java/com/moneyops/clients/controller/ClientController.java
package com.moneyops.clients.controller;

import com.moneyops.clients.dto.ClientDto;
import com.moneyops.clients.service.ClientService;
import com.moneyops.shared.utils.OrgContext;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/clients")
public class ClientController {

    @Autowired
    private ClientService clientService;

    @GetMapping
    public ResponseEntity<List<ClientDto>> getAllClients(
            @RequestHeader(value = "X-Org-Id", required = false) String orgIdStr) {
        UUID orgId = parseUuid(orgIdStr);
        if (orgId == null) orgId = OrgContext.getOrgId();
        org.slf4j.LoggerFactory.getLogger(ClientController.class).info("Fetching all clients for orgId: {}", orgId);
        List<ClientDto> clients = clientService.getAllClients(orgId);
        return ResponseEntity.ok(clients);
    }

    @GetMapping("/{id}")
    public ResponseEntity<ClientDto> getClientById(
            @PathVariable String id, 
            @RequestHeader(value = "X-Org-Id", required = false) String orgIdStr) {
        UUID orgId = parseUuid(orgIdStr);
        if (orgId == null) orgId = OrgContext.getOrgId();
        ClientDto client = clientService.getClientById(id, orgId);
        return ResponseEntity.ok(client);
    }

    @PostMapping
    public ResponseEntity<ClientDto> createClient(
            @RequestBody ClientDto dto, 
            @RequestHeader(value = "X-Org-Id", required = false) String orgIdStr, 
            @RequestHeader(value = "X-User-Id", required = false) String createdByStr) {
        UUID orgId = parseUuid(orgIdStr);
        UUID createdBy = parseUuid(createdByStr);
        
        if (orgId == null) orgId = OrgContext.getOrgId();
        if (createdBy == null) createdBy = OrgContext.getUserId();
        
        org.slf4j.LoggerFactory.getLogger(ClientController.class).info("Creating client '{}' for orgId: {} by user: {}", dto.getName(), orgId, createdBy);
        
        ClientDto created = clientService.createClient(dto, orgId, createdBy);
        return ResponseEntity.ok(created);
    }

    @PutMapping("/{id}")
    public ResponseEntity<ClientDto> updateClient(
            @PathVariable String id, 
            @RequestBody ClientDto dto, 
            @RequestHeader(value = "X-Org-Id", required = false) String orgIdStr, 
            @RequestHeader(value = "X-User-Id", required = false) String updatedByStr) {
        UUID orgId = parseUuid(orgIdStr);
        UUID updatedBy = parseUuid(updatedByStr);
        ClientDto updated = clientService.updateClient(id, dto, orgId, updatedBy);
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteClient(
            @PathVariable String id, 
            @RequestHeader(value = "X-Org-Id", required = false) String orgIdStr) {
        UUID orgId = parseUuid(orgIdStr);
        clientService.deleteClient(id, orgId);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/search")
    public ResponseEntity<List<ClientDto>> searchClients(
            @RequestParam String q, 
            @RequestHeader(value = "X-Org-Id", required = false) String orgIdStr) {
        UUID orgId = parseUuid(orgIdStr);
        if (orgId == null) orgId = OrgContext.getOrgId();
        List<ClientDto> clients = clientService.searchClients(orgId, q);
        return ResponseEntity.ok(clients);
    }

    private UUID parseUuid(String uuidStr) {
        if (uuidStr == null || uuidStr.isEmpty() || "unknown".equalsIgnoreCase(uuidStr) || uuidStr.startsWith("placeholder")) {
            return null;
        }
        try {
            return UUID.fromString(uuidStr);
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
}
