// src/main/java/com/moneyops/clients/controller/ClientController.java
package com.moneyops.clients.controller;

import com.moneyops.clients.dto.ClientDto;
import com.moneyops.clients.service.ClientService;
import com.moneyops.shared.utils.OrgContext;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/clients")
public class ClientController {

    @Autowired
    private ClientService clientService;

    @GetMapping
    public ResponseEntity<List<ClientDto>> getAllClients(
            @RequestHeader(value = "X-Org-Id", required = false) String orgId) {
        if (orgId == null || orgId.isEmpty()) orgId = OrgContext.getOrgId();
        List<ClientDto> clients = clientService.getAllClients(orgId);
        return ResponseEntity.ok(clients);
    }

    @GetMapping("/{id}")
    public ResponseEntity<ClientDto> getClientById(
            @PathVariable String id, 
            @RequestHeader(value = "X-Org-Id", required = false) String orgId) {
        if (orgId == null || orgId.isEmpty()) orgId = OrgContext.getOrgId();
        ClientDto client = clientService.getClientById(id, orgId);
        return ResponseEntity.ok(client);
    }

    @PostMapping
    public ResponseEntity<ClientDto> createClient(
            @RequestBody ClientDto dto, 
            @RequestHeader(value = "X-Org-Id", required = false) String orgIdHeader,
            @RequestHeader(value = "X-User-Id", required = false) String createdByHeader) {

        String orgId = OrgContext.getOrgId();
        String createdBy = OrgContext.getUserId();

        // Fallback for non-standard dev requests (but still prefer OrgContext).
        if (orgId == null || orgId.isEmpty()) orgId = orgIdHeader;
        if (createdBy == null || createdBy.isEmpty()) createdBy = createdByHeader;

        ClientDto created = clientService.createClient(dto, orgId, createdBy);
        return ResponseEntity.ok(created);
    }

    @PutMapping("/{id}")
    public ResponseEntity<ClientDto> updateClient(
            @PathVariable String id, 
            @RequestBody ClientDto dto, 
            @RequestHeader(value = "X-Org-Id", required = false) String orgId, 
            @RequestHeader(value = "X-User-Id", required = false) String updatedBy) {
        if (orgId == null || orgId.isEmpty()) orgId = OrgContext.getOrgId();
        if (updatedBy == null || updatedBy.isEmpty()) updatedBy = OrgContext.getUserId();
        ClientDto updated = clientService.updateClient(id, dto, orgId, updatedBy);
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteClient(
            @PathVariable String id, 
            @RequestHeader(value = "X-Org-Id", required = false) String orgId) {
        if (orgId == null || orgId.isEmpty()) orgId = OrgContext.getOrgId();
        clientService.deleteClient(id, orgId);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/search")
    public ResponseEntity<List<ClientDto>> searchClients(
            @RequestParam String q, 
            @RequestHeader(value = "X-Org-Id", required = false) String orgId) {
        if (orgId == null || orgId.isEmpty()) orgId = OrgContext.getOrgId();
        List<ClientDto> clients = clientService.searchClients(orgId, q);
        return ResponseEntity.ok(clients);
    }
}
