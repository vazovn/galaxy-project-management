#!/bin/env python

import os, sys, logging, threading, time, string, datetime
from sqlalchemy import *
import subprocess
import re
from pprint import *
import smtplib
from smtplib import SMTPException
import Project_managers

## needed to sort complex data structures
from operator import itemgetter, attrgetter


## ==== ACTIVATE THE DB ENGINE variable GOLDDB defined in startup_settings.sh  =====
#application_db_engine = create_engine(os.environ['GOLDDB'], encoding='utf-8')
#metadata = MetaData(application_db_engine)

def associate_users_to_projects ( emails, project) :
    """
    Used by PIs to associate users to the projects in GOLD which belong to the PI."
    """
 
    message = ''

    ## Get the account id
    get_account_id_command = "sudo /opt/gold/bin/glsaccount --show Id -n %s" % project
    p = subprocess.Popen(get_account_id_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.wait()
    account_id = ''
    account_info = []
    for line in p.stdout.readlines():
         account_info = line.split()
    ## The last line of the output
    account_id = account_info[0]

    ## convert single email string to one-element array for the for loop below
    if isinstance(emails, basestring) :
       emails = [emails]

    ## Process the users
    for email in emails :
        associate_user_to_project_command = "sudo /opt/gold/bin/gchproject --addUser %s %s" % (email, project)  
        p = subprocess.Popen(associate_user_to_project_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        p.wait()
        
        for line in p.stdout.readlines():
            if re.search("Successfully",line) :
                message += "User %s associated successfully to project %s .</br> " % (email,project)
                print "User %s associated successfully to project %s!" % (email,project)
            else :
                message += "Failed to associate user %s to project %s .</br> " % (email,project)
                message += line
                status = 'error'
                return (message,status)

        ## Add user to account. This account is shared account by all project members
        add_to_account_command = "sudo /opt/gold/bin/gchaccount --addUser %s %s" % (email,account_id ) 
        p = subprocess.Popen(add_to_account_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        p.wait()
        
        for line in p.stdout.readlines():
            if re.search("Successfully created",line) :
                message = message +  "User %s added to account %s in project %s.</br>" % (email,project,project)
                print "Added to account in %s  for user %s." % (project,email)
                status = 'done'
                
    return (message,status)


def add_remote_user_to_GOLD( email, feide_username, idp ) :
    """
    This is a new function for using Apache REMOTE_USER variable (SimpleSamplPhp or Dataporten)
    It is called by ../lib/galaxy/web/framework/webapp.py and requires that "use_remote_user" is set to True in galaxy.ini
    At registration all users are added to GOLD: User is inserted to 
    GOLD user DB and to gx_default (Galaxy default) project in GOLD. 
    """

    message = ""
    username = email
    user_info = []
    description = 'Unspecified IdP'
    print "==========  Accounting.py  IDP =========", idp
    
    ## Add the user to GOLD DB
    if re.search("test-fe.cbu.uib.no", idp ):
        description = 'NELS IdP user'
    elif  re.search("feide.no", idp ):
        description = 'FEIDE IdP user'
    
    useradd_command = "sudo /opt/gold/bin/gmkuser %s -d \"%s\"" % (username,description)
    p = subprocess.Popen(useradd_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.wait()

    ## Do not proceed if the user exists!!
    for line in p.stdout.readlines():
       if re.search("User already exists",line) :
            message = "User %s already exists in the GOLD DB!" % username
            return message

    ## Check if user has been added to GOLD DB
    user_check_command = "sudo /opt/gold/bin/glsuser -u %s " % username
    p = subprocess.Popen(user_check_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.wait()

    for line in p.stdout.readlines():
        if re.search(username,line) :
            user_info = line.split()

    ## Nikolay USIT - LAP customization
    ## Check if the user is associated with a MAS project    
    ## projects = _get_MAS_projects( feide_username)
    projects = []

    ## If the user is sucessfully created
    if user_info[0] == username and user_info[1] == 'True' :

        ## If the user is member of MAS projects and no 200 CPU hrs quota is allowed
        if len(projects) > 0 :
            proj_names = " ".join(projects)
            message = "A remote user %s has been added to the portal.</br>The user is a member of the project(s) %s and can only run jobs in these projects.\n" % (username,proj_names)
            #print "Feide user %s added successfully! User associated to Notur projects." % username
            return message
        
        else :  
            ## Add user to default galaxy project gx_default, create account and credit the account with default CPU hours
            add_to_gx_default_command = "sudo /opt/gold/bin/gchproject --addUsers %s gx_default " % username 
            p = subprocess.Popen(add_to_gx_default_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            p.wait()
        
            for line in p.stdout.readlines():
                if re.search("Successfully",line) :
                    message = "Remote user %s added successfully to GOLD DB and the default portal project (gx_galaxy) only.\n" % username
                    #print "Feide user %s added successfully to GOLD DB and the default portal project (gx_galaxy) only." % username

            ## Add user to account 'username_gx_default' in project gx_default
            create_account_command = "sudo /opt/gold/bin/gmkaccount -p gx_default -u %s -n \"%s_gx_default\"" % (username,username) 
            p = subprocess.Popen(create_account_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            p.wait()
        
            for line in p.stdout.readlines():
                if re.search("Successfully created",line) :
                    message = message +  "Created account in default portal project (gx_galaxy) for remote user %s. \n" % username
                    #print "Created account in gx_default for remote user %s." % username
                #print line


            ## Credit the account - 200 CPU hours
            
            ## Get the account id
            get_account_id_command = "sudo /opt/gold/bin/glsaccount --show Id -n %s_gx_default" % username
            p = subprocess.Popen(get_account_id_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            p.wait()
            account_id = ''
            account_info = []
            for line in p.stdout.readlines():
                  account_info = line.split()
            account_id = account_info[0]

            ## Credit the account (in hours)
            credit_account_command = "sudo /opt/gold/bin/gdeposit -h -a %s -z 200" % account_id
            p = subprocess.Popen(credit_account_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            p.wait()

            for line in p.stdout.readlines():
                if re.search("Successfully deposited",line) :
                    message = message +  "Credited account %s_gx_default for remote user %s in default portal project (gx_galaxy).\n" % (username,username)
                    message = message + line
                    #print "Credited account in gx_default for remote user %s." % username

            return message
          
    else :
        print "Failed to create a user in GOLD"



def add_feide_user_to_GOLD( email, feide_username ) :
    """
    This function is called by user.py & requires that "use_remote_user" is set to False in galaxy.ini
    At registration all feide users are added to GOLD: User is inserted to 
    GOLD user DB and to gx_default (Galaxy default) project in GOLD. This function
    presumes that a check has been already performed and the user is _NOT_ in the galaxy
    user DB
    """

    username = email
    user_info = []
    
    ## Add the user to GOLD DB
    useradd_command = "sudo /opt/gold/bin/gmkuser %s -d \"Default External academic -Galaxy user\"" % username
    p = subprocess.Popen(useradd_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.wait()

    ## Check if user has been added to GOLD DB
    user_check_command = "sudo /opt/gold/bin/glsuser -u %s " % username
    p = subprocess.Popen(user_check_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.wait()

    for line in p.stdout.readlines():
        if re.search(username,line) :
            user_info = line.split()

    ## Check if the user is associated with a MAS project    
    projects = _get_MAS_projects( feide_username)

    ## If the user is sucessfully created
    if user_info[0] == username and user_info[1] == 'True' :

        ## If the user is member of MAS projects and no 200 CPU hrs quota is allowed
        if len(projects) > 0 :
            proj_names = " ".join(projects)
            message = "</br>External academic  user %s has been added to the Lifeportal.</br>The user is a member of the project(s) %s and can only run jobs in these projects.</br>" % (username,proj_names)
            print "External academic  user %s added successfully! User associated to Notur projects." % username
            return message
        
        else :  
            ## Add user to default galaxy project gx_default, create account and credit the account with default CPU hours
            add_to_gx_default_command = "sudo /opt/gold/bin/gchproject --addUsers %s gx_default " % username 
            p = subprocess.Popen(add_to_gx_default_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            p.wait()
        
            for line in p.stdout.readlines():
                if re.search("Successfully",line) :
                    message = "</br>External academic  user %s added successfully to GOLD DB and the default lifeportal project (gx_galaxy) only.</br> " % username
                    print "External academic  user %s added successfully to GOLD DB and the default lifeportal project (gx_galaxy) only." % username

            ## Add user to account 'username_gx_default' in project gx_default
            create_account_command = "sudo /opt/gold/bin/gmkaccount -p gx_default -u %s -n \"%s_gx_default\"" % (username,username) 
            p = subprocess.Popen(create_account_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            p.wait()
        
            for line in p.stdout.readlines():
                if re.search("Successfully created",line) :
                    message = message +  "Created account in default lifeportal project (gx_galaxy) for External academic  user %s. </br>" % username
                    print "Created account in gx_default for External academic  user %s." % username
                print line


            ## Credit the account - 200 CPU hours
            
            ## Get the account id
            get_account_id_command = "sudo /opt/gold/bin/glsaccount --show Id -n %s_gx_default" % username
            p = subprocess.Popen(get_account_id_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            p.wait()
            account_id = ''
            account_info = []
            for line in p.stdout.readlines():
                  account_info = line.split()
            account_id = account_info[0]

            ## Credit the account (in hours)
            credit_account_command = "sudo /opt/gold/bin/gdeposit -h -a %s -z 200" % account_id
            p = subprocess.Popen(credit_account_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            p.wait()

            for line in p.stdout.readlines():
                if re.search("Successfully deposited",line) :
                    message = message +  "Credited account %s_gx_default for External academic  user %s in default lifeportal project (gx_galaxy).</br> " % (username,username)
                    message = message + line
                    print "Credited account in gx_default for External academic  user %s." % username

            return message
          
    else :
        print "Failed to create a user in GOLD"


def add_notur_non_feide_user_to_GOLD (email) :
    """
    This function is not implemented
    Automatically adds non-feide Notur users to GOLD. No PI action required. Called when "User > Register" tab has been used.
    """
    
    ## Check and reformat email / username if necessary
    message = ''
    description = ''
    username = email
    mas_username = _get_MAS_username ( email )
    email_username = email.split('@')[0]
    
    ## This is just a warning!!
    if mas_username != email_username :
        description = "Notur non-feide user with username and email prefix mismatch - username %s " % (mas_username)
        print "username and email prefix don't match!"
    else :
        description = "Notur non-feide user"
    
    ## Add the user to GOLD DB
    useradd_command = "sudo /opt/gold/bin/gmkuser %s -d \"%s\"" % (username,description)
    p = subprocess.Popen(useradd_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.wait()

    ## Check if user has been added to GOLD DB
    user_check_command = "sudo /opt/gold/bin/glsuser -u %s " % username
    p = subprocess.Popen(user_check_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    for line in p.stdout.readlines():
        if re.search(username,line) :
            user_info = line.split()

    ## If the user is sucessfully created
    if user_info[0] == username and user_info[1] == 'True' :

        # Add to MAS default Galaxy project
        add_to_project_command = "sudo /opt/gold/bin/gchproject --addUser %s MAS" % (username)
        p = subprocess.Popen(add_to_project_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        p.wait()
        
        for line in p.stdout.readlines():
            if re.search("Successfully",line) :
                message = "</br>Notur non-feide user %s added successfully to GOLD DB and the default Notur project <strong>MAS</strong>.</br>" % (username)
                print "Notur non-feide user %s added successfully to GOLD DB and the default Notur project " % username

        return message



def add_non_feide_user_to_GOLD (email, project, creator = None) :
    """
    Adds non-feide users to GOLD. Called by the PI (project administrator). The user receives an email notification to register in Galaxy
    """
    username = email
    message = ''
    
    ## Add the user to GOLD DB
    useradd_command = "sudo /opt/gold/bin/gmkuser %s -d \"non-feide user added by %s\"" % (username, creator)
    p = subprocess.Popen(useradd_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.wait()

    ## Check if user has been added to GOLD DB
    user_check_command = "sudo /opt/gold/bin/glsuser -u %s " % username
    p = subprocess.Popen(user_check_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    for line in p.stdout.readlines():
        if re.search(username,line) :
            user_info = line.split()

    ## If the user is sucessfully created
    if user_info[0] == username and user_info[1] == 'True' :

        # Add to local Galaxy project owned by PI
        if project :
             ## Add user to the selected galaxy project and create account
            add_to_project_command = "sudo /opt/gold/bin/gchproject --addUsers %s %s " % (username, project)
            p = subprocess.Popen(add_to_project_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            p.wait()
        
            for line in p.stdout.readlines():
                if re.search("Successfully",line) :
                    message = "</br>Non-feide user %s added successfully to GOLD DB and the project <strong>%s</strong>.</br>" % (username,project)
                    print "Non-feide user %s added successfully to GOLD DB and the selected galaxy project" % username

            ##  Add user to the account of the project.  ##
            
            ## Get the account id
            get_account_id_command = "sudo /opt/gold/bin/glsaccount --show Id -n %s " % (project)
            p = subprocess.Popen(get_account_id_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            p.wait()
            account_id = ''
            account_info = []
            for line in p.stdout.readlines():
                  account_info = line.split()
            account_id = account_info[0]

             ## Add user to account. This account is shared account by all project members
            add_to_account_command = "sudo /opt/gold/bin/gchaccount --addUser %s %s" % (username,account_id ) 
            p = subprocess.Popen(add_to_account_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            p.wait()
        
            for line in p.stdout.readlines():
                if re.search("Successfully created",line) :
                    message = message +  "Non-feide user %s added to account %s in project %s.</br>" % (username,project,project)
                    print "Added to account in %s  for Non-feide user %s." % (project,username)

                    # Send notification email Galaxy project
                    sender = 'noreply@usit.uio.no'
                    receiver = username
                    replyto = creator
                    header = 'To:' + receiver + '\nFrom: ' + sender + '\nReply-to: ' + creator + '\nSubject:You have been added to a Lifeportal project'
                    email_msg = header + '\nYou have been added to the Lifeportal project : ' + project +'. Please log in to https://lifeportal.uio.no and register into Lifeportal. You shall chose for username exactly the same email address (' + receiver + ') as the one used in this message!!!\nBest regards,\n' + creator
                    print "=== EMAIL notification message ===\n",email_msg

                    try:
                      smtpObj = smtplib.SMTP('localhost')
                      smtpObj.sendmail(sender, receiver, email_msg)
                      print "Successfully sent email"
                    except SMTPException:
                      print "Error: unable to send email"

            return message

def get_owned_GOLD_projects ( username ) :
    """
    Selects the GOLD projects owned/created by the user calling the function  
    """
    get_projects_command = "sudo /opt/gold/bin/glsproject --show Name,Organization | grep %s " % username
    p = subprocess.Popen(get_projects_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.wait()
    projects = []
    for line in p.stdout.readlines():
        project_line = line.split()
        projects.append(project_line[0])
    print "Accounting : I own the following GOLD projects ",projects    
    return projects

def get_other_managed_GOLD_projects ( username ) :
    """
    Selects the GOLD projects like BIR and CLOTU. This function is only called 
    from project_admin_grid_base.mako iff the user is a Project Administrator
    """
    get_projects_command = "sudo /opt/gold/bin/glsproject --show Name,Description"
    p = subprocess.Popen(get_projects_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.wait()
    projects = []
    for line in p.stdout.readlines():
        project_line = line.split()
        if re.search( "CLOTU", project_line[1]) or re.search( "BIR", project_line[1]) :
              projects.append(project_line[0])
    print "Accounting : I am allowed to manage also the following GOLD projects ",projects
    return projects


def list_owned_GOLD_projects ( username ) :
    """
    Lists the GOLD projects, users, descriptions of owned/created by the user calling the function  
    """
    get_projects_command = "sudo /opt/gold/bin/glsproject --show Organization,Name,Users,Active,Description | grep %s " % username      
    p = subprocess.Popen(get_projects_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.wait()
    projects = []
    for line in p.stdout.readlines():
       project_line = line.split()
       if project_line[0] == username :
           ## Join the description in one cell
           project_line[4:] = [" ".join(project_line[4:])] 
           ## Replace the comma with newline in users list
           project_line[2] = project_line[2].replace(",","</br>")
           ## Remove the owner
           project_line = project_line[1:]
           
           ## Get the project account info
           project_name = project_line[0]
           get_account_info_command = "sudo /opt/gold/bin/glsaccount -h --show Amount,Projects | grep -w %s | uniq " % project_name
           p = subprocess.Popen(get_account_info_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
           p.wait()
           amount = ''
           for line in p.stdout.readlines():
                account_info = line.split()
                amount = account_info[0]
           project_line[3:3] = [amount]
           
           ## The project info is now collected
           projects.append(project_line)
    
    projects_sorted = sorted(projects, key=itemgetter(0))
    print "Admin is True : Accounting : I own the following GOLD projects ", projects_sorted
    return projects_sorted

def list_all_GOLD_projects (filter_by_project_name = None) :
    """
    Lists all GOLD projects or one defined in filter_by_project_name
    """
 
    connection = application_db_engine.connect()

    if filter_by_project_name :
        result = connection.execute("select\
                                                                   g_organization,\
                                                                   g_name,\
                                                                   g_active,\
                                                                   g_description\
                                                           from\
                                                                   g_project\
                                                           where\
                                                                   g_active = 'True'\
                                                           and\
                                                                   g_name = '%s' " % filter_by_project_name)
    else :
        result = connection.execute("select\
                                                                   g_organization,\
                                                                   g_name,\
                                                                   g_active,\
                                                                   g_description\
                                                           from\
                                                                   g_project\
                                                           where\
                                                                   g_active = 'True' ")

    project_data = []
    project_data_users = []
    project_list = []
    users_list = {}
    projects_amount_start_end = {}
    final_list = []
    
    if not result :
       print "No projects available!"
       return project_data
              
    for row in result:
       if not re.search("@",str(row[0])) :
             pass
       elif re.search("root@",str(row[0])) :
             pass
       else:
             project_data.append(row)
             project_id = "'"+row[1]+"'"
             project_list.append(project_id)
    
    #print "Admin is True : Accounting : All GOLD projects ", project_data
    #print "Admin is True : Accounting : All GOLD projects NAMES ", project_list
    
    string_project_list = ','.join(project_list)
    
    users = connection.execute("select\
                                                                  g_project,\
                                                                  array_to_string(array_agg(g_name),',')\
                                                          from\
                                                                  g_project_user\
                                                         where\
                                                                  g_project in ( %s ) \
                                                         group by 1" % string_project_list)
    
    #store users in a hash : key - project_name (lpXX), value - user list
    for row in users:
       users = row[1].replace(",","</br>")
       users_list[row[0]] = users

    #append user list to project data array
    for k in users_list :
       for p in project_data :
            if k == p[1] :
               p_list = list(p)
               p_list.insert(2,users_list[k])
               project_data_users.append(p_list)
               continue
             
    #print "Admin is True : Accounting : All GOLD projects WITH USERS ", project_data_users
    
    amounts_and_time  = connection.execute("select\
                                                                                           g_account_project.g_name,\
                                                                                           g_allocation.g_id,\
                                                                                           g_allocation.g_amount,\
                                                                                           g_allocation.g_start_time,\
                                                                                           g_allocation.g_end_time\
                                                                                    from\
                                                                                           g_account_project,\
                                                                                           g_allocation\
                                                                                   where\
                                                                                           g_account_project.g_name in ( %s ) \
                                                                                           and\
                                                                                           g_account_project.g_account = g_allocation.g_account\
                                                                                   order by\
                                                                                           g_allocation.g_id " % string_project_list )
    
    
    for row in amounts_and_time :
         amount = "{0:.2f}".format(row[2]/3600)
         start = datetime.datetime.fromtimestamp(row[3]).strftime('%Y-%m-%d')
         stop = datetime.datetime.fromtimestamp(row[4]).strftime('%Y-%m-%d')
         projects_amount_start_end[row[0]] = [amount, start, stop]
         
     
    for p in projects_amount_start_end :
         for r in project_data_users :
                if p == r[1] :
                     r.insert(4,projects_amount_start_end[p][0])
                     r = r + projects_amount_start_end[p][1:]
                     final_list.append(r)
                     continue
                     
    connection.close()
    
    #print "Admin is True : Accounting : All GOLD projects FINAL LIST ",  final_list
    
    return final_list


def user_is_in_GOLD_DB ( email ) :
    """
    Checks if the user in in the GOLD DB
    """
    username = email
    user_info =  []
    user_check_command = "sudo /opt/gold/bin/glsuser -u %s " % username
    p = subprocess.Popen(user_check_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    for line in p.stdout.readlines():
        if re.search(username,line) :
            user_info = line.split()

    if user_info and user_info[0] == username and user_info[1] == 'True' :
        return True
    else :
        return False

def user_is_in_MAS_DB ( email ) :
    """
    Checks if the user in in the MAS DB, username is an email
    """
    username = email
    projects = _get_MAS_projects (username)
    
    if len(projects) > 0 :
        return True
    else :
        return False

def _get_MAS_projects ( email ):
   """
   Gets the MAS projects the user is member of (email is an email if non-feide, or e.g. user@uio.no if feide)
   """
   
   ## Get the real username from MAS
   username_mas = _get_MAS_username ( email )
   print "Accounting : real MAS (Notur) username ", username_mas
   
   username_open = '<'+username_mas+'>'
   username_close = '</'+username_mas+'>'
   f=open('/cluster/var/user-info', 'r')
   takeline = False
   projectline = ''
   projects = []
   for line in f :
        if re.search( username_open, line) :
            takeline = True
        if takeline == True  and not re.search( username_open , line) and not re.search( username_close, line) :
            if re.search('projects', line) :
                projectline = line.split()
                if len(projectline) == 2 and len(projectline[1]) > 0 :
                     full_project_list = projectline[1].split(',')
                     for p in full_project_list :
                          if p != 'uio' :
                              projects.append(p)
        if re.search(username_close, line):
            break
            
   f.close()

   print "Accounting : I am member of the following MAS (Notur) projects ", projects

   return projects


def _get_MAS_username (email ) :
   """
   Gets the MAS correct username : 
   Necessary check in case the MAS email prefix and the MAS username don't match, 
   e.g. uname = 'pr2f2815' <> email = 'dimitry.pokhotelov@fmi.fi'
   """

   username = email
   uname = ''
   email = ''
    
   ## Get the correct username
   f=open('/cluster/var/user-info', 'r')
   for line in f :
       if re.search( "uname", line) :
           uname = line.split()[1]
       if re.search( "status", line) :
           status = line.split()[1]
       if re.search( "email", line) and line.split()[0] == "email":
           email = line.split()[1]
       
       
       ## entire Notur email == the entire Galaxy email (e.g. username = email = 'dimitry.pokhotelov@fmi.fi')
       if email == username and status == 'open':
           username = uname
           break
       ## email prefix in Galaxy == Notur username ( the Galaxy prefix is actually the FEIDE username prefix  : nikolaiv@uio.no)
       else :
           email_prefix = username.split('@')[0]
           if email_prefix == uname and status == 'open':
                username = uname
                break
   f.close()
   
   return username
    
def _generate_project_name() :
    """
    Generates a local galaxy project name, e.g. lp45
    """

    project_list = []
    projects = list_all_GOLD_projects()
    
    ## Increment if projects exist
    if projects and len(projects) > 0 :
        for project in projects :
              if re.match('^lp\d+',project[1]) :
                  project_list.append(project[1])

        def atoi(text):
              return int(text) if text.isdigit() else text

        def natural_keys(text):
              return [ atoi(c) for c in re.split('(\d+)', text) ]

        project_list.sort(key=natural_keys)
    
        last_project =  re.split('(\d+)', project_list[-1])
        digit = int(last_project[1])+1
        generated_project_name = "lp" + str(digit)

    ## This is the first project!
    else :
        generated_project_name = "lp1"
    
    print "Generated project name ", generated_project_name
    return generated_project_name
    

def get_GOLD_project_info( project_name ) :
   """
   Displays the output of glsproject command
   """
   
   project_info = []
   
   project_info_display_command = "sudo /opt/gold/bin/glsproject --show Name,Users,Description %s " % project_name
   p = subprocess.Popen(project_info_display_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
   p.wait()
   for line in p.stdout.readlines():
          info_line = line
   
   project_info = info_line.split()
    
   ## Replace the comma with newline in users list
   project_info[1] = project_info[1].replace(",","</br>")
   ## Join the description in one cell
   project_info[2:] = [" ".join(project_info[2:])] 
   
   if project_info :
       return project_info


def get_GOLD_project_usage( project_name,start_date,end_date ) :
   """
   Displays the output of gusage command
   """
   project_usage = ''
   project_usage_command = "sudo /opt/gold/bin/gusage  -p %s -s %s -e %s" % (project_name,start_date,end_date)
   p = subprocess.Popen(project_usage_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
   p.wait()
   for line in p.stdout.readlines():
       line = line.replace("#","")
       project_usage += line + "</br>"
   
   if project_usage :
       return project_usage


def get_gx_default_project_usage( username ) :
   """
   Displays the output of gusage command
   """
   gx_project_usage = ''
   #gx_project_usage_command = "sudo /opt/gold/bin/gbalance --show Available -h -p gx_default -u %s" % ( username )
   gx_project_usage_command = "sudo /opt/gold/bin/gbalance --show Available,Name -h | grep %s_gx_default | awk '{print $1;}'" % ( username )
   p = subprocess.Popen(gx_project_usage_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
   p.wait()
   for line in p.stdout.readlines():
       gx_project_usage = line
   
   if gx_project_usage :
       return gx_project_usage



def add_project_to_GOLD( email, project_name, cpu_amount, gold_project_description, start_date, end_date) :
   """
   Adds a project to the GOLD DB. The user running the function is the owner of the project (email is the username).
   Owner is encoded in "Organization"
   """
   print "owner EMAIL ", email
   message = ''
   
   ## Create ownership : "Organization" contains the owner (by email). GOLD is responsible for duplicates. 
   create_organization_command = "sudo /opt/gold/bin/goldsh Organization Create Name=\'%s\' " % email
   p = subprocess.Popen(create_organization_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
   p.wait()

   ## For debugging purposes only. GOLD skips the creation request if Organization exists
   for line in p.stdout.readlines():
         if re.search("Successfully",line) :
                 print "Organization %s created " % email
                 break
         else :
                 print line
                 
   ## Create the project itself
   create_project_command = "sudo /opt/gold/bin/gmkproject -d \"%s\" %s -u MEMBERS --createAccount=False -o %s " % ( gold_project_description, project_name, email)
   p = subprocess.Popen(create_project_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
   p.wait()

   ## For debugging
   for line in p.stdout.readlines():
         if re.search("Successfully",line) :
               message = "Succesfully created project : %s" % project_name
         else :
               message = line
               
   ## Create account
   create_account_command = "sudo /opt/gold/bin/gmkaccount -p %s -n \"%s\" -u MEMBERS -d \"account for %s project \"" % ( project_name, project_name, project_name ) 
   p = subprocess.Popen(create_account_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
   p.wait()
        
   for line in p.stdout.readlines():
          if re.search("Successfully created",line) :
                 message = message +  "</br>Created account for project %s . </br>" % project_name
                 print "Created account for project %s." % project_name
          else :
                 message = line

   ## Credit the account (in hours)
   credit_account_command = "sudo /opt/gold/bin/gdeposit -h -s %s -e %s -z %s -p %s " % (start_date, end_date, cpu_amount, project_name)
   p = subprocess.Popen(credit_account_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
   p.wait()

   for line in p.stdout.readlines():
         print "Line from gdeposit in add_project_to_GOLD "
         if re.search("Successfully deposited",line) :
                message = message +  "Credited account %s in project %s .</br> " % (project_name, project_name)
                print "Credited account in project %s with amount %s hours " % (project_name, cpu_amount)

   return message


def deactivate_project( project_name ) :
   """
   Deactivates the project/account definitively from GOLD DB. Can be activated
   """
   deactivate_project_command = "sudo /opt/gold/bin/gchproject -I -p %s" % project_name
   p = subprocess.Popen(deactivate_project_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
   p.wait()
   
   for line in p.stdout.readlines():
         if re.search("Successfully",line) :
               message = "Succesfully deactivated project : %s" % project_name
               status = 'done'
               break
         else :
               message = line
               status = 'error'
               
   return (message,status)
   

def activate_project( project_name ) :
   """
   Deactivates the project/account definitively from GOLD DB. Can be activated
   """
   activate_project_command = "sudo /opt/gold/bin/gchproject -A -p %s" % project_name
   p = subprocess.Popen(activate_project_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
   p.wait()
   
   for line in p.stdout.readlines():
         if re.search("Successfully",line) :
               message = "Succesfully activated project : %s" % project_name
               status = 'done'
               break
         else :
               message = line
               status = 'error'
               
   return (message,status)
   


def modify_project( project_name, cpu_amount, start_date, end_date)  :
   """
   Changes the cpu_hours amount (allocation) and start/end dates of an already existing project account. 
   Can only be used for local galaxy projects which have 1 account per project.
   DO NOT USE FOR gx_default (default feide users projects)
   Called from "Modify" projects button
   """
   message = ''
   status = ''
   
   print "cpu amount", cpu_amount

   if not re.match('^-',cpu_amount):
       ## deposit in hours
       modify_command = "sudo /opt/gold/bin/gdeposit -h -p %s -s %s -e %s -z %s" % (project_name, start_date, end_date, cpu_amount)
       p = subprocess.Popen(modify_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
       p.wait()

       for line in p.stdout.readlines():
             if re.search("Successfully deposited",line) :
                    message = message +  "Modified project %s .</br> " % project_name
                    message = message + line
                    status = 'done'
                    print "Credited account in project %s with cpu_amount %s hours " % (project_name, cpu_amount)
                    break
             else :
                    message += line + "</br>"
                    status = 'error'
                    print "Accounting : GOLD Error line credit account >>>", line
  
   else :
       ## withdraw
       a = re.split('-',cpu_amount)
       cpu_amount = a[1]
       modify_command = "sudo /opt/gold/bin/gwithdraw -h -p %s  -z %s" % (project_name, cpu_amount)
       p = subprocess.Popen(modify_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
       p.wait()

       for line in p.stdout.readlines():
             if re.search("Successfully withdrew",line) :
                    message = message +  "Withdrew %s cpu_hours from project %s. " %  (cpu_amount, project_name)
                    status = 'done'
                    print "Withdrew %s cpu_hours from project %s" % (cpu_amount, project_name)
                    break
             else :
                    message += line + "</br>"
                    status = 'error'
                    print "Accounting : GOLD Error line withdraw >>>", line


   return (message,status)
                   

def check_pending_projects ( project_id = None, email = None) :
    """
    Gets the list of pending project for approval in GOLD table 'g_lp_applications'
    """

    pending_projects = []
    
    connection = application_db_engine.connect()
    
    if project_id is None :
         if email :
         ### Managers see only their own pending applications
              result = connection.execute("select\
                                                                 id,\
                                                                 requestor,\
                                                                 email,\
                                                                 institution,\
                                                                 country,\
                                                                 project_name,\
                                                                 cpu_hours,\
                                                                 description,\
                                                                 applications,\
                                                                 start_date,\
                                                                 end_date,\
                                                                 date_of_application\
                                                             from\
                                                                 g_lp_applications\
                                                             where\
                                                                 actual_status = 'pending' and email = '%s' " % email)
         else :
         ### Administrator see all pending applications
              result = connection.execute("select\
                                                                   id,\
                                                                   requestor,\
                                                                   email,\
                                                                   institution,\
                                                                   country,\
                                                                   project_name,\
                                                                   cpu_hours,\
                                                                   description,\
                                                                   applications,\
                                                                   start_date,\
                                                                   end_date,\
                                                                   date_of_application\
                                                             from\
                                                                   g_lp_applications\
                                                             where\
                                                                   actual_status = 'pending'")
    else :
         ### Project displayed for modifications before final approval
              result = connection.execute("select\
                                                                 id,\
                                                                 requestor,\
                                                                 email,\
                                                                 institution,\
                                                                 country,\
                                                                 project_name,\
                                                                 cpu_hours,\
                                                                 description,\
                                                                 applications,\
                                                                 start_date,\
                                                                 end_date,\
                                                                 date_of_application\
                                                             from\
                                                                 g_lp_applications\
                                                             where\
                                                                 id = '%s' " % project_id)
  
    for row in result:
                pending_projects.append(row)
                
    connection.close()
                
    return pending_projects
        
def approve_pending_project ( kwd) :
    """
    Approves (activates) a pending project from GOLD table 'g_lp_applications'
    
    Data collected so has to be put into as follows :
    
    --- both for GOLD DB and Lifeportal application table : email, cpu_amount, start_date, end_date
    --- for GOLD original DB : description
    --- for Lifeproject application table : project_id
    
    Still needed to be generated by this function :
    
    --- both for GOLD DB and Lifeportal application table : project_code (lpXX)
    --- for Lifeproject application table : actual_status, last_modified, status_before_last_modification, last_modified_by
    
    """

    print "All kwd  approve pending project ", kwd

    connection = application_db_engine.connect()
    
    last_modified_by = kwd['last_modified_by'].strip()
    project_id = kwd['project_id']
    email = kwd['email'].strip()
    cpu_amount = kwd['cpu_hours']
    description = kwd['description']
    start_date = kwd['start_date']
    end_date = kwd['end_date']
    status_before_last_modification = 'pending'
    project_name = kwd['project_name']
    application_date = kwd['application_date']
    
    ## ###################  Reject Lifeportal Application  #################
    if 'reject_pending_project' in kwd :

        if  'reason_for_rejection' in kwd :
              reason_for_rejection_email_version = kwd['reason_for_rejection']
              reason_for_rejection = re.escape(kwd['reason_for_rejection'])
              del kwd['reason_for_rejection']
        else :
              reason_for_rejection = "NA"

        connection.execute("update g_lp_applications set \
                                              reason_for_rejection = '%s', \
                                              last_modified_by = '%s', \
                                              last_modified = NOW(), \
                                              actual_status = 'rejected' \
                                           where \
                                              id = '%s' " % ( 
                                              reason_for_rejection,
                                              last_modified_by,
                                              project_id
                                              )
                                          ) 
        ## Flush button
        del kwd['reject_pending_project']
      
        ## Send application rejection email
        sender = 'lifeportal-help@usit.uio.no'
        receiver = email
        bcc = 'n.a.vazov@usit.uio.no'
        project_string = '\nproject name : ' + project_name +  '\ncpu_amount : ' + cpu_amount + '\ndescription : ' + description + '\nstart_date : ' + start_date + '\nend_date : ' + end_date + '\napplication_date : ' + application_date
        header = 'To:' + receiver + '\nFrom: ' + sender + '\nBcc: ' + bcc + '\nSubject:Your Lifeportal application has been rejected \n'
        email_msg = header + '\nYour Lifeportal application :\n' + project_string + '\n\nhas been rejected for the following reasons: ' + reason_for_rejection_email_version + '\nPlease, apply again.\n\nThe Lifeportal Resource Allocation Committee'
        
        ##For debugging
        msg = email_msg
        msg = msg.encode('utf-8')
        print "=== EMAIL application rejection notification message ===\n", msg

        try:
                smtpObj = smtplib.SMTP('localhost')
                smtpObj.sendmail(sender, [receiver,bcc], email_msg.encode('utf-8'))
                print "Successfully sent rejection email"
        except SMTPException:
                print "Error: unable to send rejection email"
                
    ## ###################  Approve Lifeportal Application #################
    elif 'approve_pending_project' in kwd  :

        message = ''

        ## Generate the project code (lpXX)
        project_code = _generate_project_name()
    
        ## Create project in GOLD DB - it creates Organization, project, account and deposits the cpu_amount into the account
        message = add_project_to_GOLD( email, project_code, cpu_amount, project_name, start_date, end_date) 
        print "Approved application is a project in GOLD DB - READY! ", message
        
        ## Add the project manager to the project users list 
        ## the function takes a dictionary, so we need to send email as a 1 element dictionary
        emails = []
        emails.append(email)
        (associate_user_message,status) = associate_users_to_projects ( emails, project_code )
        message = message + '\n' + associate_user_message

        ## Update Lifeproject application table
        connection.execute("update g_lp_applications set \
                                              status_before_last_modification = 'pending',\
                                              last_modified = NOW(),\
                                              last_modified_by = '%s' ,\
                                              actual_status = 'approved',\
                                              project_code = '%s' ,\
                                              cpu_hours = '%s',\
                                              start_date = '%s',\
                                              end_date = '%s' \
                                         where \
                                              id = '%s' " % ( 
                                              last_modified_by,
                                              project_code,
                                              cpu_amount,
                                              start_date,
                                              end_date,
                                              project_id
                                              )
                                          ) 
        ## Flush button
        del kwd['approve_pending_project']
                                          
        ## Add project owner to project manager list (project_manager.txt) if not already registered
        project_manager_message = Project_managers.add_project_manager (email ) 
        if not re.match(r'Error', project_manager_message) :
                 message = message + '\n' + project_manager_message
                 print "Project manager fixed!"

       ## Send email notification about the approved project
        sender =  'lifeportal-help@usit.uio.no'
        receiver = email
        bcc = 'n.a.vazov@usit.uio.no'
        header = 'To:' + receiver + '\nFrom: ' + sender + '\nBcc: ' + bcc +'\nSubject:Your Lifeportal application has been approved \n'
        email_msg = header + '\nYour Lifeportal application :\n' + project_name + '\n\nhas been approved today. The project code associated to it is ' + project_code + '. Please use this code when running your jobs.\nBest regards,\n\nThe Lifeportal Resource Allocation Committee'

        ##For debugging
        msg = email_msg
        msg = msg.encode('utf-8')
        print "=== EMAIL application approval notification message ===\n", msg

        try:
                smtpObj = smtplib.SMTP('localhost')
                smtpObj.sendmail(sender, [receiver,bcc], email_msg.encode('utf-8'))
                print "Successfully sent email"
        except SMTPException:
                print "Error: unable to send email"

        return message

def check_rejected_projects ( project_id = None, email = None) :
    """
    Gets the list of pending projects for approval in GOLD table 'g_lp_applications'
    """

    rejected_projects = []
    
    connection = application_db_engine.connect()
    
    if project_id is None :
         if email :
         ### Managers see only their own pending applications
              result = connection.execute("select\
                                                                 id,\
                                                                 requestor,\
                                                                 email,\
                                                                 institution,\
                                                                 country,\
                                                                 project_name,\
                                                                 cpu_hours,\
                                                                 description,\
                                                                 applications,\
                                                                 start_date,\
                                                                 end_date,\
                                                                 date_of_application,\
                                                                 reason_for_rejection\
                                                             from\
                                                                 g_lp_applications\
                                                             where\
                                                                 actual_status = 'rejected' and email = '%s' " % email)
         else :
         ### Administrators see all pending applications
              result = connection.execute("select\
                                                                   id,\
                                                                   requestor,\
                                                                   email,\
                                                                   institution,\
                                                                   country,\
                                                                   project_name,\
                                                                   cpu_hours,\
                                                                   description,\
                                                                   applications,\
                                                                   start_date,\
                                                                   end_date,\
                                                                   date_of_application, \
                                                                   reason_for_rejection\
                                                             from\
                                                                   g_lp_applications\
                                                             where\
                                                                   actual_status = 'rejected'")
    else :
         ### Project displayed for modifications before final approval
              result = connection.execute("select\
                                                                 id,\
                                                                 requestor,\
                                                                 email,\
                                                                 institution,\
                                                                 country,\
                                                                 project_name,\
                                                                 cpu_hours,\
                                                                 description,\
                                                                 applications,\
                                                                 start_date,\
                                                                 end_date,\
                                                                 date_of_application,\
                                                                 reason_for_rejection\
                                                             from\
                                                                 g_lp_applications\
                                                             where\
                                                                 id = '%s' " % project_id)
  
    for row in result:
                rejected_projects.append(row)
                
    connection.close()
                
    return rejected_projects
        

def register_project_application ( kwd) :
    """
    Registers a Lifeportal application ans sets it into the GOLD table 'g_lp_applications'
    """

    print "All kwd  register application ", kwd

    connection = application_db_engine.connect()

    if 'agree_checkbox' in kwd and kwd['agree_checkbox'] == 'on' and 'tsd_checkbox' in kwd and kwd['tsd_checkbox'] == 'on':
           
           ## block if missing name
           if kwd['name'] :
                name = re.escape(kwd['name'])
           else :
                 message = "Please add the name of the responsible person!"
                 status = 'error'
                 return (message,status)

           ## block if missing job_title
           if kwd['job_title'] :
                 job_title = re.escape(kwd['job_title'])
           else :
                 message = "Please add job title!"
                 status = 'error'
                 return (message,status)
           
           email = kwd['email']
                   
           ## block if missing cellphone
           if kwd['cellphone'] :
                cellphone = re.escape(kwd['cellphone'])
           else :
                 message = "Please add cellphone number!"
                 status = 'error'
                 return (message,status)
           
           ## phone
           phone = ''
           if not kwd['phone'] :
                   phone = kwd['cellphone']
           else :
                   phone = kwd['phone']
                   
           ## block if missing institution
           if kwd['institution'] :
                institution = re.escape(kwd['institution'])
           else :
                 message = "Please add institution!"
                 status = 'error'
                 return (message,status)
           
           ## block if missing country
           
           if kwd['country'] :
                country = re.escape(kwd['country'])
           else :
                 message = "Please add country!"
                 status = 'error'
                 return (message,status)
           
           ## block if missing project_name
           if kwd['project_name'] :
                project_name = re.escape(kwd['project_name'])
           else :
                 message = "Please add project name!"
                 status = 'error'
                 return (message,status)
           
           ## block if missing cpu_hours
           if kwd['cpu_hours'] and kwd['cpu_hours'].isdigit() :
                cpu_amount = re.escape(kwd['cpu_hours'])
           else :
                 message = "Please add cpu hours or check your format! The field may only contain digits!"
                 status = 'error'
                 return (message,status)
           
           ## block if no applications are selected
           applications = ''
           if 'applications' in kwd :
                 applications_list = kwd['applications']
                 if isinstance(applications_list,list) :
                       applications = ",".join(applications_list)
                 elif isinstance(applications_list,unicode)  :
                       applications = applications_list
           else :
                 message = "Please select Applications from the Application dropdown, click on it to display application list !"
                 status = 'error'
                 return (message,status)
           
           ## block if missing description
           if kwd['project_description'] :
                description_email_version = kwd['project_description']
                description = re.escape(kwd['project_description'])
           else :
                 message = "Please add project description!"
                 status = 'error'
                 return (message,status)
           
           start_date = kwd['start_date']
           end_date = kwd['end_date']
           last_modified_by = kwd['last_modified_by']

           ## Update Lifeproject application table
           connection.execute("insert into g_lp_applications (\
                                              requestor ,\
                                              requestor_job, \
                                              email, \
                                              phone ,\
                                              cellphone, \
                                              institution, \
                                              country, \
                                              project_name, \
                                              cpu_hours, \
                                              applications,\
                                              description, \
                                              start_date, \
                                              end_date ,\
                                              date_of_application, \
                                              actual_status, \
                                              last_modified, \
                                              last_modified_by, \
                                              status_before_last_modification ) \
                                              VALUES (\
                                              '%s' ,\
                                              '%s', \
                                              '%s', \
                                              '%s', \
                                              '%s' ,\
                                              '%s', \
                                              '%s', \
                                              '%s', \
                                              '%d' ,\
                                              '%s', \
                                              '%s', \
                                              '%s', \
                                              '%s', \
                                              NOW(), \
                                              'pending',\
                                              NOW(), \
                                              '%s', \
                                              'pending' ) " % ( 
                                                                name,
                                                                job_title,
                                                                email,
                                                                phone,
                                                                cellphone,
                                                                institution,
                                                                country,
                                                                project_name,
                                                                int(cpu_amount),
                                                                applications,
                                                                description,
                                                                start_date,
                                                                end_date,
                                                                last_modified_by
                                                              ) )
           message =  "Application stored as 'pending'. A committee will review it as soon as possible and come back to you with further information."
           status = 'done'
           
           ## Send confirmation 
           sender = 'n.a.vazov@usit.uio.no'
           replyto = 'lifeportal-help@usit.uio.no'
           bcc = 'n.a.vazov@usit.uio.no'
                      
           receiver = email
           project_string = '\nproject name : ' + project_name +  '\ncpu_amount : ' + cpu_amount + '\ndescription : ' + description_email_version + '\nstart_date : ' + start_date + '\nend_date : ' + end_date + '\nInstitution :' + institution
           header = 'To:' + receiver + '\nFrom:' + sender + '\nReply-to:' + replyto + '\nBcc:' + bcc + '\nSubject:Your Lifeportal application has been registered \n'
           email_msg = header + '\nYour Lifeportal application :\n' + project_string + '\n\nhas been registered.\n\nThe Lifeportal Resource Allocation Committee '
        
           ##For debugging
           msg = email_msg
           msg = msg.encode('utf-8')
           print "=== EMAIL application received  message ===\n", msg

           try:
                smtpObj = smtplib.SMTP('localhost')
                smtpObj.sendmail(sender, [receiver,bcc], email_msg.encode('utf-8'))
                print "Successfully sent application received email"
           except SMTPException:
                print "Error: unable to send application received email"
           
           return  (message, status)
    else :
           message = "Please select the agreement checkbox and the non-sensitive data checkbox below !"
           status = 'error'
           return (message,status)
                                          

def collect_project_info_for_report ( project_code ) :
    """
    Gets the information about the project for a report
    """

    connection = application_db_engine.connect()

    if project_code :
         ### Project displayed for modifications before final approval
              result = connection.execute("select\
                                                                 requestor,\
                                                                 requestor_job, \
                                                                 email,\
                                                                 institution,\
                                                                 country,\
                                                                 project_name,\
                                                                 cpu_hours,\
                                                                 start_date,\
                                                                 end_date \
                                                             from\
                                                                 g_lp_applications\
                                                             where\
                                                                 project_code = '%s' " % project_code)
  
              project_data = None

              if not result :
                    print "No project data to generate the report!"
                    return project_data
              
              for row in result:
                     project_data = list(row)
                     
              # convert pu hours into hours
              cpu_hours = project_data[6] 
              project_data[6] = float(cpu_hours)

              get_account_info_command = "sudo /opt/gold/bin/gbalance -h --show Name,Available | grep -w %s | uniq " % project_code
              p = subprocess.Popen(get_account_info_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
              p.wait()
       
              available = ()
              for line in p.stdout.readlines():
                     account_info = line.split()
                     available = account_info[1]
              available = float(available)
              
              project_data.insert(9,project_data[6]-available)
              project_data.insert(10,available)
              project_data.insert(11,project_code)
              
                
    connection.close()
    print "Accounting.py PROJECT data ", project_data

    return project_data

def get_all_users():
    
    all_gold_users = []
    
    get_users_command = "sudo /opt/gold/bin/glsuser --show Name"
    p = subprocess.Popen(get_users_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.wait()
    
    for line in p.stdout.readlines():
       if not re.search("@", line) :
           continue
       all_gold_users.append(line.strip())
       
    print "Accounting_project_management all gold users ",all_gold_users
    return all_gold_users
    
    
def project_dropdown_update ( email, static_options ) :
    """
    Function dynamically modifies the projects dropdown in the job parameters block for logged user.
    Called from /lib/galaxy/tools/parameters/basic.py
    """

    my_gold_projects = get_owned_GOLD_projects ( email )
    projects_in_static_options = []
    updated_static_options = []
    
    # collect all static options
    for static_option in static_options :
        
        ## The "Default Lifeportal project" is by default in the xml config file anyway
        
        flag_is_project_static_option = False
        
        if re.match('^lp\d+', static_option[0]) :
            projects_in_static_options.append(static_option[0])
            flag_is_project_static_option = True
        
        ## Only update project option
        if flag_is_project_static_option :
            updated_static_options = static_options
    
    for gold_project in my_gold_projects:
        if gold_project in projects_in_static_options :
            continue
        else :
            updated_static_options.append(( gold_project, gold_project, False)) 
    
    if len(updated_static_options) > 0 :
        static_options = updated_static_options 
    
    return static_options
         
    
    
    
                     
