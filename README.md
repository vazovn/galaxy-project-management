# galaxy-project-management   


## PART 1 - patching and copying

clone the repo to your /tmp directory

    **run ./deploy.sh run-type**

run-type can "dry-run" or "real". Null value defaults to "dry-run". 

The script will place all the neccessary files for project management and resource allocation.


## PART 2 - configuration

1. To enable the changes in the menu (Project Admin Tab):
	
    **cd GALAXY_ROOT** 
	
    **make client**
	
	
2. Create a file (_only_ if you don't take the file over from a previous version)

	_project_managers.txt_
	
	which shall contain all the project managers. This file shall be placed in 
	
    _/work/projects/galaxy/external_dbs_	
	
	is called by the controller _lib/usit/python/Project_managers.py_
	
	
3. Add a line into galaxy.ini file containing the emails of all Project Administrators (GOLD adminstrators)

    project_admin_users = <EMAIL LIST>
	
	
4. The code displaying the job parameters contains a list of projects accessible to a user. To enable this feature. the file: 

    GALAXY_ROOT/config/job_resource_params_conf.xml
	
	shall contain a parameter with name = "project", e.g.  

	```html
		<param label="Project" name="project" type="select" value="" help="Project to assign resource allocation to.">
	```  
	

5. Edit /etc/sudoers : add the following lines  

    Cmnd_Alias GOLD = /opt/gold/bin/*  

    Defaults:galaxy !requiretty  

    galaxy _hostname_=(root) NOPASSWD: GOLD  


6. Edit the file /home/galaxy/galaxy/.venv/bin/activate : add the following lines to the bottom of file

    export GALAXY_LIB=/home/galaxy/galaxy/lib  
    export PYTHONPATH=$GALAXY_LIB:/home/galaxy/galaxy/lib/usit/python  
    echo "PYTHONPATH SET IN .venv/bin/activate " $PYTHONPATH  



ATTENTION : In order to use the project management feature, GOLD shall be installed and configured for your Galaxy instance!!
