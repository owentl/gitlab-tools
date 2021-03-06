import json
import requests
import gitlab
from markdownify import markdownify


# URL for Aha! Instance.  XXXX should be set to your company
AHA_URL = 'https://XXXX.aha.io/api/v1/'
# Aha! API Token
AHA_TOKEN = 'API TOKEN HERE'
#Aha headers for calls.  Allows us to use the API key
AHA_HEADERS = {
    "Authorization": "Bearer {}".format(AHA_TOKEN),
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}
# Name of the project in Titan, used for filtering
AHA_PROJECT = 'PROJECT'

# Release to migrate.  This is the internal ID not the Release Name
AHA_RELEASE = '1'

#URL for your Gitlab Instance.  if you are using hosted, then it will just be gitlab.com
GITLAB_URL = 'https://gitlab.com/'

# this token will be used whenever the API is invoked and
# the script will be unable to match the jira's author of the comment / attachment / issue
# this identity will be used instead.
GITLAB_TOKEN = 'PERSONAL TOKEN'

# set this to false if JIRA / Gitlab is using self-signed certificate.
VERIFY_SSL_CERTIFICATE = True

# Map of projects.  This is used for epic creation in Gitlab
PROJECT_MAP = {
    'project': 10000
}
# Labels to be applied to Gitlab epics
DEFAULT_LABELS = ['PM','release']

# Used to add labels in Gitlab to track Aha feature vs epic post import.
GL_AHA_LABELS = {
  'epic': 'Aha::Epic',
  'feature': 'Aha::Feature'
}

# IMPORTANT !!!
# make sure that user (in gitlab) has access to the project you are trying to
# import into. Otherwise the API request will fail.
#use the gitlab python module
# connect to Gitlab
gl = gitlab.Gitlab(GITLAB_URL,private_token=GITLAB_TOKEN)
gl.auth()


# Get epic or create one if it doesn't exist
def get_epic_id(epic_title,epic_description,extralabel,parent_id):
    group = gl.groups.get(PROJECT_MAP['project']) #get group info for project parent
    epics = group.epics.list() #get all the epics
    # existing_epic = False
    for epic in epics:
        if epic.title == epic_title:
            return epic
    # Epic doesn't exist, so let's create it
    nl = DEFAULT_LABELS.copy()
    nl.append(extralabel)
    newepic = {
        "title":epic_title,
        "description":epic_description,
        "labels":nl
    }
    if parent_id:
        newepic['parent_id']=parent_id
    new_epic = group.epics.create(newepic)

    return new_epic


# Get all of the epics for this release
# Aha API documentation : https://www.aha.io/api
aha_release_epics = requests.get(
    AHA_URL + 'releases/{}-R-{}/epics'.format(AHA_PROJECT,AHA_RELEASE),
    headers=AHA_HEADERS,
).json()['epics']

# release_epic is the epics associated with a release in Aha
for release_epic in aha_release_epics:
    #now that we have a list of epics, get specific info about each one
    print("Processing Epic {}".format(release_epic['reference_num']))
    aha_specific_epics = requests.get(
        AHA_URL + 'epics/{}'.format(release_epic['reference_num']),
        headers=AHA_HEADERS,
    ).json()['epic']

    epic_milestone = aha_specific_epics['release']['name']
    epic_description = markdownify(aha_specific_epics['description']['body']) + "\n\n{}\n".format(aha_specific_epics['resource'])
    epic_name = aha_specific_epics['name']
    gitlabepic = get_epic_id(epic_name,epic_description,GL_AHA_LABELS['epic'],False)
    epic_parent_id = gitlabepic.id

    for feature in aha_specific_epics['features']:
        print(feature['name'])
        aha_epic_features = requests.get(
            feature['resource'],
            headers=AHA_HEADERS
        ).json()['feature']

        feature_description = markdownify(aha_epic_features['description']['body']) + "\n\n{}\n".format(aha_epic_features['resource'])
        gl_feature_epic_id = get_epic_id(aha_epic_features['name'],feature_description,GL_AHA_LABELS['feature'],epic_parent_id)
