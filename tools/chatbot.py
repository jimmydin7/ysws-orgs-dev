import requests
import json
import re

def ask_hackclub_ai(username: str, question: str, tune_file: str = "ai_tune.txt") -> str:


    with open(tune_file, "r", encoding="utf-8") as f:
        system_prompt = f.read()
    

    prompt = f"You are chatting to {username} - {system_prompt}"
    

    payload = {
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": question}
        ]
    }
    

    response = requests.post(
        "https://ai.hackclub.com/chat/completions",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload)
    )
    

    try:
        data = response.json()
        bot_reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return format_ai_response_generic(bot_reply)
    except Exception as e:
        return f"Error: {e}\nRaw response: {response.text}"


def format_ai_response_generic(raw_text: str) -> str: #doesnt work for now

    text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL)
    

    #text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank">\1</a>', text)
    

    #text = text.replace("\n", "<br>")
    
    return text

