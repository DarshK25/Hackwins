package com.moneyops.organizations.service;

import com.moneyops.organizations.dto.BusinessOrganizationDto;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.mapper.OrganizationMapper;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.organizations.repository.RegulatoryProfileRepository;
import com.moneyops.organizations.validator.OrganizationValidator;
import com.moneyops.users.entity.User;
import com.moneyops.users.repository.UserRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class OrganizationServiceTest {

    @Mock
    private BusinessOrganizationRepository orgRepository;

    @Mock
    private RegulatoryProfileRepository regulatoryRepository;

    @Mock
    private OrganizationMapper mapper;

    @Mock
    private OrganizationValidator validator;

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private OrganizationService organizationService;

    @Test
    void getMyOrganizationReturnsActiveOrganizationForOrgMember() {
        User user = new User();
        user.setId("user-1");
        user.setOrgId("org-1");

        BusinessOrganization organization = new BusinessOrganization();
        organization.setId("org-1");
        organization.setLegalName("MoneyOps Workspace");

        BusinessOrganizationDto dto = new BusinessOrganizationDto();
        dto.setId("org-1");
        dto.setLegalName("MoneyOps Workspace");

        when(userRepository.findByIdAndDeletedAtIsNull("user-1")).thenReturn(Optional.of(user));
        when(orgRepository.findByIdAndDeletedAtIsNull("org-1")).thenReturn(Optional.of(organization));
        when(mapper.toDto(organization)).thenReturn(dto);

        BusinessOrganizationDto result = organizationService.getMyOrganization("user-1");

        assertEquals("org-1", result.getId());
        assertEquals("MoneyOps Workspace", result.getLegalName());
        verify(orgRepository).findByIdAndDeletedAtIsNull("org-1");
    }
}
