<<<<<<< HEAD
import fitz
import ETC
import re
import zlib


#Extract Objects 
def extraction(pdf_f):
    stream = re.compile(rb'(\d+)\s+(\d+)\s+obj([\s\S]*?)', re.S) #format 'num-num obj'
    #Checks for the existence of the object.
    if not(stream.search(pdf_f)) : 
        print("[File Error] Object not found.")
        return []
    stream = re.compile(rb'(\d+)\s+(\d+)\s+obj([\s\S]*?)endobj', re.S) #format 'num-num obj ~ endobj'
    s = stream.findall(pdf_f) #s[1] -> [object #, generation #, object data]
    for i in range(0, len(s)):
        s[i] = list(s[i])
    return s

#Check the Save Method using the object's content and order.  -> Pending modification.
def SaveMethoad(objList, pdf):
    #Object number
    numstr = b""
    for i in range(0,len(objList)):
        numstr = numstr+objList[i][0]

    if numstr == b'314': #MAC
        pdf['SaveMethod'] = "MAC"
    elif b'1013' in numstr: #HanPDF
        if b"<< /Type /Page" in objList[0][2] and b"<</Type/Page/" in objList[1][2]:
            pdf['SaveMethod'] = "HanPDF"
    elif numstr == b'145': #Print to ALPDF
        if b"<</Type/Catalog/" in objList[0][2] and b"<</Type/Page/" in objList[1][2]:
            pdf['SaveMethod'] = "Print to ALPDF"
    elif numstr == b'134': #Save as AlPDF
        if b"<</Type/Catalog/" in objList[0][2] and b"<</Type/Page/" in objList[1][2]:
            pdf['SaveMethod'] = "AlPDF"
    elif numstr == b'458': #Microsoft Print to PDF
        if b"(Identity)" in objList[0][2] and b"(Adobe)" in objList[1][2]:
            pdf['SaveMethod'] = "Microsoft Print to PDF"
    elif numstr == b'123': #Microsoft Save as
        if b"<</Type/Catalog/" in objList[0][2] and b"<</Type/Pages" in objList[1][2]:
            pdf['SaveMethod'] = "Microsoft Save as"
    else: #Adobe of Unknown
        if pdf['Version'] =='1.6' and b"<</Linearized" in objList[0][2] and b"<</DecodeParms" in objList[1][2]:
            pdf['SaveMethod'] = "Adobe"
        elif pdf['Version'] =='1.3' and b"<</Metadata" in objList[0][2] and b"<</Length" in objList[1][2]:
            pdf['SaveMethod'] = "Adobe"
        else:
            pdf['SaveMethod'] = "Unknown"


#Verifies if the object is corrupted.
def IsCorrupted(objList):   
    num=0   
    IsDamaged = False 
    for obj in objList: 
        if b'%%EOF' in obj[2]:
            obj[2] = obj[2].split(b'%%EOF')[0]
        
        ObjNumstream = re.compile(rb'(\d+)\s+(\d+)\s+obj([\s\S]*?)', re.S) #format 'num-num obj'
        #Considered corrupt if an object has two or more headers.
        if len(re.findall(ObjNumstream, obj[2])) == 1:
            IsDamaged = True 
            NumList = re.search(ObjNumstream, obj[2])
            objData = obj[2][NumList.start():]
            #Split based on Object start and append data as a new element
            SearchResult = re.search(rb'(\d+)\s+(\d+)\s+obj([\s\S]*?)endstream', objData)
            if SearchResult == None:
                SearchResult = re.search(rb'(\d+)\s+(\d+)\s+obj([\s\S]*?)', objData)
                content = SearchResult[2]
                objList.append([SearchResult[1], SearchResult[2], content])
            else:
                content = SearchResult[2]+b'endstream' #Add for decompress
                objList.append([objData[1], objData[2], content])
            objList[num][2] = obj[2][:NumList.start()]
        num+=1
    return IsDamaged, objList

