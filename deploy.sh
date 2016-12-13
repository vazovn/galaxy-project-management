#!/bin/bash

MYDIR="$(dirname "$(realpath "$0")")"

if [[ "$1" == "dry-run" ]] || [[ "$1" == "real" ]]  ; then
  :
else
  echo "Usage: ./deploy.sh dry-run/real"
  exit 0
fi

if [ ! -f "settings.sh" ]; then
    echo Please fill in the correct variables in the file settings.sh and run the script again!
    cp default-settings.sh settings.sh
    exit 1
fi

## Edit the files before deployment
. settings.sh

sed -i -e "s@EXTERNAL_DBS@${EXTERNAL_DBS_LINK_NAME}@g" ./files_to_copy/API/Project_managers.py
sed -i -e "s@/home/galaxy/additional_tools/slurm_utils.sh@${GALAXY_ROOT}/lib/usit/scripts@" ./files_to_copy/API/Accounting_jobs.py
sed -i -e "s%^GOLDDB=.*%GOLDDB=\"${GOLDDB}\"%" ./files_to_copy/API/Accounting_jobs.py
sed -i -e "s%^GOLDDB=.*%GOLDDB=\"${GOLDDB}\"%" ./files_to_copy/API/Accounting_project_management.py

sudo yum install npm.x86_64

sudo -u galaxy -H sh -c "/usr/bin/python ${MYDIR}/patch_project_management.py $1"
