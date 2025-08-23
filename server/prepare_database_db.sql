-- Создаем базу данных
CREATE DATABASE ai_issue_genius;

-- Создаем пользователя
CREATE USER ai_issue_genius WITH PASSWORD 'ai_issue_genius';

-- Даем пользователю права на базу данных
GRANT ALL PRIVILEGES ON DATABASE ai_issue_genius TO ai_issue_genius;

-- Подключаемся к созданной базе данных
\c ai_issue_genius;

-- Создаем таблицу в правильной базе данных
CREATE TABLE logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    service VARCHAR(100) NOT NULL,
    log JSONB,
    ai_analysis JSONB,
    analysis_time TIMESTAMP WITH TIME ZONE
);

-- Даем права пользователю на таблицу
GRANT ALL PRIVILEGES ON TABLE logs TO ai_issue_genius;
GRANT ALL PRIVILEGES ON SEQUENCE logs_id_seq TO ai_issue_genius;


CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_service ON logs(service);
CREATE INDEX IF NOT EXISTS idx_logs_analysis_time ON logs(analysis_time);