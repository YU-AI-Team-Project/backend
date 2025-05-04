# pip install openai python-dotenv
import openai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")       #현재 .env에 임의의 키가 입력돼있음
client = openai.OpenAI(api_key=api_key)

#gpt 호출
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "당신은 투자 분석 도우미입니다."},
        {"role": "user", "content": "2024년 상반기 엔비디아 실적적 리포트해줘"}
    ]
)

# 응답 출력
print(response.choices[0].message.content)
