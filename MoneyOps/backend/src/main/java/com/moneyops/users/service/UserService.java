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

    public List<UserDto> getAllUsers(String orgId) {
        return userRepository.findAllByOrgIdAndDeletedAtIsNull(orgId)
                .stream()
                .map(userMapper::toDto)
                .collect(Collectors.toList());
    }

    public UserDto getUserById(String id, String orgId) {
        User user = userRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new RuntimeException("User not found"));
        return userMapper.toDto(user);
    }

    public UserDto createUser(UserDto dto, String orgId, String createdBy) {
        userValidator.validate(dto);
        if (userRepository.existsByEmailAndOrgIdAndDeletedAtIsNull(dto.getEmail(), orgId)) {
            throw new RuntimeException("User with this email already exists");
        }

        User user = userMapper.toEntity(dto);
        user.setOrgId(orgId);
        user.setCreatedBy(createdBy);

        User saved = userRepository.save(user);
        auditLogService.logCreate("User", saved.getId(), saved);
        return userMapper.toDto(saved);
    }

    public UserDto updateUser(String id, UserDto dto, String orgId, String updatedBy) {
        userValidator.validate(dto);
        User user = userRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
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

        User saved = userRepository.save(user);
        auditLogService.logUpdate("User", saved.getId(), oldUser, saved);
        return userMapper.toDto(saved);
    }

    public void deleteUser(String id, String orgId) {
        User user = userRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new RuntimeException("User not found"));
        
        // ✨ Soft Delete
        user.setDeletedAt(LocalDateTime.now());
        userRepository.save(user);
        
        auditLogService.logDelete("User", id, user);
    }

    public List<UserDto> searchUsers(String orgId, String search) {
        return userRepository.searchByOrgIdWithFilters(orgId, search)
                .stream()
                .map(userMapper::toDto)
                .collect(Collectors.toList());
    }

    public Invite createInvite(CreateInviteRequest request, String orgId, String createdBy) {
        userValidator.validateInvite(request);
        if (inviteRepository.existsByEmailAndOrgIdAndStatusAndDeletedAtIsNull(request.getEmail(), orgId, Invite.InviteStatus.PENDING)) {
            throw new RuntimeException("Invite already exists for this email");
        }

        Invite invite = new Invite();
        invite.setEmail(request.getEmail());
        invite.setRole(User.Role.valueOf(request.getRole()));
        invite.setToken(UUID.randomUUID().toString().substring(0, 8).toUpperCase());
        invite.setExpiresAt(LocalDateTime.now().plusDays(7));
        invite.setStatus(Invite.InviteStatus.PENDING);
        invite.setOrgId(orgId);
        invite.setCreatedBy(createdBy);

        return inviteRepository.save(invite);
    }

    public UserDto acceptInvite(AcceptInviteRequest request) {
        inviteValidator.validateAcceptInvite(request);

        Invite invite = inviteRepository.findByTokenAndDeletedAtIsNull(request.getToken())
                .orElseThrow(() -> new RuntimeException("Invalid invite token"));

        if (invite.getExpiresAt().isBefore(LocalDateTime.now())) {
            throw new RuntimeException("Invite has expired");
        }

        if (Invite.InviteStatus.PENDING != invite.getStatus()) {
            throw new RuntimeException("Invite has already been used");
        }

        User user = new User();
        user.setName(request.getName());
        user.setEmail(invite.getEmail());
        user.setRole(invite.getRole());
        user.setStatus(User.Status.ACTIVE);
        user.setPasswordHash(hashPassword(request.getPassword()));
        user.setOrgId(invite.getOrgId());
        user.setCreatedBy(invite.getCreatedBy());

        User saved = userRepository.save(user);

        invite.setStatus(Invite.InviteStatus.ACCEPTED);
        inviteRepository.save(invite);

        return userMapper.toDto(saved);
    }

    public List<Invite> getPendingInvites(String orgId) {
        return inviteRepository.findAllByOrgIdAndStatusAndDeletedAtIsNull(orgId, Invite.InviteStatus.PENDING);
    }

    private String hashPassword(String password) {
        return passwordEncoder.encode(password);
    }
}