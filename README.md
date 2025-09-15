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


curl -X POST "https://solar.ninja360.ru/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@ninja360.ru", "password": "securepassword123"}'



 docker build -t registry.gitlab.com/ai8595334/ai-issue-genius/ai-issue-genius-agent .
 docker push registry.gitlab.com/ai8595334/ai-issue-genius/ai-issue-genius-agent
 
 docker build --no-cache -t registry.gitlab.com/ai8595334/ai-issue-genius/ai-issue-genius-server .
 docker push registry.gitlab.com/ai8595334/ai-issue-genius/ai-issue-genius-server
 kubectl logs ai-issue-genius-server-8479f7c86b-tb9c7 -f
