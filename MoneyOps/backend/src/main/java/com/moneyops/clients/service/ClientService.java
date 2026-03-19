// src/main/java/com/moneyops/clients/service/ClientService.java
package com.moneyops.clients.service;

import com.moneyops.clients.dto.ClientDto;
import com.moneyops.clients.entity.Client;
import com.moneyops.clients.mapper.ClientMapper;
import com.moneyops.clients.repository.ClientRepository;
import com.moneyops.clients.validator.ClientValidator;
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

    public List<ClientDto> getAllClients(UUID orgId) {
        if (orgId == null) throw new com.moneyops.shared.exceptions.UnauthorizedException("Missing organization context");
        return clientRepository.findAllByOrgId(orgId)
                .stream()
                .map(clientMapper::toDto)
                .collect(Collectors.toList());
    }

    public ClientDto getClientById(String id, UUID orgId) {
        Client client = clientRepository.findByIdAndOrgId(id, orgId)
                .orElseThrow(() -> new RuntimeException("Client not found"));
        return clientMapper.toDto(client);
    }

    public ClientDto createClient(ClientDto dto, UUID orgId, UUID createdBy) {
        if (orgId == null) throw new com.moneyops.shared.exceptions.UnauthorizedException("Missing organization context");
        if (dto.getStatus() == null || dto.getStatus().trim().isEmpty()) {
            dto.setStatus("ACTIVE");
        }
        clientValidator.validate(dto);
        
        Client client = clientMapper.toEntity(dto);
        if (org.springframework.util.StringUtils.hasText(client.getEmail()) 
            && clientRepository.existsByEmail(client.getEmail())) {
            throw new RuntimeException("Client with this email already exists");
        }
        
        client.setOrgId(orgId);
        client.setCreatedBy(createdBy);
        client.setUpdatedBy(createdBy);
        client.setCreatedAt(LocalDateTime.now());
        client.setUpdatedAt(LocalDateTime.now());

        Client saved = clientRepository.save(client);
        return clientMapper.toDto(saved);
    }

    public ClientDto updateClient(String id, ClientDto dto, UUID orgId, UUID updatedBy) {
        clientValidator.validate(dto);
        Client client = clientRepository.findByIdAndOrgId(id, orgId)
                .orElseThrow(() -> new RuntimeException("Client not found"));

        client.setName(dto.getName());
        client.setTaxId(dto.getTaxId());
        client.setEmail(dto.getEmail());
        client.setPhoneNumber(dto.getPhoneNumber());
        client.setAddress(dto.getAddress());
        client.setCity(dto.getCity());
        client.setState(dto.getState());
        client.setCountry(dto.getCountry());
        client.setPostalCode(dto.getPostalCode());
        client.setPaymentTerms(dto.getPaymentTerms());
        client.setCurrency(dto.getCurrency());
        client.setStatus(Client.Status.valueOf(dto.getStatus()));
        client.setUpdatedBy(updatedBy);
        client.setUpdatedAt(LocalDateTime.now());

        Client saved = clientRepository.save(client);
        return clientMapper.toDto(saved);
    }

    public void deleteClient(String id, UUID orgId) {
        if (!clientRepository.existsByIdAndOrgId(id, orgId)) {
            throw new RuntimeException("Client not found");
        }
        clientRepository.deleteByIdAndOrgId(id, orgId);
    }

    public List<ClientDto> searchClients(UUID orgId, String search) {
        if (search == null || search.trim().isEmpty()) {
            return List.of();
        }

        String query = search.trim().toLowerCase();
        
        // 1. Get potential candidates using Regex (handles partial matches)
        List<Client> candidates = clientRepository.searchByOrgIdWithFilters(orgId, query);
        
        // 2. If no direct regex matches, try getting all active clients to perform full fuzzy matching
        if (candidates.isEmpty()) {
            candidates = clientRepository.findAllByOrgId(orgId);
        }

        // Final copy for lambda capture
        final List<com.moneyops.clients.entity.Client> finalCandidates = candidates;

        // 3. Rank candidates using Jaro-Winkler Similarity
        JaroWinklerSimilarity similarity = new JaroWinklerSimilarity();
        
        return candidates.stream()
                .map(client -> {
                    ClientDto dto = clientMapper.toDto(client);
                    // Compute similarity score
                    double nameScore = similarity.apply(query, client.getName().toLowerCase());
                    double emailScore = client.getEmail() != null ? 
                            similarity.apply(query, client.getEmail().toLowerCase()) : 0;
                    
                    // Use the best score
                    double bestScore = Math.max(nameScore, emailScore);
                    
                    // We can use the score for internal ranking
                    dto.setSearchScore(bestScore);
                    return new ScoredClient(dto, bestScore);
                })
                // Filter out very poor matches (optional threshold, e.g., 0.7)
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