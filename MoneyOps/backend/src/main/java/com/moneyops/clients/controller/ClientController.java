// src/main/java/com/moneyops/clients/controller/ClientController.java
package com.moneyops.clients.controller;

import com.moneyops.clients.dto.ClientDto;
import com.moneyops.clients.service.ClientService;
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
    public ResponseEntity<List<ClientDto>> getAllClients(@RequestHeader("X-Org-Id") UUID orgId) {
        List<ClientDto> clients = clientService.getAllClients(orgId);
        return ResponseEntity.ok(clients);
    }

    @GetMapping("/{id}")
    public ResponseEntity<ClientDto> getClientById(@PathVariable UUID id, @RequestHeader("X-Org-Id") UUID orgId) {
        ClientDto client = clientService.getClientById(id, orgId);
        return ResponseEntity.ok(client);
    }

    @PostMapping
    public ResponseEntity<ClientDto> createClient(@RequestBody ClientDto dto, @RequestHeader("X-Org-Id") UUID orgId, @RequestHeader("X-User-Id") UUID createdBy) {
        ClientDto created = clientService.createClient(dto, orgId, createdBy);
        return ResponseEntity.ok(created);
    }

    @PutMapping("/{id}")
    public ResponseEntity<ClientDto> updateClient(@PathVariable UUID id, @RequestBody ClientDto dto, @RequestHeader("X-Org-Id") UUID orgId, @RequestHeader("X-User-Id") UUID updatedBy) {
        ClientDto updated = clientService.updateClient(id, dto, orgId, updatedBy);
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteClient(@PathVariable UUID id, @RequestHeader("X-Org-Id") UUID orgId) {
        clientService.deleteClient(id, orgId);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/search")
    public ResponseEntity<List<ClientDto>> searchClients(@RequestParam String q, @RequestHeader("X-Org-Id") UUID orgId) {
        List<ClientDto> clients = clientService.searchClients(orgId, q);
        return ResponseEntity.ok(clients);
    }
}