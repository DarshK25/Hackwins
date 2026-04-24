package com.moneyops.onboarding.service;

import com.moneyops.onboarding.dto.OnboardingRequest;
import com.moneyops.onboarding.dto.OnboardingStatusResponse;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.users.entity.User;
import com.moneyops.users.repository.InviteRepository;
import com.moneyops.users.repository.UserRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.List;
import java.util.Optional;

import static org.mockito.ArgumentMatchers.any;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class OnboardingServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private BusinessOrganizationRepository orgRepository;

    @Mock
    private InviteRepository inviteRepository;

    @Mock
    private PasswordEncoder passwordEncoder;

    @InjectMocks
    private OnboardingService onboardingService;

    @Test
    void getStatusReturnsNewUserWhenIdentityDoesNotExist() {
        when(userRepository.findByClerkIdAndDeletedAtIsNull("clerk-new")).thenReturn(Optional.empty());

        OnboardingStatusResponse response = onboardingService.getStatus("clerk-new");

        assertFalse(response.isOnboardingComplete());
        assertNull(response.getUserId());
        assertNull(response.getOrgId());
        assertEquals("New user - onboarding required", response.getMessage());
    }

    @Test
    void getStatusPreservesUserWhenWorkspaceWasDeleted() {
        User user = new User();
        user.setId("user-1");
        user.setClerkId("clerk-1");
        user.setEmail("user@example.com");
        user.setOrgId("org-deleted");
        user.setOnboardingComplete(true);

        when(userRepository.findByClerkIdAndDeletedAtIsNull("clerk-1")).thenReturn(Optional.of(user));
        when(orgRepository.findByIdAndDeletedAtIsNull("org-deleted")).thenReturn(Optional.empty());
        when(orgRepository.findAllByCreatedByAndDeletedAtIsNull("user-1")).thenReturn(List.of());

        OnboardingStatusResponse response = onboardingService.getStatus("clerk-1");

        assertFalse(response.isOnboardingComplete());
        assertEquals("user-1", response.getUserId());
        assertNull(response.getOrgId());
        assertEquals("Previous workspace unavailable - onboarding required", response.getMessage());
        verify(userRepository).save(user);
        verify(userRepository, never()).delete(user);
        assertNull(user.getOrgId());
        assertFalse(user.isOnboardingComplete());
    }

    @Test
    void getStatusHealsUserWhenCreatedWorkspaceStillExists() {
        User user = new User();
        user.setId("user-2");
        user.setClerkId("clerk-2");
        user.setEmail("owner@example.com");
        user.setOnboardingComplete(false);

        BusinessOrganization org = new BusinessOrganization();
        org.setId("org-2");

        when(userRepository.findByClerkIdAndDeletedAtIsNull("clerk-2")).thenReturn(Optional.of(user));
        when(orgRepository.findAllByCreatedByAndDeletedAtIsNull("user-2")).thenReturn(List.of(org));

        OnboardingStatusResponse response = onboardingService.getStatus("clerk-2");

        assertTrue(response.isOnboardingComplete());
        assertEquals("user-2", response.getUserId());
        assertEquals("org-2", response.getOrgId());
        assertEquals("Onboarding complete", response.getMessage());
        verify(userRepository).save(user);
        verify(userRepository, never()).delete(user);
        assertEquals("org-2", user.getOrgId());
        assertTrue(user.isOnboardingComplete());
    }

    @Test
    void getStatusRelinksExistingUserByEmailWhenClerkIdChanges() {
        User user = new User();
        user.setId("user-3");
        user.setClerkId("old-clerk");
        user.setEmail("owner@example.com");
        user.setOrgId("org-3");
        user.setOnboardingComplete(true);

        BusinessOrganization org = new BusinessOrganization();
        org.setId("org-3");

        when(userRepository.findByClerkIdAndDeletedAtIsNull("new-clerk")).thenReturn(Optional.empty());
        when(userRepository.findByEmailIgnoreCaseAndDeletedAtIsNull("owner@example.com")).thenReturn(Optional.of(user));
        when(userRepository.save(user)).thenReturn(user);
        when(orgRepository.findByIdAndDeletedAtIsNull("org-3")).thenReturn(Optional.of(org));

        OnboardingStatusResponse response = onboardingService.getStatus("new-clerk", "Owner@Example.com");

        assertTrue(response.isOnboardingComplete());
        assertEquals("user-3", response.getUserId());
        assertEquals("org-3", response.getOrgId());
        assertEquals("new-clerk", user.getClerkId());
        verify(userRepository).save(user);
    }

    @Test
    void createBusinessDoesNotCreateDuplicateOrgWhenEmailBelongsToOnboardedUser() {
        User user = new User();
        user.setId("user-4");
        user.setClerkId("old-clerk");
        user.setEmail("owner@example.com");
        user.setOrgId("org-4");
        user.setOnboardingComplete(true);
        user.setRole(User.Role.OWNER);

        BusinessOrganization org = new BusinessOrganization();
        org.setId("org-4");

        OnboardingRequest request = new OnboardingRequest();
        request.setClerkId("new-clerk");
        request.setEmail("owner@example.com");
        request.setLegalName("Duplicate Attempt LLC");

        when(userRepository.findByClerkIdAndDeletedAtIsNull("new-clerk")).thenReturn(Optional.empty());
        when(userRepository.findByEmailIgnoreCaseAndDeletedAtIsNull("owner@example.com")).thenReturn(Optional.of(user));
        when(userRepository.save(user)).thenReturn(user);
        when(orgRepository.findByIdAndDeletedAtIsNull("org-4")).thenReturn(Optional.of(org));

        OnboardingStatusResponse response = onboardingService.createBusiness(request);

        assertTrue(response.isOnboardingComplete());
        assertEquals("user-4", response.getUserId());
        assertEquals("org-4", response.getOrgId());
        assertEquals("Business already exists for this account", response.getMessage());
        assertEquals(User.Role.OWNER, user.getRole());
        verify(orgRepository, never()).save(any(BusinessOrganization.class));
    }
}
