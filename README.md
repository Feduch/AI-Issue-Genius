# AIssueGenius Agent - Умный помощник

Создает issue в GitLab на анализе логов.


curl --request POST \
     --header "PRIVATE-TOKEN: glpat-HYTb4JZCs5snsQIl3ukeym86MQp1OjF5eTNiCw.01.121oz5jwx" \
     --header "Content-Type: application/json" \
     --data '{
       "title": "Новая задача",
       "description": "Описание задачи"
     }' \
     "https://gitlab.com/api/v4/projects/10046060/issues"