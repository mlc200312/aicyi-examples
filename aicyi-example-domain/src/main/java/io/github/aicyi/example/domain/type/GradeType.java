package io.github.aicyi.example.domain.type;

import io.github.aicyi.commons.lang.StringEnumType;
import io.github.aicyi.commons.util.json.jackson.StringEnumTypeJsonDeserializer;
import com.fasterxml.jackson.annotation.JsonValue;
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;
import lombok.Getter;

/**
 * @author Mr.Min
 * @description 年级枚举
 * @date 2020-03-02
 **/
@JsonDeserialize(using = StringEnumTypeJsonDeserializer.class)
public enum GradeType implements StringEnumType {
    ONE("壹", "一年级"),
    TWO("贰", "二年级"),
    THREE("叁", "三年级"),
    FOUR("肆", "四年级"),
    FIVE("伍", "五年级");

    private final String code;
    @Getter
    private final String description;

    GradeType(String code, String description) {
        this.code = code;
        this.description = description;
    }

    @JsonValue
    public String getCode() {
        return code;
    }

}
