package io.github.aicyi.example.domain.type;

import io.github.aicyi.commons.lang.EnumType;
import io.github.aicyi.commons.util.json.jackson.EnumTypeJsonDeserializer;
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;

/**
 * @author Mr.Min
 * @description 星期枚举
 * @date 2019-05-21
 **/
@JsonDeserialize(using = EnumTypeJsonDeserializer.class)
public enum Week implements EnumType {
    MON(1, "星期一"),
    TUES(2, "星期二"),
    WED(3, "星期三"),
    THUR(4, "星期四"),
    FRI(5, "星期五"),
    SAT(6, "星期六"),
    SUN(7, "星期七"),
    ;

    private final int code;
    private final String description;

    Week(int code, String description) {
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
