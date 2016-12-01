#!/usr/bin/env python

'''
Script which places a set of files / directories into the Galaxy tree and thus enabling Project / Allocation Management feature based on GOLD Allocation manager
'''

import os, sys, logging, stat
import pwd
import grp
import re
from shutil import copyfile, copytree


try:
	
    GALAXY_ROOT = sys.argv[1]
    runtype = sys.argv[2]

    if not os.path.isdir(GALAXY_ROOT+"/lib"):
       print GALAXY_ROOT + "/lib does not exist! Wrong GALAXY ROOT?"
       exit(0)
     
except:
    print "Usage ./patch_project_management.py GALAXY_ROOT runtype"
    print "GALAXY_ROOT is the galaxy directory containing /config /lib, etc. Mind the trailing slash!!"
    print "runtype can take two values : \"dry_run\"  or \"real\""
    exit(0)


print runtype

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


##APIs
api = ['Accounting_jobs.py','Accounting_project_management.py', 'decorators_usit.py', 'Project_managers.py']

if not os.path.isdir(GALAXY_ROOT + "lib/usit/python/"):
    
    print "patch log directory  'usit/python' not found, creating ..."
    
    os.makedirs(GALAXY_ROOT + "lib/usit/python/")
    
    # copy API files here
    os.chdir("./files_to_copy/API/")
    for c in api :
        if runtype == "real" :
            copyfile(c,GALAXY_ROOT + "lib/usit/python/"+c)
        print "API " + c + " copied"
    os.chdir("../..")
    
else:
    # copy API files here
    os.chdir("./files_to_copy/API/")
    for c in api :
        if runtype == "real" :
            copyfile(c,GALAXY_ROOT + "lib/usit/python/"+c)
        print "API " + c + " copied"
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


## Change ownership and permissions
os.chdir(GALAXY_ROOT)

# user galaxy
uid = 182649
gid = 70731
mode = 0o770

def change_ownership_and_permissions_recursive(path, uid, gid, mode):
    for root, dirs, files in os.walk(path, topdown=False):
        for dir in [os.path.join(root,d) for d in dirs]:
            os.chown(dir,uid, gid)
            os.chmod(dir, mode)
        for file in [os.path.join(root, f) for f in files]:
            os.chown(file,uid, gid)
            os.chmod(file, mode)
    print "Permissions for all new files changed!"
change_ownership_and_permissions_recursive(GALAXY_ROOT, uid, gid, mode)


print "Do not forget to read the README file for the additional configurations!"







