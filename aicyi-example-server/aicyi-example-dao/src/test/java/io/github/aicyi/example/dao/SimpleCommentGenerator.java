package io.github.aicyi.example.dao;

import org.apache.commons.lang3.StringUtils;
import org.mybatis.generator.api.IntrospectedColumn;
import org.mybatis.generator.api.IntrospectedTable;
import org.mybatis.generator.api.dom.java.Field;
import org.mybatis.generator.api.dom.java.TopLevelClass;
import org.mybatis.generator.internal.DefaultCommentGenerator;

/**
 * @author Mr.Min
 * @description 业务描述
 * @date 2025/9/29
 **/
public class SimpleCommentGenerator extends DefaultCommentGenerator {

    /**
     * 生成模型注释
     *
     * @param topLevelClass     类
     * @param introspectedTable 表
     */
    public void addModelClassComment(TopLevelClass topLevelClass, IntrospectedTable introspectedTable) {
        String remarks = introspectedTable.getRemarks();
        remarks = StringUtils.isEmpty(remarks) ? "" : remarks + ":";
        remarks = remarks.replace("\n", " ");

        topLevelClass.addJavaDocLine("/**");
        topLevelClass.addJavaDocLine(" * " + remarks + introspectedTable.getFullyQualifiedTable());
        topLevelClass.addJavaDocLine(" */");
    }

    /**
     * 生成字段注释
     *
     * @param field              字段
     * @param introspectedTable  表
     * @param introspectedColumn 表列
     */
    @Override
    public void addFieldComment(Field field, IntrospectedTable introspectedTable, IntrospectedColumn introspectedColumn) {
        String remarks = introspectedColumn.getRemarks();
        remarks = StringUtils.isEmpty(remarks) ? "" : remarks + ":";
        remarks = remarks.replace("\n", " ");

        field.addJavaDocLine("/**");
        field.addJavaDocLine(" * " + remarks + introspectedColumn.getActualColumnName());
        field.addJavaDocLine(" */");
    }
}
