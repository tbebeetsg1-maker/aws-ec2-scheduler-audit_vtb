CREATE TABLE ec2_activity_log (
    log_id          NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instance_id     VARCHAR2(30) NOT NULL,
    action          VARCHAR2(10) NOT NULL,
    status          VARCHAR2(20) NOT NULL,
    log_timestamp   TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL
);
