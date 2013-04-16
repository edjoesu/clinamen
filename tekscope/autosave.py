import tekscope

def main():
    #PARAMETERS
    SCOPE_NAME = "TEKUSB1"
    IMG_DIR = "E:\\Dropbox\\tek\\img\\"
    CSV_DIR = "E:\\Dropbox\\tek\\csv\\"
        
    scope = tekscope.tekScope(visaName = SCOPE_NAME,imgDir = IMG_DIR,csvDir = CSV_DIR)
    
    stopFlag = False
    while not stopFlag:
        scope.saveNextASC()
        

if __name__ == "__main__":
    main()