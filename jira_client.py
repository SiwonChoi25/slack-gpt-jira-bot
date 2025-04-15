# jira_client.py
import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

def create_jira_issue(title: str, description: str, start_date: str = None, due_date: str = None) -> str:
    """
    Jira 티켓을 생성합니다.

    :param title: 이슈 제목
    :param description: 이슈 설명
    :param start_date: 시작일 (YYYY-MM-DD) 형식. 없으면 생략.
    :param due_date: 마감일 (YYYY-MM-DD) 형식. 없으면 생략.
    :return: 생성된 Jira 이슈 키 (예: "MYPROJECT-123")
    """
    domain = os.getenv("JIRA_DOMAIN")
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_API_TOKEN")
    project_key = os.getenv("JIRA_PROJECT_KEY")

    url = f"{domain}/rest/api/3/issue"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    fields = {
        "project": {"key": project_key},
        "summary": title,
        "description": {
            "type": "doc",
            "version": 1,
            "content": [{
                "type": "paragraph",
                "content": [{
                    "type": "text",
                    "text": description
                }]
            }]
        },
        "issuetype": {"name": "Task"}
    }

    # 시작일, 마감일이 있으면 필드에 포함
    # 현재 REST API request에 startdate 필드 없는 듯함. 
    # https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/#api-rest-api-3-issue-post
    # custom으로 가야됨 -> 아직 미구현
    # if start_date and start_date != "null":
    #     fields["startdate"] = start_date

    if due_date and due_date != "null":
        fields["duedate"] = due_date

    payload = {"fields": fields}

    response = requests.post(
        url,
        headers=headers,
        auth=HTTPBasicAuth(email, token),
        json=payload
    )

    if response.status_code == 201:
        return response.json()["key"]
    else:
        raise Exception(f"Jira 이슈 생성 실패: {response.status_code}\n{response.text}")
    