#decompress
def decompress(objList):
    decompressObj = []
    DamagedObject = []
    for i in objList:
        if b'stream' in i[2]:
            stream = i[2].split(b'stream')[1]
            if b'/FlateDecode' in i[2]:
                try:
                    stream = re.compile(rb'.*?FlateDecode.*?stream(.*?)endstream', re.S) #intact object
                    s = stream.findall(i[2])[0] #s[0] -> Content of stream
                    s = s.strip(b'\r\n')

                    decompressObj.append([i[0], i[1], zlib.decompress(s)])
                except:
                    try:
                        #Focuses on a single corrupted object
                        stream = i[2].split(b'stream')[1] 
                        z = zlib.decompressobj()

                        retrieved = b''
                        while True:
                            buf = z.unconsumed_tail
                            if buf == b"":
                                buf = stream.strip(b'\r\n')
                            got = z.decompress(buf)
                            if got == b"" or got == z.decompress(buf):
                                break
                            retrieved += got
                        decompressObj.append([i[0], i[1], retrieved])
                    except:
                        decompressObj.append([i[0], i[1], i[2]])
            elif not(b'endstream' in i[2]):
                if re.search(rb'\/Length\s([\d]+)', i[2]) != None:
                    obj_length = int(re.search(rb'\/Length\s([\d]+)', i[2]).group().split(b' ')[1])
                    if len(stream) > obj_length:
                        stream = stream[:int(obj_length)]
                    try:
                        retrieved = b''
                        while True:
                            buf = z.unconsumed_tail
                            if buf == b"":
                                buf = stream.strip(b'\r\n')
                            got = z.decompress(buf)
                            if got == b"" or got == z.decompress(buf):
                                break
                            retrieved += got
                        decompressObj.append([i[0], i[1], retrieved])
                        if b'<</MCID ' in retrieved:
                            DamagedObject.append('Content')
                    except:
                        decompressObj.append([i[0], i[1], i[2]])
                elif ETC.detectZeroStreak(stream):
                        stream = stream[:re.search(b'[\\x00]{48,}', stream).start()]
                        try:
                            retrieved = b''
                            while True:
                                buf = z.unconsumed_tail
                                if buf == b"":
                                    buf = stream.strip(b'\r\n')
                                got = z.decompress(buf)
                                if got == b"" or got == z.decompress(buf):
                                    break
                                retrieved += got
                            decompressObj.append([i, b'0', retrieved])
                            if b'<</MCID ' in retrieved:
                                DamagedObject.append('Content')
                        except:
                            print("Keep decompressing...")
                            while True:
                                retrieved = b''
                                got = b''
                                buf = z.unconsumed_tail
                                if buf == b"":
                                    buf = stream.strip(b'\r\n')
                                try:
                                    got = z.decompress(buf)
                                    if got == b"" or got == z.decompress(buf):
                                        break
                                except:
                                    #Reduce by 16 bytes at a time and attempt decompression.
                                    buf = buf[:len(buf)-16]
                                if len(buf)<16:
                                    break
                            retrieved += got
                            decompressObj.append([i[0], i[1], retrieved])
                            if b'<</MCID ' in retrieved:
                                DamagedObject.append('Content')
                            print("End decompressing")     
                else: #If length is missing, remove a fixed size before decompressing.
                        print("Keep decompressing...")
                        while True:
                            retrieved = b''
                            got = b''
                            buf = z.unconsumed_tail
                            if buf == b"":
                                buf = stream.strip(b'\r\n')
                            try:
                                got = z.decompress(buf)
                                if got == b"" or got == z.decompress(buf):
                                    break
                            except:
                                #Reduce by 16 bytes at a time and attempt decompression.
                                buf = buf[:len(buf)-16] 
                            if len(buf)<16:
                                break
                        retrieved += got
                        decompressObj.append([i[0], i[1], retrieved])
                        if b'<</MCID ' in retrieved:
                            DamagedObject.append('Content')
                        print("End decompressing")    
            else:
                decompressObj.append([i[0], i[1], i[2]])
        else:
            decompressObj.append([i[0], i[1], i[2]])
    return DamagedObject, decompressObj

#Verify if multiple object data are compressed into one object and split them.
def twoMore_Check(decompressObj):
    decompressObj_checked = []
    for obj in decompressObj:
        stream = re.compile(rb"[\d+\s\d+]+\s<<", re.S) #[\d)+\s(\d)+]+[<<]
        data = obj[2].strip(b'\r\n')
        s = stream.match(data)
        objlist = []

        if s != None: #multiple object data detected -> split
            stream2 = re.compile(rb"(\d+)\s(\d+)", re.S)
            text = data[s.end()-2:]
            s2 = stream2.findall(s.group())
            for i in range(0, len(s2)):
                li2 =[]
                li2.append(s2[i][0])
                li2.append(b'0')
                if i == len(s2)-1:
                    li2.append(text[int(s2[i][1]):])
                else:
                    li2.append(text[int(s2[i][1]):int(s2[i+1][1])])
                objlist.append(li2)
            for h in objlist:
                decompressObj_checked.append(h)
        else:
            decompressObj_checked.append(obj)
            continue
    return decompressObj_checked 

