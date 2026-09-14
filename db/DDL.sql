create table t_student
(
    id            bigint                      not null comment '主键'
        primary key,
    user_id       bigint                      not null comment '用户ID',
    score         decimal(15, 2) default 0.00 not null comment '成绩',
    grade_type    varchar(2)                  not null comment '年级',
    register_time datetime(3)                 not null comment '注册时间',
    deleted       tinyint        default 0    not null comment '删除标记，0：未删除，1：已删除',
    version       int            default 0    not null comment '版本',
    create_time   datetime(3)                 not null comment '创建时间',
    update_time   datetime(3)                 not null comment '更新时间',
    constraint uk_user_id
        unique (user_id) comment '用户ID唯一键'
) comment '学生表';

create table t_user
(
    id          bigint            not null comment '主键'
        primary key,
    username    varchar(64)       not null comment '用户名',
    password    varchar(255) null comment '用户名密码',
    mobile      varchar(11)       not null comment '手机号',
    email       varchar(64) null comment '邮箱地址',
    nickname    varchar(64) null comment '用户昵称',
    id_card     varchar(32) null comment '身份证',
    age         int null comment '年龄',
    gender_type tinyint null comment '性别，1:男；2：女；',
    birthday    datetime(3)       null comment '生日',
    deleted     tinyint default 0 not null comment '删除标记，0：未删除，1：已删除',
    version     int     default 0 not null comment '版本',
    create_time datetime(3)       not null comment '创建时间',
    update_time datetime(3)       not null comment '更新时间',
    constraint uk_mobile
        unique (mobile) comment '手机号唯一键',
    constraint uk_username
        unique (username) comment '用户名唯一键'
) comment '用户表';

create index idx_id_card
    on t_user (id_card) comment '身份证索引';
create index idx_email
    on t_user (email) comment '邮箱地址索引';

