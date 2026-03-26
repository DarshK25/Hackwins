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
        dto.setOrgId(client.getOrgId());
        dto.setName(client.getName());
        dto.setGstin(client.getGstin());
        dto.setEmail(client.getEmail());
        dto.setPhoneNumber(client.getPhoneNumber());
        
        if (client.getBillingAddress() != null) {
            dto.setBillingAddress(mapAddress(client.getBillingAddress()));
        }
        if (client.getShippingAddress() != null) {
            dto.setShippingAddress(mapAddress(client.getShippingAddress()));
        }
        
        dto.setPaymentTerms(client.getPaymentTerms());
        dto.setCurrency(client.getCurrency());
        dto.setCompany(client.getCompany());
        dto.setNotes(client.getNotes());
        dto.setIdempotencyKey(client.getIdempotencyKey());
        
        if (client.getStatus() != null) {
            dto.setStatus(client.getStatus().name());
        }
        
        dto.setCreatedAt(client.getCreatedAt());
        dto.setUpdatedAt(client.getUpdatedAt());
        dto.setCreatedBy(client.getCreatedBy());
        dto.setCreatedByEmail(client.getCreatedByEmail());
        dto.setCreatedByRole(client.getCreatedByRole());
        dto.setSource(client.getSource());
        dto.setUpdatedBy(client.getUpdatedBy());
        return dto;
    }

    public Client toEntity(ClientDto dto) {
        Client client = new Client();
        if (dto.getId() != null) {
            client.setId(dto.getId());
        }
        client.setOrgId(dto.getOrgId());
        client.setName(dto.getName());
        client.setGstin(dto.getGstin());
        client.setEmail(dto.getEmail());
        client.setPhoneNumber(dto.getPhoneNumber());
        
        if (dto.getBillingAddress() != null) {
            client.setBillingAddress(mapAddress(dto.getBillingAddress()));
        }
        if (dto.getShippingAddress() != null) {
            client.setShippingAddress(mapAddress(dto.getShippingAddress()));
        }
        
        client.setPaymentTerms(dto.getPaymentTerms());
        client.setCurrency(dto.getCurrency());
        client.setCompany(dto.getCompany());
        client.setNotes(dto.getNotes());
        client.setIdempotencyKey(dto.getIdempotencyKey());
        
        if (dto.getStatus() != null) {
            client.setStatus(Client.Status.valueOf(dto.getStatus()));
        }
        
        return client;
    }

    private ClientDto.Address mapAddress(Client.Address addr) {
        ClientDto.Address dto = new ClientDto.Address();
        dto.setLine1(addr.getLine1());
        dto.setLine2(addr.getLine2());
        dto.setCity(addr.getCity());
        dto.setState(addr.getState());
        dto.setCountry(addr.getCountry());
        dto.setPincode(addr.getPincode());
        return dto;
    }

    private Client.Address mapAddress(ClientDto.Address dto) {
        Client.Address addr = new Client.Address();
        addr.setLine1(dto.getLine1());
        addr.setLine2(dto.getLine2());
        addr.setCity(dto.getCity());
        addr.setState(dto.getState());
        addr.setCountry(dto.getCountry());
        addr.setPincode(dto.getPincode());
        return addr;
    }
}