#image extraction
def Image_extract(Pdf_Path, objList, PdfOutputPath):    
    try:
        # open the PDF File
        pdf_document = fitz.open(Pdf_Path)
    except Exception as e:
        print(f"[File Error] PDF file opening error : {e}")
        return 

    # check all objects
    for i in objList:
        obj_str = i[2]
        obj_num = int(i[0])
        
        # Check "/Subtype /Image" or "/Subtype/Image"
        if b'/Subtype /Image' in obj_str or b'/Subtype/Image' in obj_str:
            try:
                # Extract Image
                base_image = pdf_document.extract_image(obj_num)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]  # File Extension

                # Set Image Filename
                image_filename = f"{PdfOutputPath}\\Media\\image_{obj_num}.{image_ext}"
                ETC.makeDir(PdfOutputPath+"\\Media")
                with open(image_filename, "wb") as file:
                    file.write(image_bytes)
                
                print(f"Media : {image_filename}")

            except Exception as e:
                print(f"[Extraction Error] Image extraction error: {e}")

#[Main]
def start(objList, pdf, PDF_path): 
    #Check the Save Method using the object's content and order.
    SaveMethoad(objList, pdf)
    #Verifies if the object is corrupted.
    pdf['IsDamaged'], objList = IsCorrupted(objList)
    damageObj = []
    damageObj, decompressObj = decompress(objList)
    for i in damageObj :
        pdf['DamagedObj'].append(damageObj)
    decompressObj = twoMore_Check(decompressObj)
    #decompress
    Image_extract(PDF_path, objList, pdf["Result_path"])
    return decompressObj



=======
import fitz
import ETC
import re
import zlib
import os
import io
from PIL import Image

#Extract Objects 
def extraction(pdf_f, pdf):
    stream = re.compile(rb'(\d+)\s+(\d+)\s+obj([\s\S]*?)', re.S) #format 'num-num obj'
    #Checks for the existence of the object.
    if not(stream.search(pdf_f)) : 
        print("[File Error] Object not found.")
        return []
    stream = re.compile(rb'(\d+)\s+(\d+)\s+obj([\s\S]*?)endobj', re.S) #format 'num-num obj ~ endobj'
    s = stream.findall(pdf_f) #s[1] -> [object #, generation #, object data]
    for i in range(0, len(s)):
        s[i] = list(s[i])
    match = re.search(rb'%PDF-(\d+\.\d+)', pdf_f)
    if match:
        pdf['Version'] = match.group(1).decode()
    return s

#Check the Save Method using the object's content and order.  -> Pending modification.
def SaveMethoad(objList, pdf):
    #Object number
    numstr = b""
    for i in range(0,len(objList)):
        numstr = numstr+objList[i][0]

    if numstr.startswith(b'314'): #MAC
        pdf['SaveMethod'] = "MAC"
    elif numstr == b'145': #Print to ALPDF
        if b"<</Type/Catalog/" in objList[0][2] and b"<</Type/Page/" in objList[1][2]:
            pdf['SaveMethod'] = "Print to ALPDF"
    elif numstr.startswith(b'1013'): #HanPDF 버전 1.4
        if b"<< /Type /Page" in objList[0][2] and b"<</Type/Page/" in objList[1][2]:
            pdf['SaveMethod'] = "HanPDF"
    elif numstr.startswith(b'123'): 
        if b"<</Type/Catalog/" in objList[0][2] and b"<</Type/Pages" in objList[1][2]:
            pdf['SaveMethod'] = "Microsoft Save as"
        elif b"/Type/Catalog/" in objList[0][2] and b"/Type/Pages>>" in objList[1][2]: #버전1.6 - 프랑스어
            pdf['SaveMethod'] = "HanPDF"
        elif b"/Type/Pages/>>" in objList[0][2] or b"<</Filter/FlateDecode" in objList[1][2]: #버전1.7 - 한국어, 영어
            pdf['SaveMethod'] = "HanPDF"
    elif numstr.startswith(b'1') and b"<< /AcroForm" in objList[0][2]: #Save as AlPDF
        pdf['SaveMethod'] = "AlPDF"
    elif numstr.startswith(b'458'): #Microsoft Print to PDF
        if b"(Identity)" in objList[0][2] and b"(Adobe)" in objList[1][2]:
            pdf['SaveMethod'] = "Microsoft Print to PDF"
    else: #Adobe of Unknown
        if pdf['Version'] =='1.6' and b"<</Linearized" in objList[0][2] and b"<</DecodeParms" in objList[1][2]:
            pdf['SaveMethod'] = "Adobe"
        elif pdf['Version'] =='1.3' and b"<</Metadata" in objList[0][2] and b"<</Length" in objList[1][2]:
            pdf['SaveMethod'] = "Adobe"
        else:
            pdf['SaveMethod'] = "Unknown"


