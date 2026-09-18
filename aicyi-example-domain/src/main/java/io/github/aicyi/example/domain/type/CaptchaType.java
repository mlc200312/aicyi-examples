package io.github.aicyi.example.domain.type;

import io.github.aicyi.commons.lang.EnumType;

/**
 * @author Mr.Min
 * @description 邮件类型枚举
 * @date 19:18
 **/
public enum CaptchaType implements EnumType {
    IMAGE_CAPTCHA_TYPE(0, "图形验证码"),
    LOGIN_CAPTCHA_TYPE(1, "登录邮件验证码"),
    REGISTER_CAPTCHA_TYPE(2, "注册邮件验证码"),
    UPDATE_PASSWORD_CAPTCHA_TYPE(3, "修改密码邮件验证码"),
    ;

    private final Integer code;
    private final String description;

    CaptchaType(Integer code, String description) {
        this.code = code;
        this.description = description;
    }

    @Override
    public Integer getCode() {
        return code;
    }

    @Override
    public String getDescription() {
        return description;
    }
}
