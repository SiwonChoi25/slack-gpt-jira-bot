from fastapi import FastAPI, Request, HTTPException
from slack_sdk import WebClient
from openai import OpenAI
from dotenv import load_dotenv
import os
import time
import logging
from collections import defaultdict
from jira_client import create_jira_issue
from datetime import datetime
import json

#  로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# 초기 설정
load_dotenv()
app = FastAPI()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

SLACK_BOT_USER_ID = os.getenv("SLACK_BOT_USER_ID")
recent_events = defaultdict(float)
DUPLICATE_WINDOW_SECONDS = 10

@app.post("/slack-event")
async def slack_event(req: Request):
    payload = await req.json()

    #  Slack challenge 확인
    if "challenge" in payload:
        return {"challenge": payload["challenge"]}

    event = payload.get("event")
    if not event:
        raise HTTPException(status_code=400, detail="이벤트 데이터 없음")

    #  중복 이벤트 차단
    event_id = payload.get("event_id")
    if not event_id:
        raise HTTPException(status_code=400, detail="event_id 없음")

    now = time.time()
    if recent_events.get(event_id) and now - recent_events[event_id] < DUPLICATE_WINDOW_SECONDS:
        logging.info(f"중복 이벤트 무시됨: {event_id}")
        return {"message": "중복 이벤트입니다. 무시됨"}
    recent_events[event_id] = now

    #  봇 메시지 무시
    if event.get("user") and event["user"] == SLACK_BOT_USER_ID:
        logging.info("봇 메시지 무시됨")
        return {"message": "봇 메시지 무시됨"}

    text = event.get("text", "").strip()
    if not text:
        return {"message": "메시지 없음"}

    #  GPT 요약 요청
    title = None
    description = None
    try:
        summary_prompt = f"""
        다음은 Slack 채널의 메시지입니다. 이 메시지가 단순 정보, 대화인지, 실제 업무 요청인지 먼저 판단해주세요.

        - 업무 요청일 경우에는 다음 JSON 형식으로 Jira 티켓 내용을 생성해주세요:
            {{
            "type": "task",
            "title": "...",
            "description": "..."
            }}

        - 단순 정보일 경우에는:
            {{
            "type": "info"
            }}

        - 단순 대화일 경우에는:
            {{
            "type": "chat"
            }}

        Slack 메시지:
        {text}

        Respond only with JSON.
        """

        summary_response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=200,
            temperature=0.7
        )

        raw_response = summary_response.choices[0].message.content.strip()

        if raw_response.startswith("```json"):
            raw_response = raw_response[7:]
        if raw_response.endswith("```"):
            raw_response = raw_response[:-3]

        logging.info("요약 결과: %s", raw_response)

        result = json.loads(raw_response.strip())
        if result.get("type") == "task":
            title = result.get("title")
            description = result.get("description")
        else:
            return {"message": "업무 요청이 아님. 티켓 생성 안함"}

    except Exception as e:
        logging.error("GPT 요약 실패", exc_info=True)
        return {"message": "GPT 요약 실패"}

    # GPT 날짜 추출 요청
    start_date = None
    due_date = None
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        date_prompt = f"""
        다음은 Slack 메시지입니다. 이 메시지에 작업의 시작일과 마감일로 해석되는 날짜가 있다면, 실제 날짜(YYYY-MM-DD)로 변환해서 각각 추출해주세요.

        - 오늘 날짜는 {today_str}입니다. 
        - 예: “이번 주 금요일”, “다음 주 수요일” 등의 표현은 오늘을 기준으로 계산하세요.
        - 시작일과 마감일이 모두 있을 수도 있고, 하나만 있을 수도 있고, 아예 없을 수도 있습니다.

        출력 형식 (JSON):
        {{
          "start_date": "YYYY-MM-DD" 또는 null,
          "due_date": "YYYY-MM-DD" 또는 null
        }}

        Slack 메시지:
        {text}

        Respond only with JSON.
        """

        date_response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": date_prompt}],
            max_tokens=50,
            temperature=0
        )

        raw_date_response = date_response.choices[0].message.content.strip()

        if raw_date_response.startswith("```json"):
            raw_date_response = raw_date_response[7:]
        if raw_date_response.endswith("```"):
            raw_date_response = raw_date_response[:-3]

        logging.info("날짜 결과: %s", raw_date_response)

        if raw_date_response:
            date_info = json.loads(raw_date_response.strip())
            start_date = date_info.get("start_date")
            due_date = date_info.get("due_date")

            # GPT가 "null" 문자열로 줄 경우 처리
            if start_date == "null":
                start_date = None
            if due_date == "null":
                due_date = None

    except Exception as e:
        logging.warning("날짜 추출 실패, 무시하고 진행", exc_info=True)
        start_date = None
        due_date = None

    # Jira 이슈 생성
    if not title or not description:
        return {"message": "요약 정보 부족으로 Jira 티켓 생성하지 않음"}

    try:
        issue_key = create_jira_issue(
            title=title,
            description=description,
            start_date=start_date,
            due_date=due_date
        )

        logging.info(f"Jira 이슈 생성됨: {issue_key}")

        slack_client.chat_postMessage(
            channel=event.get("channel"),
            text=f"Jira 이슈가 생성되었습니다: {issue_key}"
        )

        return {"message": f"Issue {issue_key} created"}

    except Exception as e:
        logging.error("Jira 이슈 생성 실패", exc_info=True)
        raise HTTPException(status_code=500, detail="Jira 이슈 생성 실패")