#Verifies if the object is corrupted.
def IsCorrupted(objList):   
    num=0   
    IsDamaged = False 
    for obj in objList: 
        if b'%%EOF' in obj[2]:
            obj[2] = obj[2].split(b'%%EOF')[0]
        
        ObjNumstream = re.compile(rb'(\d+)\s+(\d+)\s+obj([\s\S]*?)', re.S) #format 'num-num obj'
        #Considered corrupt if an object has two or more headers.
        if len(re.findall(ObjNumstream, obj[2])) == 1:
            IsDamaged = True 
            NumList = re.search(ObjNumstream, obj[2])
            objData = obj[2][NumList.start():]
            #Split based on Object start and append data as a new element
            SearchResult = re.search(rb'(\d+)\s+(\d+)\s+obj([\s\S]*?)endstream', objData)
            if SearchResult == None:
                SearchResult = re.search(rb'(\d+)\s+(\d+)\s+obj([\s\S]*?)', objData)
                content = SearchResult[2]
                objList.append([SearchResult[1], SearchResult[2], content])
            else:
                content = SearchResult[2]+b'endstream' #Add for decompress
                objList.append([objData[1], objData[2], content])
            objList[num][2] = obj[2][:NumList.start()]
        num+=1
    return IsDamaged, objList

#decompress
def decompress(objList):
    decompressObj = []
    DamagedObject = []
    for i in objList:
        if b'stream' in i[2]:
            stream = i[2].split(b'stream')[1]
            if b'/FlateDecode' in i[2]:
                try:
                    stream = re.compile(rb'.*?FlateDecode.*?stream(.*?)endstream', re.S) #intact object
                    s = stream.findall(i[2])[0] #s[0] -> Content of stream
                    s = s.strip(b'\r\n')

                    decompressObj.append([i[0], i[1], zlib.decompress(s)])
                except:
                    try:
                        #Focuses on a single corrupted object
                        stream = i[2].split(b'stream')[1] 
                        z = zlib.decompressobj()

                        retrieved = b''
                        while True:
                            buf = z.unconsumed_tail
                            if buf == b"":
                                buf = stream.strip(b'\r\n')
                            got = z.decompress(buf)
                            if got == b"" or got == z.decompress(buf):
                                break
                            retrieved += got
                        decompressObj.append([i[0], i[1], retrieved])
                    except:
                        decompressObj.append([i[0], i[1], i[2]])
            elif not(b'endstream' in i[2]):
                if re.search(rb'\/Length\s([\d]+)', i[2]) != None:
                    obj_length = int(re.search(rb'\/Length\s([\d]+)', i[2]).group().split(b' ')[1])
                    if len(stream) > obj_length:
                        stream = stream[:int(obj_length)]
                    try:
                        retrieved = b''
                        while True:
                            buf = z.unconsumed_tail
                            if buf == b"":
                                buf = stream.strip(b'\r\n')
                            got = z.decompress(buf)
                            if got == b"" or got == z.decompress(buf):
                                break
                            retrieved += got
                        decompressObj.append([i[0], i[1], retrieved])
                        if b'<</MCID ' in retrieved:
                            DamagedObject.append('Content')
                    except:
                        decompressObj.append([i[0], i[1], i[2]])
                elif ETC.detectZeroStreak(stream):
                        stream = stream[:re.search(b'[\\x00]{48,}', stream).start()]
                        try:
                            retrieved = b''
                            while True:
                                buf = z.unconsumed_tail
                                if buf == b"":
                                    buf = stream.strip(b'\r\n')
                                got = z.decompress(buf)
                                if got == b"" or got == z.decompress(buf):
                                    break
                                retrieved += got
                            decompressObj.append([i, b'0', retrieved])
                            if b'<</MCID ' in retrieved:
                                DamagedObject.append('Content')
                        except:
                            print("Keep decompressing...")
                            while True:
                                retrieved = b''
                                got = b''
                                buf = z.unconsumed_tail
                                if buf == b"":
                                    buf = stream.strip(b'\r\n')
                                try:
                                    got = z.decompress(buf)
                                    if got == b"" or got == z.decompress(buf):
                                        break
                                except:
                                    #Reduce by 16 bytes at a time and attempt decompression.
                                    buf = buf[:len(buf)-16]
                                if len(buf)<16:
                                    break
                            retrieved += got
                            decompressObj.append([i[0], i[1], retrieved])
                            if b'<</MCID ' in retrieved:
                                DamagedObject.append('Content')
                            print("End decompressing")     
                else: #If length is missing, remove a fixed size before decompressing.
                        print("Keep decompressing...")
                        while True:
                            retrieved = b''
                            got = b''
                            buf = z.unconsumed_tail
                            if buf == b"":
                                buf = stream.strip(b'\r\n')
                            try:
                                got = z.decompress(buf)
                                if got == b"" or got == z.decompress(buf):
                                    break
                            except:
                                #Reduce by 16 bytes at a time and attempt decompression.
                                buf = buf[:len(buf)-16] 
                            if len(buf)<16:
                                break
                        retrieved += got
                        decompressObj.append([i[0], i[1], retrieved])
                        if b'<</MCID ' in retrieved:
                            DamagedObject.append('Content')
                        print("End decompressing")    
            else:
                decompressObj.append([i[0], i[1], i[2]])
        else:
            decompressObj.append([i[0], i[1], i[2]])
    return DamagedObject, decompressObj

