
import requests


id = "U091HBJLQS2"
projectname = ""

if projectname:
    hackatime_data = requests.get(f"https://hackatime.hackclub.com/api/v1/users/{id}/stats?features=projects&filter_by_project=projectname={projectname}")
    print("did project name")
else:
    hackatime_data = requests.get(f"https://hackatime.hackclub.com/api/v1/users/{id}/stats?features=projects")

if hackatime_data.status_code == 200:
    print(hackatime_data.json())