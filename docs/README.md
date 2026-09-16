
> 基于 **aicyi** 框架（Spring Boot 3.2 / JDK 17）的多模块示例工程，演示框架各核心能力的落地用法。
> 适合作为新项目脚手架参考，或新手快速熟悉框架的入门工程。

## 项目简介

aicyi-example 是一个典型的分层多模块 Spring Boot 工程，覆盖：

- **Web 接口**：统一响应 `Result`、JWT 认证、图形/邮件/短信验证码、用户与学生 CRUD、OpenAPI 3 接口文档（springdoc + 自研 layui UI）
- **数据访问**：MyBatis（Generator 生成）+ MyBatis-Plus（自动 CRUD、代码生成器）
- **中间件**：Redis（缓存/分布式锁/Snowflake）、RabbitMQ（Spring Cloud Stream 消息）、XXL-Job（定时任务）
- **配置中心**：全部环境配置存放于 Nacos，通过 `spring.config.import` 拉取
- **测试**：框架能力单测 + 集成测试示例

## 模块结构

```
aicyi-examples
├── aicyi-example-boot        # 主应用（可运行，端口 80）：Web/认证/消息/缓存/Snowflake
├── aicyi-example-web         # Controller 层：Auth/Captcha/User/Student
├── aicyi-example-service     # Service 层：业务实现 + 统一消息调用
├── aicyi-example-domain      # 领域模型：BO/DTO/DO/Entity/枚举/错误码
├── aicyi-example-dao         # DAO 层：MyBatis Mapper
├── aicyi-example-test        # 纯单测：commons 工具/安全模块测试
├── aicyi-example-mybatisplus # MyBatis-Plus 示例应用（可运行，端口 8081）
├── aicyi-example-rabbitmq    # RabbitMQ 消息应用（可运行，端口 8082）
├── aicyi-example-xxljob      # XXL-Job 定时任务应用（可运行，端口 8083）
├── nacos/                    # Nacos 配置中心 YAML（Data ID 与模块导入一一对应）
├── db/                       # 初始化脚本 db/schema.sql
└── docs/                     # 使用文档（本目录）
```

## 可运行应用一览

| 应用 | 端口 | 说明 | 文档 |
| --- | --- | --- | --- |
| `aicyi-example-boot` | 80 | 主 Web 应用：认证/验证码/用户/学生/消息/缓存/Snowflake | [apps/boot.md](./apps/aicyi-example-boot.md) |
| `aicyi-example-mybatisplus` | 8081 | MyBatis-Plus 示例：自动 CRUD + 代码生成器 | [apps/mybatisplus.md](./apps/aicyi-example-mybatisplus.md) |
| `aicyi-example-rabbitmq` | 8082 | RabbitMQ 消息：生产者/消费者（direct/topic/delayed） | [apps/rabbitmq.md](./apps/aicyi-example-rabbitmq.md) |
| `aicyi-example-xxljob` | 8083 | XXL-Job 定时任务执行器 | [apps/xxljob.md](./apps/aicyi-example-xxljob.md) |

## 技术栈

| 类别 | 技术 | 版本 |
| --- | --- | --- |
| 语言 | Java | 17 |
| 框架 | Spring Boot / Spring Cloud | 3.2.8 / 2023.0.3 |
| 配置中心 | Nacos (Spring Cloud Alibaba) | 2023.0.1.2 |
| ORM | MyBatis / MyBatis-Plus | 3.0.3 / 3.5.7 |
| 数据库 | MySQL | 8.0.x |
| 缓存 | Redis (Redisson / Caffeine) | - |
| 消息队列 | RabbitMQ (Spring Cloud Stream) | - |
| 认证 | JWT (jjwt) | 0.13.0 |
| 定时任务 | XXL-Job | 2.5.0 |
| 接口文档 | springdoc-openapi (OpenAPI 3) | 2.5.0 |

## 依赖说明

- 本工程依赖 **aicyi 基础包**（`io.github.aicyi.base` / `io.github.aicyi.commons` / `io.github.aicyi.midware`），
  需先从 aicyi 仓库执行 `mvn clean install -DskipTests` 安装到本地仓库。
- 所有可运行应用均从 **Nacos** 读取环境配置，启动前必须先导入 `nacos/` 目录下的配置。

## 文档导航

**新手入门**
- [快速开始](./quickstart.md) — 从零到跑通主应用：环境 → 数据库 → Nacos → 构建 → 启动 → 验证接口

**应用说明**
- [aicyi-example-boot](./apps/aicyi-example-boot.md) — 主应用：接口清单、核心配置、测试
- [aicyi-example-mybatisplus](./apps/aicyi-example-mybatisplus.md) — MyBatis-Plus 应用
- [aicyi-example-rabbitmq](./apps/aicyi-example-rabbitmq.md) — RabbitMQ 消息应用
- [aicyi-example-xxljob](./apps/aicyi-example-xxljob.md) — XXL-Job 定时任务应用

**基础设施**
- [Nacos 配置中心](./infra/nacos.md) — 环境隔离、Data ID 清单、导入步骤
- [RabbitMQ 本地环境](./infra/rabbitmq.md) — 容器、账号、延迟插件、拓扑初始化

**进阶**
- [集成 aicyi 到自有项目](./framework-integration.md) — 依赖引入、注解、配置、常见问题
