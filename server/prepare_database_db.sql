CREATE DATABASE ai_issue_genius;
CREATE USER ai_issue_genius WITH PASSWORD 'ai_issue_genius';
ALTER USER ai_issue_genius WITH SUPERUSER;

\c ai_issue_genius

-- Сначала создаем таблицу от имени postgres пользователя
CREATE TABLE logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    service VARCHAR(100) NOT NULL,
    log JSONB,
    ai_analysis JSONB,
    analysis_time TIMESTAMP WITH TIME ZONE
);

-- Создаем индексы
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_service ON logs(service);
CREATE INDEX IF NOT EXISTS idx_logs_analysis_time ON logs(analysis_time);

-- Предоставляем права пользователю ai_issue_genius
GRANT ALL PRIVILEGES ON TABLE logs TO ai_issue_genius;
GRANT ALL PRIVILEGES ON SEQUENCE logs_id_seq TO ai_issue_genius;
GRANT USAGE ON SCHEMA public TO ai_issue_genius;