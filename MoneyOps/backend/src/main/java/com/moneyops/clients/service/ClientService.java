// src/main/java/com/moneyops/clients/service/ClientService.java
package com.moneyops.clients.service;

import com.moneyops.clients.dto.ClientDto;
import com.moneyops.clients.entity.Client;
import com.moneyops.clients.mapper.ClientMapper;
import com.moneyops.clients.repository.ClientRepository;
import com.moneyops.clients.validator.ClientValidator;
import com.moneyops.audit.service.AuditLogService;
import com.moneyops.security.team.TeamActionAuthorizationService;
import com.moneyops.users.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;
import org.apache.commons.text.similarity.JaroWinklerSimilarity;

@Service
@Transactional
public class ClientService {

    @Autowired
    private ClientRepository clientRepository;

    @Autowired
    private ClientMapper clientMapper;

    @Autowired
    private ClientValidator clientValidator;

    @Autowired
    private TeamActionAuthorizationService teamActionAuthorizationService;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private AuditLogService auditLogService;

    public List<ClientDto> getAllClients(String orgId) {
        if (orgId == null || orgId.isBlank()) throw new com.moneyops.shared.exceptions.UnauthorizedException("Missing organization context");
        return clientRepository.findAllByOrgIdAndDeletedAtIsNull(orgId)
                .stream()
                .map(clientMapper::toDto)
                .collect(Collectors.toList());
    }

    public ClientDto getClientById(String id, String orgId) {
        Client client = clientRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new RuntimeException("Client not found"));
        return clientMapper.toDto(client);
    }

    public ClientDto createClient(ClientDto dto, String orgId, String createdBy) {
        if (orgId == null || orgId.isBlank()) throw new com.moneyops.shared.exceptions.UnauthorizedException("Missing organization context");

        if (createdBy == null || createdBy.isBlank()) {
            throw new com.moneyops.shared.exceptions.UnauthorizedException("Missing user context");
        }

        // Enforce protected create rules (membership + active status + PIN).
        var creator = teamActionAuthorizationService.assertUserCanCreateSensitiveAction(
                orgId,
                createdBy,
                dto.getTeamActionCode()
        );

        // Default source to MANUAL if caller didn't specify.
        if (dto.getSource() == null || dto.getSource().isBlank()) {
            dto.setSource("MANUAL");
        }

        // ✨ Idempotency check
        if (dto.getIdempotencyKey() != null && clientRepository.existsByEmailAndDeletedAtIsNull(dto.getEmail())) {
             // For simplicity, we check email uniqueness but you could check idempotencyKey explicitly if tracked
        }

        if (dto.getStatus() == null || dto.getStatus().trim().isEmpty()) {
            dto.setStatus("ACTIVE");
        }
        clientValidator.validate(dto);
        
        Client client = clientMapper.toEntity(dto);
        if (client.getEmail() != null && !client.getEmail().isBlank() 
            && clientRepository.existsByEmailAndDeletedAtIsNull(client.getEmail())) {
            throw new RuntimeException("Client with this email already exists");
        }
        
        client.setOrgId(orgId);

        // Protected-action creator metadata
        client.setCreatedBy(creator.userId());
        client.setCreatedByEmail(creator.email());
        client.setCreatedByRole(creator.role());
        client.setSource(dto.getSource());
        client.setCreatedAt(LocalDateTime.now());
        client.setUpdatedAt(LocalDateTime.now());
        
        Client saved = clientRepository.save(client);
        auditLogService.logCreate("CLIENT", saved.getId(), saved);
        return clientMapper.toDto(saved);
    }

    public ClientDto updateClient(String id, ClientDto dto, String orgId, String updatedBy) {
        clientValidator.validate(dto);
        Client client = clientRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new RuntimeException("Client not found"));

        client.setName(dto.getName());
        client.setGstin(dto.getGstin());
        client.setEmail(dto.getEmail());
        client.setPhoneNumber(dto.getPhoneNumber());
        
        if (dto.getBillingAddress() != null) {
            client.setBillingAddress(clientMapper.toEntity(dto).getBillingAddress()); // Simplified reuse
        }
        if (dto.getShippingAddress() != null) {
            client.setShippingAddress(clientMapper.toEntity(dto).getShippingAddress());
        }
        
        client.setPaymentTerms(dto.getPaymentTerms());
        client.setCurrency(dto.getCurrency());
        client.setCompany(dto.getCompany());
        client.setNotes(dto.getNotes());
        
        if (dto.getStatus() != null) {
            client.setStatus(Client.Status.valueOf(dto.getStatus()));
        }

        Client saved = clientRepository.save(client);
        return clientMapper.toDto(saved);
    }

    public void deleteClient(String id, String orgId) {
        Client client = clientRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new RuntimeException("Client not found"));
        
        // ✨ Soft Delete
        client.setDeletedAt(LocalDateTime.now());
        clientRepository.save(client);
    }

    public List<ClientDto> searchClients(String orgId, String search) {
        if (search == null || search.trim().isEmpty()) {
            return List.of();
        }

        String query = search.trim().toLowerCase();
        
        // 1. Get potential candidates using Regex
        List<Client> candidates = clientRepository.searchByOrgIdWithFilters(orgId, query);
        
        // 2. perform full fuzzy matching if no direct regex matches
        if (candidates.isEmpty()) {
            candidates = clientRepository.findAllByOrgIdAndDeletedAtIsNull(orgId);
        }

        final List<com.moneyops.clients.entity.Client> finalCandidates = candidates;
        JaroWinklerSimilarity similarity = new JaroWinklerSimilarity();
        
        return candidates.stream()
                .map(client -> {
                    ClientDto dto = clientMapper.toDto(client);
                    double nameScore = similarity.apply(query, client.getName().toLowerCase());
                    double emailScore = client.getEmail() != null ? 
                            similarity.apply(query, client.getEmail().toLowerCase()) : 0;
                    double bestScore = Math.max(nameScore, emailScore);
                    dto.setSearchScore(bestScore);
                    return new ScoredClient(dto, bestScore);
                })
                .filter(sc -> sc.score > 0.7 || finalCandidates.size() < 10) 
                .sorted(Comparator.comparingDouble((ScoredClient sc) -> sc.score).reversed())
                .map(sc -> sc.client)
                .collect(Collectors.toList());
    }

    // Helper class for ranking
    private static class ScoredClient {
        ClientDto client;
        double score;
        ScoredClient(ClientDto client, double score) {
            this.client = client;
            this.score = score;
        }
    }
}