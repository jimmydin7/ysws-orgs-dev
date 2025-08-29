import requests

def get_commit_count(github_url):

    try:
        parts = github_url.rstrip("/").split("/")
        owner = parts[-2]
        repo = parts[-1]
    except IndexError:
        return "Invalid GitHub URL"


    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"
    
 
    response = requests.get(api_url)
    if response.status_code != 200:
        return f"Error: {response.status_code}"

    if 'Link' in response.headers:
        link = response.headers['Link']
        import re
        match = re.search(r'&page=(\d+)>; rel="last"', link)
        if match:
            return int(match.group(1))

    return len(response.json())


