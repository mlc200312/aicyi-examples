# aicyi-example-mybatisplus（MyBatis-Plus 示例）

演示 aicyi 的 MyBatis-Plus 增强能力（分页/乐观锁/公共字段自动填充）与官方代码生成器。

- 端口：**8081**
- 启动类：`io.github.aicyi.example.mybatisplus.AicyiExampleMyBatisPlusApplication`

## 启动

```bash
cd aicyi-example-mybatisplus
mvn spring-boot:run
```

前置：MySQL + Nacos（导入 `aicyi-datasource.yml`，见 [Nacos 配置中心](../infra/nacos.md)）；
数据库需已初始化（`aicyi-examples/db/schema.sql`）。

## 配置

### 本地 `application.yml`

- `server.port: 8081`，`spring.profiles.active: test`
- `mybatis-plus`：mapper xml 位置、下划线转驼峰、`id-type: assign_id`（雪花主键）等

### Nacos 导入清单（`application-test.yml`）

| Data ID | 作用 |
| --- | --- |
| `aicyi-datasource.yml` | 数据源（MySQL） |

## 代码结构

```
io.github.aicyi.example.mybatisplus
├── AicyiExampleMyBatisPlusApplication
├── controller/          # UserController、MessageTemplateController（MP 示例入口）
├── domain/entity/       # User、MessageTemplate（继承 BaseEntity，自动填充审计字段）
├── domain/type/         # GenderType 枚举
├── mapper/              # UserMapper、MessageTemplateMapper（继承 BaseMapper）
├── service/             # IUserService、IMessageTemplateService（继承 IService）
│   └── impl/            # UserServiceImpl、MessageTemplateServiceImpl（继承 ServiceImpl）
└── config/              # PasswordEncoderConfiguration
```

`src/main/resources/mapper/` 下另有 `UserMapper.xml` / `MessageTemplateMapper.xml`（自定义 SQL）。

## 代码生成器

`src/test/java/.../MyBatisPlusGenerator` 封装了官方 `FastAutoGenerator`：
- 连接参数、包名、字段类型覆盖从 `src/test/resources/generator.yml` 读取
- 支持自定义实体模板（为全限定自定义类型自动补 import）

> 注意：测试源码目录包名为 `io.github.aicyi.example.mybaitsplus`（`mybaits` 为历史拼写，与主源码的 `mybatisplus` 不同），
> 下面命令里的全限定名需照此拼写。

```bash
# 修改 generator.yml 后直接运行 main 方法
mvn test-compile exec:java -Dexec.mainClass=io.github.aicyi.example.mybaitsplus.MyBatisPlusGenerator
```

生成产物示例：实体、Mapper（BaseMapper）、Service（IService+Impl）、Controller（含通用 CRUD）。

## 测试

| 测试 | 说明 |
| --- | --- |
| `IUserServiceTest` | User CRUD + MP 自动填充验证 |
| `IMessageTemplateServiceTest` | MessageTemplate CRUD 验证 |

```bash
mvn test -pl aicyi-example-mybatisplus
```
