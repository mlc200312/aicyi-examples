package io.github.aicyi.example.web.dto;

import io.github.aicyi.commons.lang.DtoBean;
import io.github.aicyi.midware.web.model.PageRequest;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Getter;
import lombok.Setter;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;


/**
 * @author Mr.Min
 * @description 业务描述
 * @date 15:05
 **/
@Getter
@Setter
@Schema(description = "学生对象请求参数")
public class StudentReq extends PageRequest implements DtoBean {
    @Schema(description = "用户ID")
    private String userIdEq;
    @Schema(description = "班级")
    private String gradeTypeEq;
    @Pattern(regexp = "^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}\\.\\d{3}$",
            message = "日期格式必须为 yyyy-MM-dd HH:mm:ss.SSS")
    @NotBlank
    @Schema(description = "注册开始时间", example = "2020-01-01 00:00:00.000")
    private String registerTimeStart;
    @Pattern(regexp = "^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}\\.\\d{3}$",
            message = "日期格式必须为 yyyy-MM-dd HH:mm:ss.SSS")
    @NotBlank
    @Schema(description = "注册结束时间", example = "2025-08-12 23:59:59.999")
    private String registerTimeEnd;
}
