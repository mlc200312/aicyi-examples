# 快速开始

本文档引导你**从零到跑通主应用**（`aicyi-example-boot`），约 10 分钟。其他三个示例应用的启动方式见文末及对应文档。

## 环境要求

| 软件 | 版本 | 用途 |
| --- | --- | --- |
| JDK | **17+** | 运行环境（Spring Boot 3.2 与 BOM `java.version=17` 的最低要求，JDK 8 无法编译） |
| Maven | **3.8.8+** | 构建（`aicyi-base-starter-parent` 的 enforcer 强制 `[3.8.8,)`，低版本直接构建失败） |
| MySQL | 8.0+ | 业务库（t_user / t_student / message_template） |
| Redis | 5.0+ | 缓存、分布式锁、Snowflake WorkerId、Token 存储 |
| Nacos Server | 2.x | 配置中心（所有环境配置存放于此） |
| RabbitMQ | 3.12+ | 仅 `aicyi-example-rabbitmq` 与主应用的 MQ 能力需要（可选，延迟插件需与版本匹配） |
| Docker | 任意 | 快速启动 Nacos / RabbitMQ（推荐） |

> 主应用 `application-{profile}.yml` 中声明了 Nacos 导入清单（含 `aicyi-rabbitmq.yml`），
> 因此**主应用启动时也会连接 RabbitMQ**；若本地未准备 RabbitMQ，可把导入清单中的
> `aicyi-rabbitmq.yml` 移除后重启（见 [常见问题](#常见问题)）。

## 1. 基础设施准备

### 1.1 MySQL

确保本机 MySQL 8 可连接（默认 `localhost:3306`，root/root）。连接参数可在
`nacos/aicyi-datasource.yml` 中调整。

### 1.2 Redis

确保 Redis 可连接（默认 `localhost:6379`，密码 root）。连接参数见 `nacos/aicyi-redis.yml`。

### 1.3 Nacos

启动 Nacos Server（默认 `127.0.0.1:8848`，可用环境变量 `NACOS_SERVER_ADDR` 覆盖）：

```bash
docker run -d --name nacos -p 8848:8848 -e MODE=standalone nacos/nacos-server:v2.2.3
```

创建 test 环境命名空间（本地已内置默认值 `29b4684f-0751-4290-a0a4-f65a51893ef6`），
并把 `nacos/` 目录下的配置逐个导入该命名空间。详细步骤见 [Nacos 配置中心](./infra/nacos.md)。

### 1.4 RabbitMQ（可选）

仅当需要跑主应用的 MQ 能力或 `aicyi-example-rabbitmq` 应用时准备。
Docker 容器、应用账号、延迟插件与交换机/队列拓扑的完整初始化见 [RabbitMQ 本地环境](./infra/rabbitmq.md)。

## 2. 初始化数据库

应用需要 3 张表：`t_user`、`t_student`、`message_template`（库名与连接参数见 `nacos/aicyi-datasource.yml`）。

仓库内的 `aicyi-examples/db/DDL.sql` ：

```bash
mysql -uroot -proot -h127.0.0.1 <库名> < aicyi-examples/db/DDL.sql
```

> **注意：`t_user` / `t_student` 的建表脚本未纳入仓库。**
> 这两张表当初是由 MyBatis Generator 从已有数据库反向生成的（见
> `aicyi-example-dao/src/test/resources/generatorConfig.xml`），仓库里没有对应 DDL。
> 首次搭建需自行创建，否则注册/登录/学生接口会报 `Table '<库名>.t_user' doesn't exist`。
> 字段以实体为准（下划线命名）：
>
> - `t_user`（`domain/entity/base/User.java`）：`id`、`username`、`password`、`mobile`、`email`、`nickname`、
>   `id_card`、`age`、`gender_type`、`birthday`、`deleted`、`version`、`create_time`、`update_time`
> - `t_student`（`domain/entity/base/Student.java`）：`id`、`user_id`、`score`、`grade_type`、
>   `register_time`、`deleted`、`version`、`create_time`、`update_time`
>
> 公共字段（`deleted` / `version` / `create_time` / `update_time`）的类型与默认值约定
> 与 `message_template` 一致，可直接参照其 DDL 补齐；`gender_type` / `grade_type` 为枚举，
> 按 TypeHandler 约定存整型或字符串（参照 `GenderType` / `GradeType`）。

## 3. 构建项目

```bash
# 1) 先构建并安装 aicyi 基础包（BOM/commons/midware）
cd <aicyi-仓库路径>
mvn clean install -DskipTests

# 2) 再构建本工程
cd <aicyi-example-仓库路径>
mvn clean install -DskipTests
```

## 4. 启动主应用

```bash
cd aicyi-example-boot
mvn spring-boot:run
```

启动成功后监听 **80 端口**，日志出现 `Started AicyiExampleApplication` 即成功。

## 5. 验证接口

### 5.1 获取图形验证码（登录需要）

```bash
curl http://localhost/captcha/get-captcha
```

返回 `data.uuid` 与 `data.captcha`（图片地址）。浏览器打开图片地址查看验证码，登录时提交 `uuid` + `verCode`。
（test 环境默认跳过验证码一致性校验，`verCode` 传任意值即可。）

### 5.2 用户注册

```bash
curl -X POST http://localhost/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test",
    "password": "123456",
    "mobile": "13800138000"
  }'
```

### 5.3 用户登录

```bash
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test",
    "password": "123456",
    "uuid": "<5.1 的 uuid>",
    "verCode": "<图片验证码>"
  }'
```

返回 `data.token.accessToken` / `data.token.refreshToken`。

### 5.4 访问需认证接口

```bash
curl http://localhost/user/get-user-info \
  -H "Authorization: Bearer <5.3 的 accessToken>"
```

### 5.5 刷新 Token

```bash
curl -X POST http://localhost/api/auth/refresh-token \
  -H "Content-Type: application/json" \
  -d '{ "refreshToken": "<5.3 的 refreshToken>" }'
```

### 5.6 查看接口文档

框架提供两套并存的文档 UI（均由 springdoc-openapi 2.5.0 输出的 OpenAPI 3.0 文档驱动）：

| 入口 | 说明 |
| --- | --- |
| `http://localhost/apidoc/index.html` | 自研 layui UI（推荐），支持分组切换、Token 调试、Mock 示例 |
| `http://localhost/api-doc.html` | 跳板页，自动转向上面的自研 UI（保留 `#` 与查询串，兼容旧书签） |
| `http://localhost/swagger-ui/index.html` | springdoc 自带的官方 Swagger UI |

数据端点：`/v3/api-docs`（全量）、`/v3/api-docs/swagger-config`（分组清单）、
`/v3/api-docs/{group}`（分组文档，本项目为 `all` / `auth` / `biz`）。

在自研 UI 里调试需鉴权的接口：先调 `/api/auth/login` 取 `accessToken`，填入页面顶部的
Token 输入框，后续请求会自动补全 `Authorization: Bearer <token>` 头。

> 全部接口清单与请求/响应示例见 [apps/aicyi-example-boot.md](./apps/aicyi-example-boot.md)。

## 6. 其他应用快速启动

| 应用 | 端口 | 前置 | 启动命令 | 文档 |
| --- | --- | --- | --- | --- |
| `aicyi-example-mybatisplus` | 8081 | MySQL + Nacos | `cd aicyi-example-mybatisplus && mvn spring-boot:run` | [apps/mybatisplus.md](./apps/aicyi-example-mybatisplus.md) |
| `aicyi-example-rabbitmq` | 8082 | RabbitMQ + Nacos | `cd aicyi-example-rabbitmq && mvn spring-boot:run` | [apps/rabbitmq.md](./apps/aicyi-example-rabbitmq.md) |
| `aicyi-example-xxljob` | 8083 | XXL-Job 调度中心 + Nacos | `cd aicyi-example-xxljob && mvn spring-boot:run` | [apps/xxljob.md](./apps/aicyi-example-xxljob.md) |

> 所有应用均通过 Nacos 拉取配置，启动前请先完成 [Nacos 配置导入](./infra/nacos.md)。

## 常见问题

### Q: 启动报 Nacos 配置导入失败？

Nacos 未启动、namespace 不对，或 `nacos/` 下的 Data ID 未完整导入目标命名空间。核对
`NACOS_SERVER_ADDR` / `NACOS_NAMESPACE` 环境变量；导入为非 optional，缺失即启动失败。

### Q: 启动报 Redis / MySQL 连接失败？

检查 `nacos/aicyi-redis.yml` / `nacos/aicyi-datasource.yml` 中的 host/port/账号密码是否与本机一致。

### Q: 没有 RabbitMQ 也能启动主应用吗？

可以。编辑 `aicyi-example-boot/src/main/resources/application-test.yml`，从 `spring.config.import`
中移除 `nacos:aicyi-rabbitmq.yml?...` 这一行（并同步移除 `application-prod.yml` 中对应行）即可；
主应用其余能力不受影响。

### Q: 如何跑单元/集成测试？

boot 模块内测试直接依赖本机 Redis/MySQL：
`mvn test -pl aicyi-example-boot`。纯单测在 `aicyi-example-test` 模块：`mvn test -pl aicyi-example-test`。

### Q: 访问 `/apidoc/index.html` 或 `/v3/api-docs` 返回的是一段 JSON 错误体？

说明请求被鉴权拦截器拦下了。`@EnableMidwareWeb` 的 `excludePathPatterns` 必须同时放行文档 UI
与其数据端点（注意 springdoc 2.x 是 `/v3/api-docs`，不是 springfox 时代的 `/v2/api-docs`）：

```java
@EnableMidwareWeb(excludePathPatterns = {
        "/apidoc/**", "/api-doc.html",      // 自研 UI 与跳板页
        "/swagger-ui/**", "/webjars/**",    // 官方 Swagger UI 及其 webjars 资源
        "/v3/api-docs/**"                   // OpenAPI 数据端点（含 /swagger-config 与分组）
})
```

本项目的全局异常处理器会把未命中静态资源的请求也转成 HTTP 200 + JSON 错误体，
所以**不能仅凭状态码判断资源是否存在**，要看响应体是不是 `{"code":...,"message":...}` 信封。
