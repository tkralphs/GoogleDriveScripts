# GoogleDriveScripts

A Python class for working with Google Drive developed for use with Google Classroom. 

This class has methods to help overcome the fact that Google Classroom puts all the files for a given assignment into one giant folder and it's not easy to see which files belong to which student. 

## Sort files in a Google Drive folder into subfolders according to the e-mail id of the last modifying user.
```
DriveSort --folder-name FolderNameOnDrive --create-subfolders --move-files
```
## Change permission to the folders into subfolders according to the e-mail id of the last modifying user.
```
DriveSort --folder-name FolderNameOnDrive --change-permissions --email-domain example.edu
```

