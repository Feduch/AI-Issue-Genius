def prepare_ai_request(log_data):
    # Извлекаем информацию о контексте ошибки
    traceback = log_data["error"]["traceback"]
    code_context = extract_code_context(traceback)

    request = {
        "request_type": "error_analysis",
        "user": {
            "is_authenticated": log_data["user"]["is_authenticated"],
            "id": log_data["user"]["id"] if log_data["user"]["is_authenticated"] else None,
        },
        "error_context": {
            "timestamp": log_data["timestamp"],
            "environment": log_data["environment"],
            "application": log_data["application"],
            "service": log_data["service"],
            "request_id": log_data["request_id"],
            "request_method": log_data["request"]["method"],
            "request_path": log_data["request"]["path"],
            "client_ip": log_data["request"]["client_ip"],
            "user_authenticated": log_data["user"]["is_authenticated"],
            "request_body": log_data["request"]["body"]
        },
        "error_details": {
            "type": log_data["error"]["type"],
            "message": log_data["error"]["message"],
            "traceback": traceback,
            "code_context": code_context
        },
        "environment_info": {
            "python_version": log_data["versions"]["python"],
            "django_version": log_data["versions"]["django"],
            "debug_mode": log_data["settings"]["debug"],
            "database_engine": log_data["settings"]["database_engine"]
        },
        "analysis_request": {
            "required_output": {
                "problem_description": "",
                "root_cause": "",
                "solution_steps": [],
                "prevention_measures": [],
                "severity_level": "",
                "affected_components": []
            }
        }
    }

    return request


def extract_code_context(traceback):
    # Ищем строки с кодом приложения (не библиотек)
    for line in reversed(traceback):
        if '/opt/app/' in line and 'line ' in line:
            parts = line.strip().split(',')
            if len(parts) >= 2:
                file_info = parts[0].split('File ')[1].replace('"', '').strip()
                line_info = parts[1].split('line ')[1].split(')')[0].strip()
                code_snippet = parts[2] if len(parts) > 2 else ""

                return {
                    "file": file_info,
                    "line": line_info,
                    "code_snippet": code_snippet.strip()
                }

    return {"file": "unknown", "line": "unknown", "code_snippet": ""}