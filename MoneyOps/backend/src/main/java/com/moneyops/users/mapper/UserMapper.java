// src/main/java/com/moneyops/users/mapper/UserMapper.java
package com.moneyops.users.mapper;

import com.moneyops.users.dto.UserDto;
import com.moneyops.users.dto.InviteDto;
import com.moneyops.users.entity.User;
import com.moneyops.users.entity.Invite;
import org.springframework.stereotype.Component;

@Component
public class UserMapper {

    public UserDto toDto(User user) {
        UserDto dto = new UserDto();
        dto.setId(user.getId());
        dto.setName(user.getName());
        dto.setEmail(user.getEmail());
        dto.setPhone(user.getPhone());
        dto.setRole(user.getRole().name());
        dto.setStatus(user.getStatus().name());
        dto.setLastLoginAt(user.getLastLoginAt());
        return dto;
    }

    public User toEntity(UserDto dto) {
        User user = new User();
        user.setId(dto.getId());
        user.setName(dto.getName());
        user.setEmail(dto.getEmail());
        user.setPhone(dto.getPhone());
        user.setRole(User.Role.valueOf(dto.getRole()));
        user.setStatus(User.Status.valueOf(dto.getStatus()));
        user.setLastLoginAt(dto.getLastLoginAt());
        return user;
    }

    public InviteDto toInviteDto(Invite invite) {
        InviteDto dto = new InviteDto();
        dto.setId(invite.getId());
        dto.setEmail(invite.getEmail());
        dto.setRole(invite.getRole().name());
        dto.setExpiresAt(invite.getExpiresAt());
        dto.setStatus(invite.getStatus().name());
        return dto;
    }

    public Invite toInviteEntity(InviteDto dto) {
        Invite invite = new Invite();
        invite.setId(dto.getId());
        invite.setEmail(dto.getEmail());
        invite.setRole(User.Role.valueOf(dto.getRole()));
        invite.setExpiresAt(dto.getExpiresAt());
        invite.setStatus(Invite.InviteStatus.valueOf(dto.getStatus()));
        return invite;
    }
}