#Verify if multiple object data are compressed into one object and split them.
def twoMore_Check(decompressObj):
    decompressObj_checked = []

    for obj in decompressObj:
        stream1 = re.compile(rb"[\d+\s\d+]+\s<<", re.S)
        stream2 = re.compile(rb"(?:\d+\s+\d+\s+){5,}[\[\<]", re.S)
        data = obj[2].strip(b'\r\n')
        s = stream1.match(data) or stream2.match(data)
        objlist = []

        if s != None: #multiple object data detected -> split
            stream2 = re.compile(rb"(\d+)\s(\d+)", re.S)
            text = data[s.end()-2:]
            s2 = stream2.findall(s.group())
            for i in range(0, len(s2)):
                li2 =[]
                li2.append(s2[i][0])
                li2.append(b'0')
                if i == len(s2)-1:
                    li2.append(text[int(s2[i][1]):])
                else:
                    li2.append(text[int(s2[i][1]):int(s2[i+1][1])])
                objlist.append(li2)
            for h in objlist:
                decompressObj_checked.append(h)
        else:
            decompressObj_checked.append(obj)
            continue
    return decompressObj_checked 

def extract_imagename(objList):
    imagename = {}
    name_counter = {}  # 중복 이름 카운트

    for i in objList:
        obj_str = i[2]
        if b"/XObject" in obj_str:
            # XObject 블록 추출
            match = re.search(rb'/XObject\s*<<([^>]*)>>', obj_str, re.DOTALL)
            if match:
                xobject_block = match.group(1)

                # /ImageN obj_num 0 R 추출
                image_refs = re.findall(rb'/(\S+)\s+(\d+)\s+0\s+R', xobject_block)
                for name, obj_num in image_refs:
                    name = name.decode("utf-8", errors="ignore")
                    obj_num = obj_num.decode()

                    # 이름이 이미 존재하면 _1, _2 붙이기
                    count = name_counter.get(name, 0) + 1
                    name_counter[name] = count

                    if count == 1:
                        name = name
                    else:
                        name = f"{name}_{count}"

                    imagename[obj_num] = name
    
    #print(imagename)
    return imagename

