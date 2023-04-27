#!/usr/bin/env python
# coding: utf-8

# In[1]:


import requests
import ruamel.yaml as yaml
import json
import os
import sys
from typing import List, Tuple, Dict, Union, Optional, Any


# In[2]:


credentials_path = 'memsource_credentials.yml'


# In[3]:


#For .ipynb notebook
PROJECT_NAME = "Alp MT eval test proper workflow"


# In[4]:


#For .py script
project_name = sys.argv[1]
print('project', PROJECT_NAME)


# ### 1- authenticate

# In[5]:


def load_credentials(memsource_credentials):
    with open(memsource_credentials, "r") as f:
        data = yaml.safe_load(f)
        return (data["memsource_username"], data["memsource_password"])


# In[6]:


def api_get_token(username, password):
    assert isinstance(username, str)
    assert isinstance(password, str)

    res = requests.post(
        "https://cloud.memsource.com/web/api2/v1/auth/login",
        json={"userName": username, "password": password},
    )

    return res.json()["token"]


def authenticate(memsource_credentials):
    return api_get_token(*load_credentials(memsource_credentials))

def arg_checker(
    acceptable: Union[List[Tuple[str, str]], List[str]],
    **kwargs
) -> bool:

    ref = {}
    for x in acceptable:
        if not isinstance(x, tuple):
            x = {x: object}
        else:
            x = {x[0]: x[1]}
        ref.update(**x)

    for key, val in kwargs.items():
        try:
            assert key in ref
        except AssertionError:
            logger.error(f"Wrong argument name: {key} is not in {ref.keys()}")
            raise

        try:
            assert isinstance(val, ref[key])
        except AssertionError:
            logger.error(
                f"Wrong argument type: {key} = {val} should be of type {ref[key]}"
            )
            raise

    return True

def check_status(
    res: requests.Response,
    element: str,
    **kwargs):
    if res.ok:
        return res.json()
    else:
        if res.status_code == 404:
            print(f"Could not find {element}: parameter: `{kwargs}`")
        else:
            print(f"Problem with the request: parameters: `{kwargs}`")
        return False


# In[7]:


authentication_token = authenticate(credentials_path)
print("token", authentication_token)


# ### 1.5 - Get project uid

# In[8]:


# def api_list_projects_old(token, **kwargs):

#     res = requests.get(
#         f"https://cloud.memsource.com/web/api2/v1/projects",
#         params={"token": token, **kwargs},
#     )

#     return res.json()

def get_authorization_header(token):
    return {
      'Authorization': 'ApiToken '+ token
    }

def api_list_projects(token, **kwargs):
    
#     headers = {
#       'Authorization': 'ApiToken '+ token
#     }
    
    url  = f"https://cloud.memsource.com/web/api2/v1/projects"
    response = requests.request("GET", url, headers=get_authorization_header(token))

    return response.json()

def get_project_uid_from_name(project_name, token):
    projects_info = api_list_projects(token)
    if 'content' in projects_info:
        for p in projects_info['content']:
            if p['name'] == project_name:
                return p['uid']
    else:
        print(projects_info['errorDescription'])
    
    return None


# In[9]:


project_uid = get_project_uid_from_name(PROJECT_NAME, authentication_token)
print('project_uid', project_uid)


# ### 2- List jobs of project

# In[10]:


def api_list_jobs(project_uid, token, **kwargs):
    assert arg_checker(
        acceptable=[
            ("pageNumber", int),
            ("pageSize", int),
            ("count", int),
            ("workflowLevel", int),
            ("status", str),
            ("targetLang", str),
        ],
        **kwargs,
    )

    res = requests.get(
        f"https://cloud.memsource.com/web/api2/v2/projects/{project_uid}/jobs",
        params={"token": token, **kwargs},
        headers=get_authorization_header(token)
    )

#     return check_status(res, "jobs", **kwargs)
    return res.json()

def get_completed_job_ids(job_list):
    return [job['uid'] for job in job_list['content'] if job['status'] == "COMPLETED"]

def get_filename_of_job(job_uid, jobs_responses_per_workflow):
    for workflow in jobs_responses_per_workflow:
        for job in jobs_responses_per_workflow[workflow]['content']:
            if job['uid'] == job_uid:
                return job['filename']
    return None

