package io.github.aicyi.example.dao;

import org.mybatis.generator.api.IntrospectedColumn;
import org.mybatis.generator.api.dom.java.FullyQualifiedJavaType;
import org.mybatis.generator.internal.types.JavaTypeResolverDefaultImpl;


import java.util.HashMap;
import java.util.Map;

public class MyJavaTypeResolver extends JavaTypeResolverDefaultImpl {

    // 添加Doris特有类型映射
    public MyJavaTypeResolver() {
        super();

        // 添加Doris特有类型识别
        dbColumnToJavaTypeMap.put(93, new FullyQualifiedJavaType("java.time.LocalDateTime"));
    }

    @Override
    public FullyQualifiedJavaType calculateJavaType(IntrospectedColumn column) {
        // 优先检查特有类型
//        System.out.println("actualColumnName ==> " + column.getActualColumnName());
//        System.out.println("jdbcType ==> " + column.getJdbcType());

        if (column.getActualColumnName().toLowerCase().endsWith("cur")) {
            return new FullyQualifiedJavaType("javax.money.CurrencyUnit");
        }

        if (column.getActualColumnName().toLowerCase().equals("deleted")) {
            return new FullyQualifiedJavaType("io.github.aicyi.commons.lang.type.BooleanType");
        }

        if (dbColumnToJavaTypeMap.containsKey(column.getJdbcType())) {
            return dbColumnToJavaTypeMap.get(column.getJdbcType());
        }

        // 默认处理
        return super.calculateJavaType(column);
    }

    private static final Map<Integer, FullyQualifiedJavaType> dbColumnToJavaTypeMap = new HashMap<>();
}