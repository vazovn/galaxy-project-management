# galaxy-project-management


=== PART 1 ===

clone the repo to your /tmp directory

run

./patch_project_management.py GALAXY_ROOT run-type

GALAXY_ROOT is the directory containing /lib, /config, .run.sh, etc
run-type can "dry-run" or "real". Null value defaults to "dry-run". Dry-run checks the prerequisites but does not patch and copy the files.

e.g.

./patch_project_management.py /home/galaxy/usit-galaxy dry-run

The script will place all the neccessary files for project management and resource allocation.


=== PART 2 ===

1. To enable the changes in the menu :
	
	cd GALAXY_ROOT
	make client
	
2. Create a file 

	project_managers.txt
	
	which shall contain all the project managers. This file is called by the controller
	
	lib/usit/python/Project_managers.py
	
	and intantiates its location path from a variable EXTERNAL_DBS in local_env.sh file

3. Add a line into galaxy.ini file containing the emails of all Project Administrators (GOLD adminstrators)

	project_admin_users = <EMAIL LIST>


ATTENTION : In order to use the project management feature, GOLD shall be installed and configured for your Galaxy instance!!
