#!/usr/bin/env python

'''
Script which places a set of files / directories into the Galaxy tree and thus enabling Project / Allocation Management feature based on GOLD Allocation manager
'''

import os, sys, logging, stat, getpass
import pwd
import grp
import re
from shutil import copyfile, copytree

## the script must be run as galaxy
whoami = getpass.getuser()
if whoami != 'galaxy' :
    print "You must run this script as galaxy user!"
    exit(0)

runtype = sys.argv[1]
print "Runtype :", runtype

## Set the paths to:
# EXTERNAL_DBS_PATH : the location (path) to all db text files containing information about projects managers and other info
# EXTERNAL_DBS_LINK_NAME : symbolic link pointing to EXTERNAL_DBS_PATH
# GALAXY_ROOT : directory with Galaxy installation

EXTERNAL_DBS_LINK_NAME = None
EXTERNAL_DBS_PATH = None
GALAXY_ROOT= None

if os.path.isfile('settings.sh'):
    fh=open('settings.sh', 'r')
    for line in fh :
        if re.search('EXTERNAL_DBS_LINK_NAME', line) :
            EXTERNAL_DBS_LINK_NAME = line.split('=')[1]
        if re.search('EXTERNAL_DBS_PATH', line) :
            EXTERNAL_DBS_PATH = line.split('=')[1]
        if re.search('GALAXY_ROOT', line) :
            GALAXY_ROOT = line.split('=')[1]
    fh.close()
else :
    print "Please fill in the variables in the file settings.txt in this directory!"
    exit(0)

# check if variables have been filled during the second run of deploy.sh
if GALAXY_ROOT is None :
    print "Please fill in GALAXY_ROOT in settings.sh!"
    exit(0)
elif EXTERNAL_DBS_PATH is None :
    print "Please fill in EXTERNAL_DBS_PATH in settings.sh!"
    exit(0)
elif EXTERNAL_DBS_LINK_NAME is None :
    print "Please fill in EXTERNAL_DBS_LINK_NAME in settings.sh!"
    exit(0)
else :
    print "Settings variables are instantiated!\n", GALAXY_ROOT, EXTERNAL_DBS_PATH, EXTERNAL_DBS_LINK_NAME

## Add the trailing slash if missing
GALAXY_ROOT = GALAXY_ROOT.strip()+'/' if not GALAXY_ROOT.endswith('/') else GALAXY_ROOT


if not os.path.isdir(GALAXY_ROOT+"/lib"):
       print GALAXY_ROOT + "/lib does not exist! Wrong GALAXY ROOT?"
       exit(0)
  
files_to_patch = {
			'lib/galaxy/config.py' : ['config','self.admin_users'],
			'lib/galaxy/managers/context.py' : ['context','def user_is_admin'],
			'lib/galaxy/managers/users.py' : ['users','def is_admin'],
			'lib/galaxy/web/__init__.py': ['init','require_admin'], # basically no need, just for consistence
			'lib/galaxy/web/base/controller.py': ['controller','USER_BOOTSTRAP_KEYS'],
			'lib/galaxy/web/framework/decorators.py' : ['decorators','from galaxy.web.framework import url_for'], # basically no need, just for consistence
			'lib/galaxy/tools/parameters/basic.py' : ['basic','determining dynamic options'],
			'templates/galaxy_client_app.mako' : ['galaxy_client_app','trans.user_is_admin'],
			'client/galaxy/scripts/layout/menu.js' : ['menu','user.get( \'is_admin\' )']
}

## Necessary checks before patching each file

for key,value in files_to_patch.iteritems():

    if os.path.isfile(GALAXY_ROOT+key):
        filename = GALAXY_ROOT+key
        if value[1] in open(filename).read():
            patch_command = "patch " + filename + " < patches/" + value[0] + ".patch"
            if runtype == "real" :
                    # patch command here
                    os.system(patch_command)
            else :
                    pass
        else:
            sys.exit('PATCH ERROR : neighbouring string ' + key + ' NOT FOUND, PROBABLY IN A DIFFERENT FILE!')
    else:
       sys.exit('PATCH ERROR : ' + key + ' FILE NOT FOUND, PROBABLY MOVED!')

