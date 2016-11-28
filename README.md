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
 - Ability to compare laps between days (two different csv files)
 - Clear temp files after use
- Better filenames / youtube descriptions
 - Fix audio for 2nd half of "split" gopro videos
 - Upload multiple laps to a YT Folder
 - Show filename and lap number in screen
 - Show predictive laptime throughout the lap, compared to best of the day
  -- Can do this by comparing what % through the lap we are at this time (which we've already calculated) to the fastest lap in the dataset.  Can show a % off of optimal?
 - Show splits if they exist
 - Show lap number
 - Account for gap between chapters in gopro videos (~1 second) during rendering.  Gopro is fucking awful

Google Client ID: 767886164356-3sp661b4gk9o6kmdn06pqqrf708p5c3b.apps.googleusercontent.com
