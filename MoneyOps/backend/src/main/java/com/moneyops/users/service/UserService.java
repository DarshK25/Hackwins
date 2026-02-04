// src/main/java/com/moneyops/users/service/UserService.java
package com.moneyops.users.service;

import com.moneyops.audit.service.AuditLogService;
import com.moneyops.users.dto.UserDto;
import com.moneyops.users.dto.CreateInviteRequest;
import com.moneyops.users.dto.AcceptInviteRequest;
import com.moneyops.users.entity.User;
import com.moneyops.users.entity.Invite;
import com.moneyops.users.mapper.UserMapper;
import com.moneyops.users.repository.UserRepository;
import com.moneyops.users.repository.InviteRepository;
import com.moneyops.users.validator.UserValidator;
import com.moneyops.users.validator.InviteValidator;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@Transactional
public class UserService {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private InviteRepository inviteRepository;

    @Autowired
    private UserMapper userMapper;

    @Autowired
    private UserValidator userValidator;

    @Autowired
    private InviteValidator inviteValidator;

    @Autowired
    private AuditLogService auditLogService;

    @Autowired
    private org.springframework.security.crypto.password.PasswordEncoder passwordEncoder;

    public List<UserDto> getAllUsers(UUID orgId) {
        return userRepository.findAllByOrgId(orgId)
                .stream()
                .map(userMapper::toDto)
                .collect(Collectors.toList());
    }

    public UserDto getUserById(UUID id, UUID orgId) {
        User user = userRepository.findByIdAndOrgId(id, orgId)
                .orElseThrow(() -> new RuntimeException("User not found"));
        return userMapper.toDto(user);
    }

    public UserDto createUser(UserDto dto, UUID orgId, UUID createdBy) {
        userValidator.validate(dto);
        if (userRepository.existsByEmailAndOrgId(dto.getEmail(), orgId)) {
            throw new RuntimeException("User with this email already exists");
        }

        User user = userMapper.toEntity(dto);
        user.setOrgId(orgId);
        user.setCreatedBy(createdBy);
        user.setUpdatedBy(createdBy);
        user.setCreatedAt(LocalDateTime.now());
        user.setUpdatedAt(LocalDateTime.now());

        User saved = userRepository.save(user);
        auditLogService.logCreate("User", saved.getId().toString(), saved);
        return userMapper.toDto(saved);
    }

    public UserDto updateUser(UUID id, UserDto dto, UUID orgId, UUID updatedBy) {
        userValidator.validate(dto);
        User user = userRepository.findByIdAndOrgId(id, orgId)
                .orElseThrow(() -> new RuntimeException("User not found"));

        User oldUser = new User();
        oldUser.setName(user.getName());
        oldUser.setEmail(user.getEmail());
        oldUser.setRole(user.getRole());
        oldUser.setStatus(user.getStatus());

        user.setName(dto.getName());
        user.setEmail(dto.getEmail());
        user.setRole(User.Role.valueOf(dto.getRole()));
        user.setStatus(User.Status.valueOf(dto.getStatus()));
        user.setUpdatedBy(updatedBy);
        user.setUpdatedAt(LocalDateTime.now());

        User saved = userRepository.save(user);
        auditLogService.logUpdate("User", saved.getId().toString(), oldUser, saved);
        return userMapper.toDto(saved);
    }

    public void deleteUser(UUID id, UUID orgId) {
        User user = userRepository.findByIdAndOrgId(id, orgId)
                .orElseThrow(() -> new RuntimeException("User not found"));
        auditLogService.logDelete("User", id.toString(), user);
        userRepository.deleteByIdAndOrgId(id, orgId);
    }

    public List<UserDto> searchUsers(UUID orgId, String search) {
        return userRepository.searchByOrgIdWithFilters(orgId, search)
                .stream()
                .map(userMapper::toDto)
                .collect(Collectors.toList());
    }

    public void createInvite(CreateInviteRequest request, UUID orgId, UUID createdBy) {
        userValidator.validateInvite(request);
        if (inviteRepository.existsByEmailAndOrgIdAndStatus(request.getEmail(), orgId, Invite.InviteStatus.PENDING)) {
            throw new RuntimeException("Invite already exists for this email");
        }

        Invite invite = new Invite();
        invite.setEmail(request.getEmail());
        invite.setRole(User.Role.valueOf(request.getRole()));
        invite.setToken(UUID.randomUUID().toString());
        invite.setExpiresAt(LocalDateTime.now().plusDays(7));
        invite.setStatus(Invite.InviteStatus.PENDING);
        invite.setOrgId(orgId);
        invite.setCreatedBy(createdBy);
        invite.setCreatedAt(LocalDateTime.now());

        inviteRepository.save(invite);
    }

    public UserDto acceptInvite(AcceptInviteRequest request) {
        inviteValidator.validateAcceptInvite(request);

        Invite invite = inviteRepository.findByToken(request.getToken())
                .orElseThrow(() -> new RuntimeException("Invalid invite token"));

        if (invite.getExpiresAt().isBefore(LocalDateTime.now())) {
            throw new RuntimeException("Invite has expired");
        }

        if (Invite.InviteStatus.PENDING != invite.getStatus()) {
            throw new RuntimeException("Invite has already been used");
        }

        // Create user
        User user = new User();
        user.setName(request.getName());
        user.setEmail(invite.getEmail());
        user.setRole(invite.getRole());
        user.setStatus(User.Status.ACTIVE);
        user.setPasswordHash(hashPassword(request.getPassword())); // Implement password hashing
        user.setOrgId(invite.getOrgId());
        user.setCreatedBy(invite.getCreatedBy());
        user.setUpdatedBy(invite.getCreatedBy());
        user.setCreatedAt(LocalDateTime.now());
        user.setUpdatedAt(LocalDateTime.now());

        User saved = userRepository.save(user);

        // Mark invite as accepted
        invite.setStatus(Invite.InviteStatus.ACCEPTED);
        invite.setUpdatedAt(LocalDateTime.now());
        inviteRepository.save(invite);

        return userMapper.toDto(saved);
    }

    public List<Invite> getPendingInvites(UUID orgId) {
        return inviteRepository.findAllByOrgIdAndStatus(orgId, Invite.InviteStatus.PENDING);
    }

    private String hashPassword(String password) {
        return passwordEncoder.encode(password);
    }
}