import visa 
import re
import os
import sys
import numpy as np
import time
import datetime
from struct import unpack

class tekScope:
    # Class for autosaving data from Tektronix oscilloscopes 
    
    def __init__(self, visaName="", numChannels=4, tifDir = r"./", csvDir = r"./", timeout = 30, imgFormat = 'JPEG'):
        try:
            self.scope = visa.instrument(visaName)
            self.scope.timeout = timeout
            self.scope.write("HARDCOPY:FORMAT " + imgFormat)
        except visa.VisaIOError:
            raise 
        self.numchannels = numChannels
        self.tifDir = tifDir
        self.csvDir = csvDir
        self.imgFormat = imgFormat
        
    def saveNextASC(self, pollDelay = 1): 
        # save next acquisition, polling the scope every PollDelay seconds
        
        self.scope.write("ACQ:STOPA SEQ") #stop after a single sequence
        self.scope.write("ACQ:STATE RUN")
        
        stopFlag = False
        while not stopFlag: 
            if self.scope.ask("ACQ:STATE?"):
                time.sleep(pollDelay)
            else:
                stopFlag = True
                
                timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

                imgpath = self.tifDir + timestamp + '.' + self.imgFormat
                self.getImage(imgpath)
                                
                self.updateActiveChannels()                
                for channel in self.activeChannels:
                    csvpath = self.csvDir + timestamp + '_' + str(channel) + '.csv'
                    self.wfm2csvasc(csvpath, channel)    
                    
    def wfm2csvasc(self, filename, channel):
        # save waveform in CH[channel] as .csv file using ASCII transfer
        
        self.scope.write("DATA:SOURCE CH" + str(channel))
        
        xincr = float(self.scope.ask("wfmpre:xincr?"))
        xzero = float(self.scope.ask("wfmpre:xzero?"))
        
        ymult = float(self.scope.ask("wfmpre:ymult?"))
        yoff = float(self.scope.ask("wfmpre:yoff?"))
        yzero = float(self.scope.ask("wfmpre:yzero?"))
              
        cstr = self.scope.ask("CURVE?")
        cdata = np.asarray([int(x) for x in re.split(',', cstr)])      
        
        x = np.arange(len(cdata)) * xincr + xzero 
        y = ((cdata - yoff) * ymult) + yzero
                
        csvFile = open(filename, 'w')
        for i in range(0,len(cdata)):
            csvFile.write(str(x[i]) + ',' + str(y[i])+ '\n') 
        csvFile.close()   
        
    def wfm2csvbin(self, filename, channel):
        # save waveform in CH[channel] as .csv file using binary transfer. This is faster but currently doesn't handle waveforms with two-byte-wide 
        # datapoints correctly. 
        
        self.scope.write("DATA:SOURCE CH" + str(channel))
        recLen = self.scope.ask("horizontal:recordlength?")
        self.scope.write("data:start 1;stop " + recLen + ";:data:encdg rpbinary;:DESE 1;:*ESE 1");
        self.scope.write("wfmoutpre:bit_nr 8")
        
        #From the Tek manual: 
        #<Block> is the waveform data in binary format. The waveform is formatted as: #<x><yyy><data> where <x> is the number of 
        #characters in <yyy>. For example, if <yyy> = 500, then <x> = 3, where <yyy> is the number of bytes to transfer. Refer to Block
        #Arguments on page 2--13 for more information
        
        recLenNumBytes = len(recLen)
        headerLen = 1 + 1 + recLenNumBytes;

        xincr = float(self.scope.ask("wfmpre:xincr?"))
        ymult = float(self.scope.ask("wfmpre:ymult?"))
        yoff = float(self.scope.ask("wfmpre:yoff?"))
        yzero = float(self.scope.ask("wfmpre:yzero?"))
        
        Hscale = float(self.scope.ask("HOR:SCA?"))
        HDelay = float(self.scope.ask("HORizontal:DELay:POSITION?"))
        HPos = float(Hscale * 5 + float(scope.ask("HORIZONTAL:POSITION?")))/(Hscale * 10) * 100        

        self.scope.write("CURVE?")
        datac = self.scope.read_raw()  

        # Strip header
        datac = datac[headerLen:(int(recLen)-1)]
        # Convert to byte values
        datac = unpack('%sB' % len(datac),datac)
        
        x = []
        y = []
        for i in range(0,len(datac)):
            x.append((i-(len(datac)*(HPos/100)))* xincr + HDelay)
            y.append(((datac[i]-yoff) * ymult) + yzero)
        
        #save curve data in .csv format
        csvFile = open(filename, 'w')
        for i in range(0,len(datac)):
            csvFile.write(str(x[i]) + ',' + str(y[i])+ '\n') 
        csvFile.close()
    def getImage(self, filename):
        # save image of scope screen        
        self.scope.write("HARDCOPY START")
        try:        
            data = self.scope.read()
        except visa.VisaIOError:
            raise
        imgFile = open(filename, 'wb') 
        imgFile.write(data)
        imgFile.close()
    def updateActiveChannels(self):
        # update self.activeChannels with the channels that are currently active
        self.activeChannels = range(1, self.numchannels+1)
        for channel in self.activeChannels:
            if int(scope.ask("SEL:CH"+ str(channel) +"?"))==0:
                self.activeChannels.remove(channel)
                
            
        
        
        
    


