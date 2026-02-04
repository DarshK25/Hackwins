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
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

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
        return clientRepository.findAllByOrgId(orgId)
                .stream()
                .map(clientMapper::toDto)
                .collect(Collectors.toList());
    }

    public ClientDto getClientById(UUID id, UUID orgId) {
        Client client = clientRepository.findByIdAndOrgId(id, orgId)
                .orElseThrow(() -> new RuntimeException("Client not found"));
        return clientMapper.toDto(client);
    }

    public ClientDto createClient(ClientDto dto, UUID orgId, UUID createdBy) {
        clientValidator.validate(dto);
        if (clientRepository.existsByEmailAndOrgId(dto.getEmail(), orgId)) {
            throw new RuntimeException("Client with this email already exists");
        }

        Client client = clientMapper.toEntity(dto);
        client.setOrgId(orgId);
        client.setCreatedBy(createdBy);
        client.setUpdatedBy(createdBy);
        client.setCreatedAt(LocalDateTime.now());
        client.setUpdatedAt(LocalDateTime.now());

        Client saved = clientRepository.save(client);
        return clientMapper.toDto(saved);
    }

    public ClientDto updateClient(UUID id, ClientDto dto, UUID orgId, UUID updatedBy) {
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

    public void deleteClient(UUID id, UUID orgId) {
        if (!clientRepository.existsByIdAndOrgId(id, orgId)) {
            throw new RuntimeException("Client not found");
        }
        clientRepository.deleteByIdAndOrgId(id, orgId);
    }

    public List<ClientDto> searchClients(UUID orgId, String search) {
        return clientRepository.searchByOrgIdWithFilters(orgId, search)
                .stream()
                .map(clientMapper::toDto)
                .collect(Collectors.toList());
    }
}