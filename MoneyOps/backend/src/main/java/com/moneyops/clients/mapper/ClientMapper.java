// src/main/java/com/moneyops/clients/mapper/ClientMapper.java
package com.moneyops.clients.mapper;

import com.moneyops.clients.dto.ClientDto;
import com.moneyops.clients.entity.Client;
import org.springframework.stereotype.Component;

@Component
public class ClientMapper {

    public ClientDto toDto(Client client) {
        ClientDto dto = new ClientDto();
        dto.setId(client.getId());
        dto.setName(client.getName());
        dto.setTaxId(client.getTaxId());
        dto.setEmail(client.getEmail());
        dto.setPhoneNumber(client.getPhoneNumber());
        dto.setAddress(client.getAddress());
        dto.setCity(client.getCity());
        dto.setState(client.getState());
        dto.setCountry(client.getCountry());
        dto.setPostalCode(client.getPostalCode());
        dto.setPaymentTerms(client.getPaymentTerms());
        dto.setCurrency(client.getCurrency());
        dto.setStatus(client.getStatus().name());
        dto.setCreatedAt(client.getCreatedAt());
        dto.setUpdatedAt(client.getUpdatedAt());
        dto.setCreatedBy(client.getCreatedBy());
        dto.setUpdatedBy(client.getUpdatedBy());
        return dto;
    }

    public Client toEntity(ClientDto dto) {
        Client client = new Client();
        client.setId(dto.getId());
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
        if (dto.getStatus() != null) {
            client.setStatus(Client.Status.valueOf(dto.getStatus()));
        }
        client.setCreatedAt(dto.getCreatedAt());
        client.setUpdatedAt(dto.getUpdatedAt());
        client.setCreatedBy(dto.getCreatedBy());
        client.setUpdatedBy(dto.getUpdatedBy());
        return client;
    }
}