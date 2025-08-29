# add your ysws to the ysws list at ysws.hackclub.com" where users will enter data and it will auto generate the yml code and open the ysws catalog to merge

data_link = "https://github.com/hackclub/YSWS-Catalog/blob/main/data.yml"

def generate_yml(name, description, website, slack, slackChannel, status, deadline):
    
    yml_snippet = f"""
- name: {name}
  description: {description}
  website: {website}
  slack: {slack}
  slackChannel: '{slackChannel}'
  status: {status}
  deadline: {deadline}
"""
    
    return yml_snippet
