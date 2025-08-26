# AIssueGenius Agent - Умный помощник

Создает issue в GitLab на анализе логов.


curl --request POST \
     --header "PRIVATE-TOKEN: glpat-****" \
     --header "Content-Type: application/json" \
     --data '{
       "title": "Новая задача",
       "description": "Описание задачи"
     }' \
     "https://gitlab.com/api/v4/projects/10046060/issues"



CREATE TABLE service_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    service VARCHAR(100) NOT NULL,
    log JSONB,
    ai_analysis JSONB,
    analysis_time TIMESTAMP WITH TIME ZONE
);