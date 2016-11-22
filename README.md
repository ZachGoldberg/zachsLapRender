zachsLapRender Readme

GOPro + Harrys Laptimer + Python => consume your track videos with a smile on your face

#Installation
Requirements:
 OpenCV (for video swizzling)
 ffmpeg (for audio processing and muxing)
 python libs in requirements.txt

# Usage
--analyze  -- only output some statistics about the input data file
--input-data-file -- path to a structured data file from your GPS laptimer.  Currently only supports Harrys Laptimer GPS DB in CSV format though adding other formats should be pretty straightforward.


./run test-harrys-csv-parser   # Tests the Harrys GPS DB CSV Parser and prints some basic output


TODO:
 - Render a whole session at a time
 - Show current and last laptime in a box somewhere
 - Upload multiple laps to a YT Folder
 - Change color of g-force ball depending on Gs
 - Show filename and lap number in screen
 - Show previous laptime in bold letters
 - Store offsets in some kind of config / preference file so I dont have to do it
 everytime during testing...
 - Options for MPH vs KPH
 - Show predictive laptime throughout the lap, compared to best of the day
 - Show splits if they exist
 - Show lap number
 - Account for gap between chapters in gopro videos (~1 second) during rendering.  Gopro is fucking awful

Google Client ID: 767886164356-3sp661b4gk9o6kmdn06pqqrf708p5c3b.apps.googleusercontent.com
