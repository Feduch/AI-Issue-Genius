-- Предоставляем права на схему public пользователю ai_issue_genius
GRANT ALL ON SCHEMA public TO ai_issue_genius;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ai_issue_genius;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ai_issue_genius;

-- Создаем таблицу
CREATE TABLE IF NOT EXISTS logs (
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