def get_workflow_id(workflow_step):
    if workflow_step == 1:
        return "MT"
    elif workflow_step == 2:
        return "Tr"
    elif workflow_step == 3:
        return "Rv"
    else:
        return "Unknown"


# In[11]:


WORKFLOWS = {1:"MT", 2:"Tr", 3:"Rv"}
complete_job_ids_of_project = set()
complete_job_ids_of_project_per_workflow = {1:[], 2:[], 3:[]}
job_ids_of_project = set()
jobs_info_per_workflow = {}

for workflow_level in WORKFLOWS:

#     workflow_level = 2 # 1-MT, 2-Tr, 3-Rv
    workflow = get_workflow_id(workflow_level)
    workflow_job_response = api_list_jobs(project_uid, authentication_token, workflowLevel=workflow_level)
    complete_jobs = get_completed_job_ids(workflow_job_response)
    
    job_ids = [j['uid'] for j in workflow_job_response['content']]
    
    complete_job_ids_of_project = complete_job_ids_of_project.union(complete_jobs)

    complete_job_ids_of_project_per_workflow[workflow_level].extend(complete_jobs)
    
    jobs_info_per_workflow[workflow_level] = workflow_job_response
    
    job_ids_of_project = job_ids_of_project.union(job_ids)

    print("Workflow", workflow_level, workflow)
    print('jobs', job_ids)
    print('complete', complete_jobs)
    print('===')
    
complete_job_ids_of_project = list(complete_job_ids_of_project)
job_ids_of_project = list(job_ids_of_project)
# project_job_ids = [j['content']['uid'] for j in jobs_of_project]
    
print("All")
print("jobs", job_ids_of_project)
print("complete per wf", complete_job_ids_of_project_per_workflow)


# ### 3 - Create analyses

# In[13]:


def api_post_create_analysis(token, job_uid_list, analysis_type, countSourceUnits, analysis_name, compareWorkflowLevel=None):
    if analysis_type == "Compare":
        json={"jobs":[{"uid":uid} for uid in job_uid_list], 
              "type":analysis_type, "countSourceUnits":countSourceUnits, 
              "name":analysis_name, "compareWorkflowLevel":compareWorkflowLevel}
    else:
        json={"jobs":[{"uid":uid} for uid in job_uid_list], 
              "type":analysis_type, "countSourceUnits":countSourceUnits, 
              "name":analysis_name}
    
    res = requests.post(
        "https://cloud.memsource.com/web/api2/v1/analyses",
        headers=get_authorization_header(token),
        json=json,
    )

    return res.json()

#List analysis by project id (https://cloud.memsource.com/web/docs/api#operation/listByProjectV3)
def api_list_analyses(token, project_uid):

    res = requests.get(
        f"https://cloud.memsource.com/web/api2/v3/projects/{project_uid}/analyses",
        headers=get_authorization_header(token),
    )

    return res.json()


# In[14]:


analysis_id_list = [an['name'] for an in api_list_analyses(authentication_token, project_uid)['content']]


# In[15]:


#Pre-analysis on MT (Run on workflow 1)

for job_id in complete_job_ids_of_project_per_workflow[1]:
    doc_id = get_filename_of_job(job_id, jobs_info_per_workflow)
    print('job', job_id, doc_id)
    
    workflow_level = 1
    workflow = get_workflow_id(workflow_level)
    analysis_type = "PreAnalyse"
    pre_analysis_name = f"TWBData-{analysis_type}-{workflow}-{job_id}-{doc_id}"
    
    if pre_analysis_name not in analysis_id_list:
        res = api_post_create_analysis(authentication_token, complete_job_ids_of_project, analysis_type="PreAnalyse", 
                                 countSourceUnits=False, analysis_name=pre_analysis_name)
        print(analysis_type, pre_analysis_name)


# In[17]:


#Post-editing analysis on Translation (Run on workflow 2)

