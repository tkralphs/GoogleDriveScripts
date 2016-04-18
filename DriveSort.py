#!/usr/bin/env python

__author__     = 'Xiaocheng Tang and Ted Ralphs'
__maintainer__ = 'Ted Ralphs'
__email__      = 'ted@lehigh.edu'
__version_     = '1.0.0'
__url__        = 'https://github.com/tkralphs/GoogleDriveScripts'

# Last modified 2/17/2016 Ted Ralphs
# Visit this URL to download client secret file
# https://console.developers.google.com/start/api?id=drive

import httplib2
import pprint

import sys, os
from os.path import expanduser, join
from apiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow, argparser
import argparse

class DriveSort:

    def __init__(self):

        HOME = expanduser("~")

        parser = argparse.ArgumentParser(parents=[argparser])

        parser.add_argument('--folder-name', dest='folder_name',
                            help='Name of folder on Google Drive',
                            required=True)
        parser.add_argument('--credentials-file', dest='credentials_file',
                            help='Name of file to get/store credentials',
                            default=join(HOME, '.gdrive_credentials'))
        parser.add_argument('--dry-run', dest='dry_run', action='store_true',
                            help='Do dry run')
        parser.add_argument('--user_agent', dest='user_agent',
                            help='Name of app under which to run the script')
        parser.add_argument('--client_secret', dest='client_secret',
                            help='File in which client secret is stored',
                            default=join(HOME, '.client_secret.json'))
        parser.add_argument('--email-domain', dest='email_domain',
                            help='Domain for e-mail addresses',
                            default=None)
        parser.add_argument('--create-subfolders', dest='create_subfolders',
                            action='store_true',
                            help='Create subfolders for each file owner')
        parser.add_argument('--move-files', dest='move_files',
                            action='store_true',
                            help='Move files to subfolders')
        parser.add_argument('--change-permissions', dest='change_permissions',
                            action='store_true',
                            help='Change permissions on subfolders')
        parser.add_argument('--list', dest='list_contents', action='store_true',
                            help='List all files in folder')
        self.flags = parser.parse_args()

        self.authorize()
        
    def authorize(self):

        # Check https://developers.google.com/drive/scopes for all available
        # scopes
        OAUTH_SCOPE = 'https://www.googleapis.com/auth/drive'

        # Run through the OAuth flow and retrieve credentials

        # Create a Storage object. This object holds the credentials that your
        # application needs to authorize access to the user's data. The name of
        # the credentials file is provided. If the file does not exist, it is
        # created. This object can only hold credentials for a single user, so
        # as-written, this script can only handle a single user.
        storage = Storage(self.flags.credentials_file)

        # The get() function returns the credentials for the Storage object.
        # If no credentials were found, None is returned.
        credentials = storage.get()

        # If no credentials are found or the credentials are invalid due to
        # expiration, new credentials need to be obtained from the authorization
        # server. The oauth2client.tools.run() function attempts to open an
        # authorization server page in your default web browser. The server
        # asks the user to grant your application access to the user's data.
        # If the user grants access, the run() function returns new credentials.
        # The new credentials are also stored in the supplied Storage object,
        # which updates the credentials.dat file.
        if credentials is None or credentials.invalid:
            flow = flow_from_clientsecrets(client_secret, OAUTH_SCOPE)
            flow.user_agent = self.flags.user_agent
            credentials = run_flow(flow, storage, self.flags)

        # Create an httplib2.Http object and authorize it with our credentials
        http = httplib2.Http()
        http = credentials.authorize(http)
        
        self.drive_service = build('drive', 'v3', http=http)

    #http://stackoverflow.com/questions/13558653/
    def createRemoteFolder(self, folderName, parentID = None):
        # Create a folder on Drive, returns the newly created folders ID
        body = {
            'name': folderName,
            'mimeType': "application/vnd.google-apps.folder"
        }
        if parentID:
            body['parents'] = [parentID]
        root_folder = self.drive_service.files().create(body = body).execute()
        return root_folder['id']

    def getFilesInFolder(self, folderName = None):
        if folderName == None:
            folderName = self.flags.folder_name
        q = r"mimeType = 'application/vnd.google-apps.folder'"
        pageToken = None
        while True:
            fields = "nextPageToken, "
            fields += "files(id, name)"
            results = self.drive_service.files().list(q=q, pageSize=1000,
                                                      pageToken=pageToken,
                                                      fields=fields).execute()
            folders = results['files']
            try:
                folder_id = filter(lambda x: x['name'] == folderName,
                               folders)[0]['id']
            except IndexError:
                pageToken = results.get('nextPageToken')
                if not results.get('nextPageToken'):
                    print "ERROR: Specified folder does not exist."
                    sys.exit()
            else:
                break
        # search for all files under that folder
        q = r"'{}' in parents".format(folder_id)
        fields  = ("files(id, name, mimeType, permissions, sharingUser, " +
                   "owners, parents)")
        return (folder_id, self.drive_service.files().list(q=q, pageSize=1000,
                                            fields=fields).execute()['files'])
                         
    def createSubFolders(self, folderName = None):
        if folderName == None:
            folderName = self.flags.folder_name
        folder_id, files = self.getFilesInFolder(folderName)
        print folder_id
        user_ids = []
        for f in files:
            if f['mimeType'] != 'application/vnd.google-apps.folder':
                # Google Drive seems to not change ownership sometimes...
                try:
                    user_id = f['sharingUser']['emailAddress'].split('@')[0]
                except KeyError:
                    user_id = f['owners'][0]['emailAddress'].split('@')[0]
                if user_id not in user_ids:
                    user_ids.append(user_id)
                    
        self.folderIds = {}
        for user_id in user_ids:
            print "Creating folder", user_id
            # Check to see if it's a dry run or folder is already there
            if (self.flags.dry_run == False or
                filter(lambda x: x['name'] == user_id, files) != []):
                self.folderIds['user_id'] = self.createRemoteFolder(user_id,
                                                                    folder_id)

    def moveFiles(self, folderName = None):
        if folderName == None:
            folderName = self.flags.folder_name
        folder_id, files = self.getFilesInFolder(folderName)
        for f in files:
            if f['mimeType'] != 'application/vnd.google-apps.folder':
                # Google Drive seems to not change ownership sometimes...
                try:
                    user_id = f['sharingUser']['emailAddress'].split('@')[0]
                except KeyError:
                    user_id = f['owners'][0]['emailAddress'].split('@')[0]
                print "Moving", f['name'], 'to', user_id
                parents = f['parents']
                if not self.flags.dry_run:
                    try:
                        new_parent = filter(lambda x: x['name'] ==
                                            user_id, files)[0]['id']
                    except KeyError:
                        print "Folder not found. Maybe",
                        print "run creatFolders() again?"
                    self.drive_service.files().update(fileId=f['id'],
                                                      removeParents=parents[0],
                                                      addParents=new_parent
                                                      ).execute()

    def changePermissions(self, domain = None, folderName = None):
        if folderName == None:
            folderName = self.flags.folder_name
        if domain == None:
            if self.flags.email_domain:
                domain = self.flags.email_domain
            else:
                print "ERROR: Must specify e-mail domain to change permissions."
                sys.exit()
        folder_id, files = self.getFilesInFolder(folderName)
        for f in files:
            if f['mimeType'] == 'application/vnd.google-apps.folder':
                print 'Sharing', f['name'], 'with', '%s@%s'% (f['name'],
                                                               domain)
                emailAddress = f['name']+"@"+domain
                permissionId = None
                for perms in f['permissions']:
                    if perms['emailAddress'] == emailAddress:
                        permissionId = perms['id']
                if not self.flags.dry_run:
                    if permissionId:
                        new_perm = {
                            'role' : 'commenter'
                        }
                        try:
                            self.drive_service.permissions().update(
                                  fileId=f['id'],
                                  permissionId=permissionId,
                                  body = new_perm).execute()
                        except:
                            print "Could not change permissions on", f['name']
                    else:
                        new_perm = {
                            'emailAddress' : emailAddress,
                            'type' : 'user',
                            'role' : 'commenter'
                        }
                        self.drive_service.permissions().create(fileId=f['id'],
                                  permissionId=permissionId,
                                  body = new_perm).execute()


if __name__ == '__main__':

    # Parse arguments and authorize connection
    drive = DriveSort()
    
    # Print names of all files in folder
    if drive.flags.list_contents:
        print "Folder contents:"
        for f in drive.getFilesInFolder()[1]:
            print f['name']
        
    #Create subfolder with same name as e-mail user ID of last modifying user
    if drive.flags.create_subfolders:
        drive.createSubFolders()

    # Move files into folders
    if drive.flags.move_files:
        drive.moveFiles()

    # Grant permission to original owner
    if drive.flags.change_permissions:
        drive.changePermissions()
