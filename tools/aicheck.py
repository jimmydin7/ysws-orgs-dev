import requests
from urllib.parse import urlparse

API_URL = "https://ai.hackclub.com/chat/completions"
MODEL = "qwen/qwen3-32b"

def get_readme_from_github(repo_url):
    parsed_url = urlparse(repo_url)
    path_parts = parsed_url.path.strip("/").split("/")
    if len(path_parts) < 2:
        raise ValueError("Invalid GitHub repo URL")
    owner, repo = path_parts[:2]

    branches = ["main", "master"]
    for branch in branches:
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
        r = requests.get(raw_url)
        if r.status_code == 200:
            return r.text
    return None

def detect_ai_probability(readme_text):
    prompt = f"""
You are an expert AI text detector. Your task is to analyze the provided text and determine the probability that it was written by an AI (0.0-1.0).

Analyze the text for human vs AI patterns as described below:

HUMAN PATTERNS (lower AI probability 0.05-0.25):
- Natural imperfections: typos, informal grammar, inconsistent style
- Personal voice: use of "I think", "gonna", "pretty cool", casual contractions
- Direct and simple language: "Added this feature", "Fixed the bug"
- Authentic emotion: frustration or excitement: "finally got it working!", "this sucks"
- Technical but personal tone: "had issues with X, solved by doing Y"

AI PATTERNS (higher AI probability 0.70-0.95):
- Perfect grammar combined with a corporate tone
- Buzzword clusters: "comprehensive solution leveraging cutting-edge technology"
- Marketing speak: "showcasing expertise", "seamlessly integrates", "effortlessly optimizes"
- Structured lists with emoji bullets (e.g., ✅, 🎯, 🚀)
- Overuse of em dashes for emphasis—like this
- Generic and overly formal descriptions: "robust platform delivering exceptional results"

Provide your answer as a number between 0.0 (definitely human) and 1.0 (definitely AI). Only return the probability.

Text to analyze:
{readme_text[:2000]}
"""
    
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    response = requests.post(API_URL, json=payload)
    result = response.json()
    return result['choices'][0]['message']['content'].strip()

if __name__ == "__main__":
    urls = [
        "https://github.com/jimmydin7/auth-ysws"
    ]
    
    for url in urls:
        print(f"Checking {url}...")
        readme = get_readme_from_github(url)
        if readme:
            scores = []
            for i in range(10):  
                probability = detect_ai_probability(readme)
                try:
                    prob_val = float(probability)
                    scores.append(prob_val)
                    print(f"Run {i+1}: {prob_val}")
                except ValueError:
                    print(f"Run {i+1}: Invalid response ({probability})")
            
            if scores:
                avg = sum(scores) / len(scores)
                print(f"\nAverage AI probability over {len(scores)} runs: {avg:.3f}\n")
            else:
                print("No valid probability values received.\n")
        else:
            print("No README found.\n")
