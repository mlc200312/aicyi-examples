package io.github.aicyi.example.mybatisplus.domain.type;

import com.baomidou.mybatisplus.annotation.EnumValue;
import io.github.aicyi.commons.lang.EnumType;
import lombok.Getter;

/**
 * @author Mr.Min
 * @description 性别类型
 * @date 2026/8/21
 **/
@Getter
public enum GenderType implements EnumType {
    MAN(1, "男"), WOMAN(2, "女");

    private final Integer code;
    private final String description;

    GenderType(Integer code, String description) {
        this.code = code;
        this.description = description;
    }
}
