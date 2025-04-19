# Slack GPT Jira Bot

Slack 메시지를 GPT로 분석해 Jira 티켓을 자동 생성하는 FastAPI 기반 연동 봇

---

## 🚀 기능 요약

- Slack 채널에서 메시지를 수신
- GPT를 사용해 메시지를 분석: 단순 대화인지, 정보인지, 업무 요청인지 분류
- 업무 요청 메시지일 경우:
  - GPT로 제목과 설명 요약
  - Jira 이슈 자동 생성
  - 마감일(`due_date`)이 메시지에 언급되었을 경우 자동 추출

<br>
<br>

## 🛠 기술 스택

- Python, FastAPI
- OpenAI API (GPT-4o)
- Slack Events API
- Jira REST API

<br>
<br>

## 💻 실행 방법

1. `.env` 파일 생성
```env
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_SIGNING_SECRET=your_slack_sigging_secret
SLACK_BOT_USER_ID=your_bot_user_id
OPENAI_API_KEY=your_openai_api_key
JIRA_EMAIL=your_jira_email
JIRA_API_TOKEN=your_jira_api_token
JIRA_DOMAIN=https://your-domain.atlassian.net
JIRA_PROJECT_KEY=PROJECTKEY
```

2. 서버 실행
```bash
uvicorn main:app --reload
ngrok http 8000  # 생성된 주소를 Slack Event URL로 사용
```

<br>

3. Slack App에 이벤트 URL 등록 (/slack-event)

<br>
<br>

## 🔧 사용 방법 (실제 작동 테스트)
1. Slack App을 생성하고, 이벤트 권한 및 봇을 설정한 후 채널에 추가
2. .env 파일을 설정하고 uvicorn + ngrok으로 서버 실행
3. Slack에서 일반적인 업무 요청 메시지 전송 (ex: "다음 주 화요일까지 데모 영상 촬영해주세요")
4. 처리 결과:
- Slack 메시지가 GPT에 의해 분석되어 Jira 티켓으로 자동 생성
- Jira 보드에서 제목, 설명, 마감일 정보 확인 가능