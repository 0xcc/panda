import os
import os.path
import shutil
import time,datetime

def copyFiles(sourceDir,targetDir):
	files= os.listdir(sourceDir)
	for file in  os.listdir(sourceDir):
		sourceFile = os.path.join(sourceDir,  file)
		targetFile = os.path.join(targetDir,  file)
		print "sourceFile: ",sourceFile
		print "targetFile: ",targetFile
		if os.path.isfile(sourceFile):
			if not os.path.exists(targetDir):
				os.makedirs(targetDir)
			if not os.path.exists(targetFile) or (os.path.exists(targetFile) and (os.path.getsize(targetFile)!=os.path.getsize(sourceFile))):
				open(targetFile, "wb").write(open(sourceFile, "rb").read())
		
		#if os.path.isdir(sourceFile):
		#	copyFiles(sourceFile, targetFile)
			

copyFiles("F:/pyprojs/panda/panda","C:/Python27/Lib/site-packages/panda")
#copyFiles("F:/pyprojs/panda/panda","F:/pyprojs/panda/2")