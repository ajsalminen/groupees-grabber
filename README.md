# groupees-grabber
Groupees bundle downloader based on Frederik Lauber's work from here: https://flambda.de/2014/01/16/groupees-dot-com-grabber/

Updated to work with current Groupees site. As the site might be going away in just a few days and there's very little time to make a copy of your library this is hacked together in a hurry.

## Notes

 Downloads all MP3 and FLAC files from bundles. Might work with game bundles too. Login fails at first, you have to go to your email and accept the new login attempt to actually get in. Included CookieCon version modified to just shoddily disable Content-Length detection because that was causing errors.
 
 Program currently looks for duplicate bundles and prints out a report for those. When downloading it reveals all bundles before downloading except for those that were found to have duplicates so you can handle those manually.