for job_id in complete_job_ids_of_project_per_workflow[2]:
    doc_id = get_filename_of_job(job_id, jobs_info_per_workflow)
    print('job', job_id, doc_id)
    
    workflow_level = 2
    workflow = get_workflow_id(workflow_level)
    analysis_type = "PostAnalyse"
    translation_post_analysis_name = f"TWBData-{analysis_type}-{workflow}-{job_id}-{doc_id}"
    if pre_analysis_name not in analysis_id_list:
        res = api_post_create_analysis(authentication_token, [job_id], analysis_type=analysis_type, 
                                 countSourceUnits=False, analysis_name=translation_post_analysis_name)
        print(analysis_type, workflow, translation_post_analysis_name)


# In[18]:


#Analyses on revision

for job_id in complete_job_ids_of_project_per_workflow[3]:
    doc_id = get_filename_of_job(job_id, jobs_info_per_workflow)
    print('job', job_id, doc_id)
    
    #Post editing analysis on revision (Run on workflow 3)
    workflow_level = 3
    workflow = get_workflow_id(workflow_level)
    analysis_type = "PostAnalyse"
    revision_post_analysis_name = f"TWBData-{analysis_type}-{workflow}-{job_id}-{doc_id}"
    if pre_analysis_name not in analysis_id_list:
        res = api_post_create_analysis(authentication_token, [job_id], analysis_type=analysis_type, 
                                 countSourceUnits=False, analysis_name=revision_post_analysis_name)
        print(analysis_type, workflow, revision_post_analysis_name)
    
    #Compare analysis on revision (Run on workflow 3)
    workflow_level = 3
    workflow = get_workflow_id(workflow_level)
    analysis_type = "Compare"
    compare_to_workflow_step = 2
    compare_to_workflow = get_workflow_id(compare_to_workflow_step)
    compare_analysis_name = f"TWBData-{analysis_type}-{workflow}_{compare_to_workflow}-{job_id}-{doc_id}"
    if pre_analysis_name not in analysis_id_list:
        res = api_post_create_analysis(authentication_token, [job_id], analysis_type=analysis_type, 
                                       countSourceUnits=False, analysis_name=compare_analysis_name,
                                       compareWorkflowLevel=compare_to_workflow_step)
        print(analysis_type, compare_analysis_name)


# ### 4 - List analyses

# In[19]:


#List analysis by project id (https://cloud.memsource.com/web/docs/api#operation/listByProjectV3)
def api_list_analyses(token, project_uid):

    res = requests.get(
        f"https://cloud.memsource.com/web/api2/v3/projects/{project_uid}/analyses",
        headers=get_authorization_header(token),
    )

    return res.json()


# In[20]:


analysis_list = api_list_analyses(authentication_token, project_uid)
analysis_dict = {an['uid']:an['name'] for an in analysis_list['content']}
print(len(analysis_dict), 'ANALYSES for project', project_uid, 'job', job_id)


# ### 5- Get and save analysis results

# In[21]:


#Create results dir if it doesn't exist
results_dir_name = 'results'
if not os.path.exists(results_dir_name):
    os.makedirs(results_dir_name)


# In[22]:


def api_get_analysis(token, analyse_uid):

    res = requests.get(
        f"https://cloud.memsource.com/web/api2/v3/analyses/{analyse_uid}",
        headers=get_authorization_header(token),
    )

    return res.json()

def assign_analysis_id(anname:str):
    aid = ""
    


# In[24]:


analysis_results_dict = {}

for anid, anname in analysis_dict.items():
    
    doc_name = anname.split('-')[-1]
    doc_dir = os.path.join(results_dir_name, doc_name)
    
    if not os.path.exists(doc_dir):
        os.makedirs(doc_dir)
    
    analysis_result = api_get_analysis(authentication_token, anid)
    analysis_out = os.path.join(doc_dir, anname + '.json')
    
    analysis_results_dict[anname] = analysis_result
    
    with open(analysis_out, 'w') as f:
        f.write(json.dumps(analysis_result, indent=4))
        
    print(analysis_out)


# ### 6- Interpret results
# 
# - Translation Approval Rate: Percentage of segments that were accepted without changes by the translator
# - Revision approval rate: Percentage of segments that were accepted without changes by the revisor
#  
# - Translation edit percentage and editing time from PE analysis on translation
# - Translation edit percentage and editing time from PE analysis on revision
# - Accumulative edit percentage from PE analysis on revision
# - Time from PE analysis on revision?
# 

# In[ ]:




