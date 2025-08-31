import requests
import json
import re

def ask_hackclub_ai(username: str, question: str, tune_file: str = "ai_tune.txt") -> str:


    #with open(tune_file, "r", encoding="utf-8") as f:
    #    system_prompt = f.read()
    system_prompt = """
YSWS stands for "You Ship We Ship" and are programs made possible with Hack Club; Teenagers can pitch a YSWS idea and someone can sponsor it. A YSWS has a theme, and participants build something of that theme and get a reward. 

Basic terms: (if a question is thrown to you about a term, give the meaning + tell them to go to https://ysws.jimdinias.dev/terminology for more)
PoC - PoC stands for Point of Contact. This is usually an intern who connects you to a full-time HQ staff member sponsoring the YSWS project.
Sponsor - The Sponsor is the full-time HQ staff member who makes the YSWS possible. They oversee your PoC and provide funding through HCB.
Unified DB - The Unified Database is an internal system where all approved YSWS submissions are stored. You can add a reviewed project to it using the Airtable automation tickbox.
Weighted Grants - Weighted Grants measure contribution by tracking how many hours of teen coding work went into a project. Each Weighted Grant represents 10 hours of work on an approved YSWS submission.
Override Hours Count - This is the manually adjusted estimate of how long it actually took to create the project, based on Hackatime or a reviewer’s judgment. It replaces the default grant hours if modified.
Override Reason - The explanation for changing the default hours, including the number of hours chosen and details on how the project was tested or evaluated.
Shadow Granting - This occurs when a grant is sent manually without being added to the Unified DB. This is considered a bad practice.

ALWAYS RETURN EVERYTHING IN HTML FORMAT! Don't write **, use <b> tags. Dont do []() for links, use <a> tags. Use <br> for new lines.

"""

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

