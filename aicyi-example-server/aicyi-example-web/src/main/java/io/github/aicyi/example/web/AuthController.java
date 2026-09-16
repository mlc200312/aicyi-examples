package io.github.aicyi.example.web;

import io.github.aicyi.commons.lang.model.Result;
import io.github.aicyi.commons.core.token.AuthenticationTokens;
import io.github.aicyi.commons.core.token.TokenPair;
import io.github.aicyi.example.domain.bo.LoginParam;
import io.github.aicyi.example.domain.bo.LoginResult;
import io.github.aicyi.example.domain.bo.RegisterParam;
import io.github.aicyi.example.domain.bo.UpdatePasswordParam;
import io.github.aicyi.example.service.AuthService;
import io.github.aicyi.example.web.dto.LoginReq;
import io.github.aicyi.example.web.dto.RefreshTokenReq;
import io.github.aicyi.example.web.dto.RegisterReq;
import io.github.aicyi.example.web.dto.UpdatePasswordReq;
import io.github.aicyi.example.web.mapper.AuthVoMapper;
import io.github.aicyi.example.web.vo.*;
import io.github.aicyi.midware.operatelog.annotation.OperLog;
import io.github.aicyi.midware.web.annotation.IgnoreAuth;
import io.swagger.v3.oas.annotations.tags.Tag;
import io.swagger.v3.oas.annotations.Operation;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

/**
 * @author Mr.Min
 * @description 授权控制器
 * @date 15:45
 **/
@IgnoreAuth
@Tag(name = "授权控制器")
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthVoMapper beanMapper;
    private final AuthService authService;

    @Operation(summary = "注册", description = "注册")
    @RequestMapping(value = "/register", method = RequestMethod.POST)
    public Result<Void> register(@Validated @RequestBody RegisterReq req) {
        RegisterParam param = beanMapper.toRegisterParam(req);
        authService.register(param);
        return Result.success();
    }

    @OperLog(module = "授权控制器", operType = "登录", desc = "用户登录")
    @Operation(summary = "登录", description = "登录")
    @RequestMapping(value = "/login", method = RequestMethod.POST)
    public Result<LoginResp> login(@Validated @RequestBody LoginReq req) {
        LoginParam param = beanMapper.toLoginParam(req);
        LoginResult result = authService.login(param);
        LoginResp resp = beanMapper.toLoginResp(result);
        return Result.success(resp);
    }

    @Operation(summary = "刷新Token接口", description = "刷新Token接口")
    @RequestMapping(value = "/refresh-token", method = RequestMethod.POST)
    public Result<TokenPair> refreshToken(@Validated @RequestBody RefreshTokenReq req) {
        TokenPair tokenPair = AuthenticationTokens.refreshToken(req.getRefreshToken());
        return Result.success(tokenPair);
    }

    @Operation(summary = "更新密码", description = "更新密码")
    @RequestMapping(value = "/update-password", method = RequestMethod.POST)
    public Result<Void> updatePassword(@Validated @RequestBody UpdatePasswordReq req) {
        UpdatePasswordParam param = beanMapper.toUpdatePasswordParam(req);
        authService.updatePassword(param);
        return Result.success();
    }
}