#image extraction
def Image_extract(Pdf_Path, objList, PdfOutputPath, imagename):    
    try:
        pdf_document = fitz.open(Pdf_Path)
    except Exception as e:
        print(f"PDF 파일을 여는 중 에러 발생: {e}")
        return  # 파일 열기에 실패하면 함수 종료

    # Step1 : base image → smask_num 매핑 수집 (png의 경우 올바르게 하나만 추출하기 위한 전처리 과정정)
    smask_map = {}
    for i in objList:
        obj_str = i[2]
        obj_num = int(i[0])

        if b'/Subtype /Image' in obj_str or b'/Subtype/Image' in obj_str:
            match = re.search(rb'/SMask\s+(\d+)\s+\d+\s+R', obj_str)
            if match:
                smask_num = int(match.group(1))
                smask_map[obj_num] = smask_num  # base image → smask num
            ETC.makeDir(PdfOutputPath+"\\multimedia")

    # Step2 : 이미지 추출
    for i in objList:
        obj_str = i[2] 
        obj_num = int(i[0])

        if obj_num in smask_map.values(): # SMask 오브젝트는 skip
            continue
        
        if b'/Subtype /Image' in obj_str or b'/Subtype/Image' in obj_str:
            try:
                base_image = pdf_document.extract_image(obj_num)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]  # 확장자 찾기

                # SMask 처리
                if b'/SMask' in obj_str or b'/Mask' in obj_str:
                    smask_num = smask_map[obj_num]
                    try:
                        smask_image_info = pdf_document.extract_image(smask_num)
                        smask_bytes = smask_image_info["image"]
                        smask_pil = Image.open(io.BytesIO(smask_bytes)).convert("L")
                        base_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")

                        # 둘 중 더 큰 사이즈 선택
                        if base_pil.size >= smask_pil.size:
                            size = base_pil.size
                        else:
                            size = smask_pil.size

                        # 리사이징
                        base_resized = base_pil.resize(size)
                        smask_resized = smask_pil.resize(size)

                        # 알파 채널 적용
                        image_rgba = base_resized.convert("RGBA")
                        image_rgba.putalpha(smask_resized)

                        #Imagename 사용. 없으면 오브젝트 번호 사용.
                        name = imagename.get(str(obj_num), f"image_{obj_num}") if imagename else f"image_{obj_num}"
                        image_filename = os.path.join(PdfOutputPath, "multimedia", f"{name}.{image_ext}")
                        image_rgba.save(image_filename)
                        print(f"multimedia : {image_filename}")
                    
                    except Exception as e:
                        print(f"SMask 오브젝트 {smask_num} 처리 중 에러 발생: {e}")

                else:
                    # 일반 이미지 저장
                    name = imagename.get(str(obj_num), f"image_{obj_num}") if imagename else f"image_{obj_num}"
                    image_filename = os.path.join(PdfOutputPath, "multimedia", f"{name}.{image_ext}")
                    with open(image_filename, "wb") as file:
                        file.write(image_bytes)
                    print(f"multimedia : {image_filename}")

            except Exception as e:
                print(f"이미지 추출 중 에러 발생 (오브젝트 {obj_num}): {e}")
                try: #JPEG 이미지 강제 추출 시도
                    image_data = None

                    if b'JFIF' in obj_str:
                        parts = obj_str.split(b'JFIF', 1)
                        image_data =  b'\xff\xd8\xff\xe0\x00\x10' + parts[1]
                    
                        # 이미지 데이터를 파일로 저장
                        image_filename = os.path.join(PdfOutputPath, "multimedia", f"extract_image{i}.jpeg")
                        with open(image_filename, "wb") as file:
                            file.write(image_data)
                    
                except Exception as e:
                    print(f"이미지 추출 실패")

                return 

#[Main]
def start(objList, pdf, PDF_path): 
    #Check the Save Method using the object's content and order.
    SaveMethoad(objList, pdf)
    #Verifies if the object is corrupted.
    pdf['IsDamaged'], objList = IsCorrupted(objList)
    damageObj = []
    damageObj, decompressObj = decompress(objList)
    for i in damageObj :
        pdf['DamagedObj'].append(damageObj)
    decompressObj = twoMore_Check(decompressObj)
    #decompress
    imagename = extract_imagename(objList)
    Image_extract(PDF_path, objList, pdf["Result_path"], imagename)
    return decompressObj



>>>>>>> 77c3de1 (Code Upload)