print "All files patched OK !"


## Copy single files

## Controllers
controllers = ['project_admin.py','project_application.py']

if os.path.isdir(GALAXY_ROOT + "lib/galaxy/webapps/galaxy/controllers/"):
    print "patch log directory 'controllers' found"
    
    os.chdir("./files_to_copy/controllers/")
    
    # copy controller files here
    for c in controllers :
        if runtype == "real" :
            copyfile(c,GALAXY_ROOT + "lib/galaxy/webapps/galaxy/controllers/"+c)
        print "controller " + c + " copied"
    os.chdir("../..")
        
else :
    sys.exit('COPY ERROR : controllers directory NOT FOUND, PROBABLY MOVED!')


## APIs
api = ['Accounting_jobs.py','Accounting_project_management.py', 'decorators_usit.py', 'Project_managers.py']

if not os.path.isdir(GALAXY_ROOT + "lib/usit/python/"):
    
    print "patch log directory  'usit/python' not found, creating ..."
    
    os.makedirs(GALAXY_ROOT + "lib/usit/python/")
    
    # copy API files here
    os.chdir("./files_to_copy/API/")
    for a in api :
        if runtype == "real" :
            copyfile(a,GALAXY_ROOT + "lib/usit/python/"+a)
        print "API " + a + " copied"
    os.chdir("../..")
    
else:
    # copy API files here
    os.chdir("./files_to_copy/API/")
    for a in api :
        if runtype == "real" :
            copyfile(a,GALAXY_ROOT + "lib/usit/python/"+a)
        print "API " + a + " copied"
    os.chdir("../..")


## Utilities scripts
util_scripts = ['slurm_utils.sh']

if not os.path.isdir(GALAXY_ROOT + "lib/usit/scripts/"):
    
    print "patch log directory  'usit/scripts' not found, creating ..."
    
    os.makedirs(GALAXY_ROOT + "lib/usit/scripts/")
    
    # copy Utilities files here
    os.chdir("./files_to_copy/Utils/")
    for u in util_scripts :
        if runtype == "real" :
            copyfile(u,GALAXY_ROOT + "lib/usit/scripts/"+u)
        print "Utility script " + u + " copied"
    os.chdir("../..")
    
else:
    # copy Utilities files here
    os.chdir("./files_to_copy/Utils/")
    for u in util_scripts :
        if runtype == "real" :
            copyfile(u,GALAXY_ROOT + "lib/usit/scripts/"+u)
        print "Utility script " + u + " copied"
    os.chdir("../..")


## Copy directories

## Templates
if os.path.isdir(GALAXY_ROOT + "templates/webapps/galaxy/"):
    print "patch log directory : templates (makos) found"
    
    # copy mako files here (project_admin and project_application)
    if runtype == "real" :
        copytree('templates_to_copy/project_admin', GALAXY_ROOT + 'templates/webapps/galaxy/project_admin')
        copytree('templates_to_copy/project_applications', GALAXY_ROOT + 'templates/webapps/galaxy/project_applications')
        
    print "project_admin mako directory copied"
    print "project_applications mako directory copied"
        
        
else :
    sys.exit('COPY ERROR : templates (makos)  directory NOT FOUND, PROBABLY MOVED!')

## EXTERNAL DB symlink creation
if not os.path.isdir(EXTERNAL_DBS_PATH) :
    if runtype == "real" :
        os.symlink(EXTERNAL_DBS_PATH, EXTERNAL_DBS_LINK_NAME)
        print "EXTERNAL_DBS_PATH LINK created"
    else :
        print "DEBUG EXTERNAL_DBS_PATH LINK created"
else :
    print "EXTERNAL_DBS_PATH (cluster) is missing! "


print runtype + " run completed!"





