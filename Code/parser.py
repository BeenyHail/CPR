<<<<<<< HEAD
import pandas as pd
import os
import xml.etree.ElementTree as ET
import re


#Metadata Parser -> Pending modification.
def parse_Metadata(decompressObj_checked, pdf, cnt):
    try:
        if pdf['Metadata'] != None:
            Metadata = {}
            hex_data = decompressObj_checked[pdf['Metadata']][2].decode('utf-8').strip()
            hex_data = hex_data.replace('\n','')
            hex_data = hex_data.replace('\r','')

            hex_data = hex_data.split('stream')[1]
            hex_data = '<root>'+hex_data+'</root>'
            
            
            # XML parsing
            root = ET.fromstring(hex_data)

            #Explore XML elements and output tags with text
            for element in root.iter():
                if element.text is not None:
                    # ModifyDate, CreateDate, DocumentID, InstanceID
                    if element.tag.endswith("ModifyDate") or element.tag.endswith("CreateDate") or element.tag.endswith("DocumentID") or element.tag.endswith("InstanceID") or element.tag.endswith("Producer") or element.tag.endswith("creator"):
                        key = element.tag.split("}")[1] if '}' in element.tag else element.tag
                        Metadata[key] = element.text
                elif element.tag.endswith("creator"):
                    for i in element.iter():
                        if i.tag.endswith("li"):
                            Metadata["Creator"] = i.text
            # Set 'Not found' if the keys ModifyDate, CreateDate, DocumentID, or InstanceID are missing
            for key in ["ModifyDate", "CreateDate", "DocumentID", "InstanceID", "Creator", "Producer"]:
                if key not in Metadata:
                    Metadata[key] = 'Not found'
                else:
                    with open(pdf['Result_path']+"\\PDF_"+str(cnt)+"_Metadata.txt", "a", encoding = 'utf-8') as f:
                        f.write(key+" : ", Metadata[key]+"\n")
        else:
            return
    except Exception as e:
        return

#Verify essential objects
def CheckEssential(decompressObj, pdf): # catalog, page, pages, font, CMap, content 확인
    cnt = 0
    for cnt, i in enumerate(decompressObj):
        if b'/Catalog' in i[2] and b'/Pages' in i[2]: 
            pdf['Catalog'] = cnt
        elif b'/Pages' in i[2] and b'/Kids' in i[2]:
            pdf['Pages'] = cnt
        elif b'/Page' in i[2] and b'/Content' in i[2]: 
            pdf['Page'].append(cnt)
        elif b'/CIDInit' in i[2]: 
            pdf['CMap'].append(cnt)
        elif (b'<</MCID ' in i[2] or b'/MC' in i[2]) or (b' Tf' in i[2] and b' BT' in i[2]) or b'\nQ\nq' in i[2]: #content 여러 개일 수 있음 -> 이를 어떻게 처리할 것인가?
            pdf['Content'].append(cnt) 
        elif b'XML' in i[2] and b'Metadata' in i[2]:
            pdf['Metadata'] = cnt
        if b'/Font' in i[2] or b'/ToUnicode' in i[2] or b'/DescendantFonts' in i[2]: #n개
            pdf['Font'].append(cnt)
    
    #Verification Stage - Collect and Compare Relevant Information
    objlist  = {}
    for ObjName in ['Catalog', 'Pages', 'Page', 'Font', 'CMap','Content']: 
        if pdf[ObjName] != None:
            if ObjName == 'Catalog': #Catalog -> Pages, Metadata 
                objData = decompressObj[pdf[ObjName]][2]
                stream = re.compile(rb'\/([a-zA-Z]+)\s(\d+)\s+(\d+)\sR', re.S)
                repl = stream.findall(objData)
                for j in repl:
                    objlist[j[0]] = j[1] 
            elif ObjName == 'Pages': #Pages -> Count, Kids
                objData = decompressObj[pdf[ObjName]][2]
                CntStream = re.compile(rb'\/Count\s(\d+)', re.S) #count - Check the number of pages.
                KidsStream = re.compile(rb'\/Kids[\s]*\[[A-Z0-9\s]*\]',re.S)#\/Kids\[(.*)\]', re.S)#kids
                objlist['Pages count'] = int(CntStream.findall(objData)[0], 16) #the number of page 

                objlist['Kids'] = []
                kids = KidsStream.findall(objData)[0]
                KidsStream2 = re.compile(rb'(\d+)\s(\d+)\sR', re.S)
                kids = KidsStream2.findall(kids)#page object number
                for j in kids:
                    objlist['Kids'].append(j[0])
            elif ObjName == 'Page': #Page -> Parent, Content
                if len(pdf[ObjName]) != 0:
                    page_cnt = 0
                    cnt = 1
                    for j in pdf[ObjName]:
                        objData = decompressObj[j][2]
                        stream = re.compile(rb'\/([a-zA-Z]+)\s(\d+)\s+(\d+)\sR', re.S)
                        stream2 = re.compile(rb'/Contents\s\[([a-zA-Z0-9\s]+)\]', re.S)
                        content_d = stream2.findall(objData)
                        repl = stream.findall(objData)
                        for k in repl:
                            if k[0] == b'Parent':
                                page_cnt+=1
                            key = ('Page'+str(cnt)+'_').encode()+k[0] 
                            objlist[key] = k[1]
                        for k in content_d:
                            con_d = k.split(b'R') 
                            if len(con_d) == 2: # 4 0 R -> " 4 0 ", ""
                                if len(pdf['Content']) == 0:
                                    num = con_d[0][1:-1].split(b' ')[0]
                                    for cnt, i in enumerate(decompressObj):
                                        if i[0] == num:
                                            pdf['Content'].append(cnt)
                                            break
                        cnt+=1
                    if page_cnt != 0:
                        for k in objlist.keys():
                            if "Parent" in str(k): #Detect potential corruption by checking against the Pages attribute.
                                if b'Pages' in objlist.keys():
                                    if objlist[k] != objlist[b'Pages']:
                                        pdf['IsDamaged'] = True
                                        pdf['DamagedObj'].append('Page')
                                continue
                    else: #Treat as corrupted if the attribute is absent.
                        pdf['IsDamaged'] = True
                        pdf['DamagedObj'].append('Page')
                else: #Need Modification
                    pdf['IsDamaged'] = True
                    pdf['DamagedObj'].append('Page')
            elif ObjName == 'Content':
                if len(pdf[ObjName]) == 0: #content missing
                    pdf['IsDamaged'] = True
                    pdf['DamagedObj'].append('Content')
                    pdf['IsRecoverable'] = False #Irrecoverable -> Termination
                else:
                    cnt_content = 0
                    for k in objlist.keys(): 
                        if "_Content" in str(k):
                            cnt_content += 1
                    if len(pdf[ObjName]) != cnt_content: #the number of content  != the number of  cnt_content 
                        pdf['IsDamaged'] = True
                        if len(pdf[ObjName]) > cnt_content: 
                            pdf['DamagedObj'].append('Page')
                        else:
                            pdf['DamagedObj'].append('Content')
            elif ObjName == "Font":
                if len(pdf[ObjName]) == 0: 
                    pdf['IsDamaged'] = True
                    pdf['DamagedObj'].append('ToUnicode')
                    pdf['DamagedObj'].append('DescendantFonts')
                    continue
                objlist[b'ToUnicode'] = []
                objlist[b'DescendantFonts'] = []
                des_idx = 0
                for j in pdf[ObjName]: 
                    objData = decompressObj[j][2]
                    stream = re.compile(rb'\/([a-zA-Z]+)\s(\d+)\s+(\d+)\sR', re.S)
                    repl = stream.findall(objData)
                    cnt = 0
                    for j in repl:
                        if j[0] == b'ToUnicode':
                            objlist[b'ToUnicode'].append(j[1])
                        elif j[0] == b'DescendantFonts':
                            objlist[b'DescendantFonts'].append(j[1])
                            des_idx+=1
                        else:
                            continue
                if len(objlist[b'ToUnicode']) != len(pdf['CMap']) or len(objlist[b'ToUnicode']) == 0:
                    pdf['IsDamaged'] = True
                    if len(objlist[b'ToUnicode']) == 0:
                        pdf['DamagedObj'].append('ToUnicode')
                    elif len(objlist[b'ToUnicode']) > len(pdf['CMap']):
                        pdf['DamagedObj'].append('CMap')
                    else:
                        pdf['DamagedObj'].append('ToUnicode')
                if des_idx == 0 or des_idx < len(objlist[b'ToUnicode']):
                    pdf['DamagedObj'].append('DescendantFonts')
            else: #CMap
                if len(pdf[ObjName]) == 0:
                    pdf['IsDamaged'] = True
                    pdf['DamagedObj'].append('CMap')
                else: 
                    if 'ToUnicode' in objlist.keys():
                        if len(objlist[b'ToUnicode']) != 0:
                            errflag = False
                            if len(pdf[ObjName]) != len(objlist[b'ToUnicode']):
                                for k in pdf[ObjName]:
                                    objnum = decompressObj[k][0]
                                    for j in objlist[b'ToUnicode']:
                                        if j == objnum:
                                            errflag==False
                                            break
                                        else:
                                            errflag = True
                                    if errflag :
                                        pdf['IsDamaged'] = True
                                        break
                                if len(pdf[ObjName]) > len(objlist[b'ToUnicode']):
                                    pdf['DamagedObj'].append('ToUnicode')
                                else:
                                    pdf['DamagedObj'].append('CMap')
                        else:
                            continue
        else:
            pdf['IsDamaged'] = True
            pdf['DamagedObj'].append(ObjName)

    #Compare Pages' Kids with Page search results.
    if 'Kids' in objlist.keys(): 
        kids = objlist['Kids']
        if objlist['Pages count'] == len(kids):#kids
            pdfPage = pdf['Page'] 
            if pdfPage != [] and len(pdfPage) == len(kids): 
                for k in pdfPage: 
                    pageNum = decompressObj[k][0]
                    if pageNum not in kids:
                        pdf["DamagedObj"].append("Page")
                        break
            elif pdfPage == []:
                pdf["DamagedObj"].append("Page")
            elif len(pdfPage)>len(kids):
                pdf["DamagedObj"].append("Pages")
            else:
                pdf["DamagedObj"].append("Page")
        else:
            pdf["DamagedObj"].append("Pages")
    else:#No Pages
        pdf["DamagedObj"].append("Pages")
    
    if pdf["DamagedObj"] == []:
        pdf['IsDamaged'] = False
    else:
        pdf['IsDamaged'] = True

    pdf["DamagedObj"] = list(set(pdf["DamagedObj"]))

#Font name parser -> output : {FontName : CMapObj Num}
def parse_FontName(decompressObj_checked, pdf):
    #check Font object -> out : {Font Name : number of ToUnicode object} 
    pdf['Font'] = list(set(pdf['Font']))
    if len(pdf['Font']) == 0: # If all font-related objects are missing -> need modification
        if pdf['SaveMethod'] == '한PDF' or pdf['SaveMethod'] == 'Mac': 
            pdf['IsRecoverable'] = False
        else: #If using other methods, map to DB (code to be added).
            pass
    else: 
        stream = re.compile(rb'(\/Font)\s*\<{2}\s*([A-z0-9\\\/\s]+)\>{2}', re.S) #Font name
        stream2 = re.compile(rb'(\/Font)\s*([A-z0-9\\\/\s]+)\>{2}', re.S)
        font_name = []
        for i in pdf['Font']:
            tmp= stream.findall(decompressObj_checked[i][2])
            tmp2 = stream2.findall(decompressObj_checked[i][2])
            stream_FontN = re.compile(rb'\/BaseFont\/([A-z\+]+)\/', re.S) #/Font 13 0 R
            if stream_FontN.search(decompressObj_checked[i][2]) != None:
                pdf['FontName'].append(stream_FontN.search(decompressObj_checked[i][2]).group().decode('utf-8').split('/')[2])
            if len(tmp) != 0:
                font_name.append([tmp[0][0], tmp[0][1]])#Store extracted font names in a list -> ['/Font' , 'C2_0 46 0 R']
            if len(tmp2) != 0:
                font_name.append([tmp2[0][0], tmp2[0][1]])
        fontName_dict = {} #Font name - font object 
        for i in font_name:
            font = i[1].split(b'/') #/C2_0 46 0 R -> " ", "C2_0 46 0 R", "?"
            if len(font) == 2:
                tmp = font[1].split(b' ')
                if re.match(rb'\b[A-Z]+[0-9]+\b', tmp[0]) != None:
                    if b'File' in tmp[0]:
                        continue
                    if len(tmp) >= 2:
                        if not(tmp[0] in fontName_dict.keys()): 
                            fontName_dict[tmp[0]] = tmp[1]
            elif len(font) > 2: 
                for f in font:
                    if len(f) > 1: 
                        tmp = f.split(b' ')
                        if re.match(rb'\b[A-Z]+[0-9]+\b', tmp[0]) != None:
                            if b'File' in tmp[0]:
                                continue
                            if len(tmp) >= 2:
                                if not(tmp[0] in fontName_dict.keys()):
                                    fontName_dict[tmp[0]] = tmp[1]
            else:
                tmp = font[0].split(b' ')
                if re.match(rb'\b[A-Z]+[0-9]+\b', tmp[0]) != None: 
                    if not(tmp[0] in fontName_dict.keys()):
                        fontName_dict[tmp[0]] = tmp[1]
                else: #/Font 13 0 R 
                    for k in decompressObj_checked:#fint object related font name
                        if tmp[0] == k[0]:
                            font_d = k[2].split(b'/') #need modification 
                            if len(font_d) == 2:
                                tmp2 = font_d[1].split(b' ')
                                if re.match(rb'\b[A-Z]+[0-9]+\b', tmp2[0]) != None: 
                                    if not(tmp[0] in fontName_dict.keys()):
                                        fontName_dict[tmp2[0]] = tmp2[1]
                            break
       
        #fontName_dict: {font name - the number of object related font} 
        #-> fontCmap_dict2 : {font name - the number of CMap object}
        fontCmap_dict2 = {}
        for i in fontName_dict.keys():
            TouniNum = b''
            for j in range(len(decompressObj_checked)-1):
                if fontName_dict[i] == decompressObj_checked[j][0]:
                    data = decompressObj_checked[j][2]
                    stream = re.compile(rb'\/ToUnicode\s(\d+)\s+(\d+)\sR', re.S)
                    repl = stream.findall(data)
                    if re.search(rb'\/Encoding\s\/MacRomanEncoding', data) != None:
                        #Mac Roman Character Set
                        TouniNum = j
                    elif len(repl) != 0:
                        TouniNum = repl[0][0]
                        fontCmap_dict2[i] = TouniNum  
                        break
                    fontCmap_dict2[i] = TouniNum
            fontCmap_dict2[i] = TouniNum

        #compare CMap and font name
        for i in fontCmap_dict2.keys():
            for j in pdf['CMap']:
                value = list(fontCmap_dict2.values())
                while b'' in value:
                    value.remove(b'')
                if fontCmap_dict2[i] == b'': #missing font
                    if len(value) == len(pdf['CMap']):
                        continue
                    pdf['isDamaged'] = True
                    pdf['DamagedObj'].append('Font')
                elif fontCmap_dict2[i] == decompressObj_checked[j][0]:
                    continue
                elif len(value) >len(pdf['CMap']): #missing cmap
                    pdf['isDamaged'] = True
                    pdf['DamagedObj'].append('CMap')
        pdf['FontCMap'] = fontCmap_dict2
        pdf["FontName"] = list(set(pdf["FontName"]))

#CMap parser
def parse_CMap(decompressObj, pdf):
    font_CidUnicode = {} #output : {fontname : {CID : unicode}}
    eng_table = pd.read_csv(os.path.dirname(os.path.realpath(__file__))+"\\eng_mapping_table.csv", header = None, names = ['cid', 'char', 'nothing'])
    eng_table = eng_table.drop('nothing', axis='columns')
    cmap = {}
    for i in range(52):
        cmap[eng_table['cid'][i]] = eng_table['char'][i]
    font_CidUnicode['eng'] = cmap
    # Extract and store CMap data.
    checked_cmap = []
    cnt = 0
    ran_cnt = 0
    FontCnt = 0
    CharStream = re.compile(rb'beginbfchar([\s\S]*?)endbfchar') #one
    RangeStream = re.compile(rb'beginbfrange([\s\S]*?)endbfrange') #range
    for num in pdf['CMap']:
        if decompressObj[num][0] in pdf['FontCMap'].values():
            for font in pdf['FontCMap'].keys():
                if decompressObj[num][0] == pdf['FontCMap'][font]:
                    checked_cmap.append(num)
                    font_CidUnicode[font] = {}
                    CMap_data = {}
                    c = decompressObj[num][2] 

                    
                    repl = CharStream.findall(c) #one
                    for j in repl:
                        pattern_bfchar = re.compile(rb'<([A-Fa-f0-9]+)>\s*<([A-Fa-f0-9]+)>')
                        li = pattern_bfchar.findall(j)
                        for h in li:
                            pdf_code = h[0].upper()
                            uni_code = h[1]
                            if len(uni_code) >4:
                                uni_code = uni_code[-4:]
                            font_CidUnicode[font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                    
                    repl = RangeStream.findall(c) #range
                    if len(repl) != 0:
                        for j in repl:
                            for k in j.split(b'\n'):
                                cnt = 0
                                if len(k) == 0:
                                    continue
                                #<0496> <0497> <B4DC>
                                #<07C7> <07C9> <C548> -> <07C7> <C548> / <07C8> <C549> / <07C9> <C550>
                                pattern_bfrange3 = re.compile(rb'\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>')
                                li = pattern_bfrange3.findall(k)
                                if not(b'[' in k) and len(li) != 0:
                                    num = int(li[0][1], 16) - int(li[0][0], 16)
                                    pdf_code = li[0][0]
                                    uni_code = li[0][2]
                                    font_CidUnicode[font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                    for h in range(0, num):
                                        uni_code = str(hex(int(uni_code, 16)+1))
                                        if len(uni_code) == 6:
                                            uni_code = uni_code.replace("0X","")
                                        elif len(uni_code) == 5:
                                            uni_code = uni_code.replace("X","")
                                        pdf_code = format(int(pdf_code, 16)+1, '04x')
                                        font_CidUnicode[font][pdf_code.upper()] = chr(int(uni_code, 16))
                                    cnt+=1
                                else:
                                    #<058B> <058B> [<B9DB>]
                                    pattern_bfrange1 = re.compile(rb'\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>\s*\[\<([A-Fa-f0-9]+)\>\]')
                                    li = pattern_bfrange1.findall(k)
                                    if len(li) != 0:
                                        for h in li:
                                            if h[0] == h[1]:
                                                pdf_code = h[0].upper()
                                                uni_code = h[2]
                                                font_CidUnicode[font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                            else:
                                                pdf_code = h[0].upper()
                                                uni_code = h[2]
                                                font_CidUnicode[font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                                pdf_code = h[1].upper()
                                                font_CidUnicode[font][pdf_code.decode().upper()] = chr(int(uni_code, 16)+1)
                                        cnt+=1
                                    #b'<0396> <0397> [<B05D> <B07C>]'
                                    #b'<0478> <047A> [<B418> <B41C> <B420>]'
                                    if cnt == 0:
                                        noBrace = k.split(b"[")[0]
                                        yesBrace = k.split(b"[")[1]
                                        noBrace = noBrace.split(b"<")
                                        yesBrace = yesBrace.split(b"<")
                                        if len(noBrace) == len(yesBrace):
                                            for u in range(1, len(noBrace)):
                                                pdf_code = noBrace[u][0:4].upper()
                                                uni_code = yesBrace[u][0:4]
                                                font_CidUnicode[font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                        else:
                                            num = int(noBrace[2][0:4], 16)-int(noBrace[1][0:4], 16)
                                            pdf_code = noBrace[1][0:4].decode()
                                            for u in range(0, num+1):
                                                uni_code = yesBrace[u+1][0:4]
                                                font_CidUnicode[font][pdf_code.upper()] = chr(int(uni_code, 16))
                                                pdf_code = str(hex(int(pdf_code, 16)+1)).upper()
                                                if len(pdf_code) == 6:
                                                    pdf_code = pdf_code.replace("0X","").upper()
                                                elif len(pdf_code) == 5:
                                                    pdf_code = pdf_code.replace("X","").upper()
                    FontCnt+=1
        else: #If CMap is missing from values()
            if not(num in checked_cmap) :
                ran_cnt+=1
                name = bytes("Random"+str(ran_cnt),'utf-8')
                CMap_data = {}
                c = decompressObj[num][2]
                
                repl = CharStream.findall(c) # one
                for j in repl:
                    pattern_bfchar = re.compile(rb'<([A-Fa-f0-9]+)>\s*<([A-Fa-f0-9]+)>')
                    li = pattern_bfchar.findall(j)
                    for h in li:
                        pdf_code = h[0].upper()
                        uni_code = h[1]
                        if len(uni_code)>4:
                            uni_code = uni_code[-4:]
                        CMap_data[pdf_code.decode().upper()] = chr(int(uni_code, 16))
                
                repl = RangeStream.findall(c)# range
                if len(repl) != 0:
                    for j in repl:
                        for k in j.split(b'\n'):
                            cnt = 0
                            if len(k) == 0:
                                continue
                            #<0496> <0497> <B4DC>
                            #<07C7> <07C9> <C548> -> <07C7> <C548> / <07C8> <C549> / <07C9> <C550>
                            pattern_bfrange3 = re.compile(rb'\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>')
                            li = pattern_bfrange3.findall(k)
                            if not(b'[' in k) and len(li) != 0:
                                num = int(li[0][1], 16) - int(li[0][0], 16)
                                pdf_code = li[0][0].upper()
                                uni_code = li[0][2]
                                CMap_data[pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                for h in range(0, num):
                                    uni_code = str(hex(int(uni_code, 16)+1))
                                    if len(uni_code) == 6:
                                        uni_code = uni_code.replace("0X","")
                                    elif len(uni_code) == 5:
                                        uni_code = uni_code.replace("X","")
                                    pdf_code = format(int(pdf_code, 16)+1, '04x').upper()
                                    CMap_data[pdf_code.upper()] = chr(int(uni_code, 16))
                                cnt+=1
                            else:
                                #<058B> <058B> [<B9DB>]
                                pattern_bfrange1 = re.compile(rb'\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>\s*\[\<([A-Fa-f0-9]+)\>\]')
                                li = pattern_bfrange1.findall(k)
                                if len(li) != 0:
                                    for h in li:
                                        if h[0] == h[1]:
                                            pdf_code = h[0].upper()
                                            uni_code = h[2]
                                            CMap_data[pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                        else:
                                            pdf_code = h[0].upper()
                                            uni_code = h[2]
                                            CMap_data[pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                            pdf_code = h[1].upper()
                                            CMap_data[pdf_code.decode().upper()] = chr(int(uni_code, 16)+1)
                                    cnt+=1
                                #b'<0396> <0397> [<B05D> <B07C>]'
                                #b'<0478> <047A> [<B418> <B41C> <B420>]'
                                if cnt == 0:
                                    noBrace = k.split(b"[")[0]
                                    yesBrace = k.split(b"[")[1]
                                    noBrace = noBrace.split(b"<")
                                    yesBrace = yesBrace.split(b"<")
                                    if len(noBrace) == len(yesBrace):
                                        for u in range(1, len(noBrace)):
                                            pdf_code = noBrace[u][0:4].upper()
                                            uni_code = yesBrace[u][0:4]
                                            CMap_data[pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                    else:
                                        num = int(noBrace[2][0:4], 16)-int(noBrace[1][0:4], 16)
                                        pdf_code = noBrace[1][0:4].decode().upper()
                                        for u in range(0, num+1):
                                            uni_code = yesBrace[u+1][0:4]
                                            CMap_data[pdf_code.upper()] = chr(int(uni_code, 16))
                                            pdf_code = str(hex(int(pdf_code, 16)+1)).upper()
                                            if len(pdf_code) == 6:
                                                pdf_code = pdf_code.replace("0X","").upper()
                                            elif len(pdf_code) == 5:
                                                pdf_code = pdf_code.replace("X","").upper()
                font_CidUnicode[name] = CMap_data
    return font_CidUnicode

#[Main]
def Parsing(decompressObj, pdf):
    CheckEssential(decompressObj, pdf)
    parse_FontName(decompressObj, pdf)
    pdf['FontCMap'] = parse_CMap(decompressObj, pdf)
=======
import pandas as pd
import os
import xml.etree.ElementTree as ET
import re
import main 
import ETC
import preprocess
import json
import tempfile
import subprocess
import shutil

#Metadata Parser -> Pending modification.
def parse_Metadata(decompressObj_checked, pdf, cnt):
    try:
        if pdf['Metadata'] != None:
            Metadata = {}
            hex_data = decompressObj_checked[pdf['Metadata']][2].decode('utf-8').strip()
            hex_data = hex_data.replace('\n','')
            hex_data = hex_data.replace('\r','')

            hex_data = hex_data.split('stream')[1]
            hex_data = '<root>'+hex_data+'</root>'
            
            
            # XML parsing
            root = ET.fromstring(hex_data)

            #Explore XML elements and output tags with text
            for element in root.iter():
                if element.text is not None:
                    # ModifyDate, CreateDate, DocumentID, InstanceID
                    if element.tag.endswith("ModifyDate") or element.tag.endswith("CreateDate") or element.tag.endswith("DocumentID") or element.tag.endswith("InstanceID") or element.tag.endswith("Producer") or element.tag.endswith("creator"):
                        key = element.tag.split("}")[1] if '}' in element.tag else element.tag
                        Metadata[key] = element.text
                elif element.tag.endswith("creator"):
                    for i in element.iter():
                        if i.tag.endswith("li"):
                            Metadata["Creator"] = i.text
        
        else:
            for i in decompressObj_checked:
                if b'Producer' in i[2] and b'CreationDate' in i[2]:
                    pdf['Metadata'] = i[0]
                    text = i[2].decode("utf-8", errors="replace")
                    pattern = re.compile(r'/(\w+)\s*\((.*?)\)')
                    matches = pattern.findall(text)
                    for key, val in matches:
                        if key == "Author":
                            Metadata["Author"] = val
                        elif key == "Creator":
                            Metadata["Creator"] = val
                        elif key == "CreationDate":
                            Metadata["CreateDate"] = val
                        elif key == "ModDate":
                            Metadata["ModifyDate"] = val
                        elif key == "Producer":
                            Metadata["Producer"] = val
                        elif key == "Title":
                            Metadata["Title"] = val
                        break
                else:
                    continue

        # Set 'Not found' if the keys ModifyDate, CreateDate, DocumentID, or InstanceID are missing
        for key in ["ModifyDate", "CreateDate", "DocumentID", "InstanceID", "Creator", "Producer", "Author", "Title"]:
            if key not in Metadata:
                Metadata[key] = 'Not found'
            else:
                with open(pdf['Result_path']+"\\PDF_"+str(cnt)+"_Metadata.txt", "a", encoding = 'utf-8') as f:
                    f.write(key+" : ", Metadata[key]+"\n")

    except Exception as e:
        return

#Verify essential objects
def CheckEssential(decompressObj, pdf): # catalog, page, pages, font, CMap, content 확인
    cnt = 0
    for cnt, i in enumerate(decompressObj):
        if b'/Catalog' in i[2] and b'/Pages' in i[2]: 
            pdf['Catalog'] = cnt
        elif b'/Pages' in i[2] and b'/Kids' in i[2]:
            pdf['Pages'] = cnt
        elif b'/Page' in i[2] and b'/Content' in i[2]: 
            pdf['Page'].append(cnt)
        elif b'/CIDInit' in i[2]: 
            pdf['CMap'].append(cnt)
        elif (b'<</MCID ' in i[2] and b'\n/P' in i[2]) or (b' Tf' in i[2] and b'BT' in i[2]) or (b'TJ' in i[2] and b' Tc' in i[2] and b' Tw' in i[2]) or b'\nQ\nq' in i[2]: #content 여러 개일 수 있음 -> 이를 어떻게 처리할 것인가?
            pdf['Content'].append(cnt) 
        elif b'XML' in i[2] and b'Metadata' in i[2]:
            pdf['Metadata'] = cnt
        if b'/Font' in i[2] or b'/ToUnicode' in i[2] or b'/DescendantFonts' in i[2]: #n개
            pdf['Font'].append(cnt)
        if b'/Resources' in i[2] and b'/Font' in i[2]:
            pdf['Resources'].append(cnt)
        if b'/Font' in i[2]:
            match = re.search(br"<<\s*(/F\d+\s+\d+\s+0\s+R\s*)+>>", i[2])
            if match:
                pdf['Resources'].append(cnt)
    
    #Verification Stage - Collect and Compare Relevant Information
    objlist  = {}
    for ObjName in ['Catalog', 'Pages', 'Page', 'Font', 'CMap','Content', 'Metadata', 'Resources']: 
        if pdf[ObjName] != None:
            if ObjName == 'Catalog': #Catalog -> Pages, Metadata 
                objData = decompressObj[pdf[ObjName]][2]
                stream = re.compile(rb'\/([a-zA-Z]+)\s(\d+)\s+(\d+)\sR', re.S)
                repl = stream.findall(objData)
                for j in repl:
                    objlist[j[0]] = j[1] 
            elif ObjName == 'Pages': #Pages -> Count, Kids
                objData = decompressObj[pdf[ObjName]][2]
                CntStream = re.compile(rb'\/Count\s(\d+)', re.S) #count - Check the number of pages.
                KidsStream = re.compile(rb'\/Kids[\s]*\[[A-Z0-9\s]*\]',re.S)#\/Kids\[(.*)\]', re.S)#kids
                objlist['Pages count'] = int(CntStream.findall(objData)[0], 16) #the number of page 

                objlist['Kids'] = []
                kids = KidsStream.findall(objData)[0]
                KidsStream2 = re.compile(rb'(\d+)\s(\d+)\sR', re.S)
                kids = KidsStream2.findall(kids)#page object number
                for j in kids:
                    objlist['Kids'].append(j[0])
            elif ObjName == 'Page': #Page -> Parent, Content
                if len(pdf[ObjName]) != 0:
                    page_cnt = 0
                    cnt = 1
                    for j in pdf[ObjName]:
                        objData = decompressObj[j][2]
                        stream = re.compile(rb'\/([a-zA-Z]+)\s(\d+)\s+(\d+)\sR', re.S)
                        stream2 = re.compile(rb'/Contents\s*(\[(?:.|\s)*?\]|\d+\s+\d+\s+R)', re.S)
                        content_d = stream2.findall(objData)
                        repl = stream.findall(objData)
                        for k in repl:
                            if k[0] == b'Parent':
                                page_cnt+=1
                            key = ('Page'+str(cnt)+'_').encode()+k[0] 
                            objlist[key] = k[1]
                        for k in content_d:
                            contents = re.findall(rb'(\d+)\s+\d+\s+R', k)  # ['4 0', '21 0']
                                # 리스트로 저장 (기존에 값이 있으면 extend)
                            key = ('Page' + str(cnt) + '_Content').encode()
                            if key not in objlist:
                                objlist[key] = contents
                            else:
                                objlist[key].extend(contents)
                            if len(pdf['Content']) == 0:
                                for num in contents:
                                    for cidx, i in enumerate(decompressObj):
                                        if i[0] == num:
                                            pdf['Content'].append(cidx)
                                            break
                        cnt+=1
                    if page_cnt != 0:
                        for k in objlist.keys():
                            if "Parent" in str(k): #Detect potential corruption by checking against the Pages attribute.
                                if b'Pages' in objlist.keys():
                                    if objlist[k] != objlist[b'Pages']:
                                        pdf['IsDamaged'] = True
                                        pdf['DamagedObj'].append('Page')
                                continue
                    else: #Treat as corrupted if the attribute is absent.
                        pdf['IsDamaged'] = True
                        pdf['DamagedObj'].append('Page')
                else: #Need Modification
                    pdf['IsDamaged'] = True
                    pdf['DamagedObj'].append('Page')
            elif ObjName == 'Content':
                if len(pdf[ObjName]) == 0: #content missing
                    pdf['IsDamaged'] = True
                    pdf['DamagedObj'].append('Content')
                    pdf['IsRecoverable'] = False #Irrecoverable -> Termination
                else:
                    cnt_content = 0
                    for k, v in objlist.items():
                        if isinstance(k, bytes) and b"_Content" in k:
                            if isinstance(v, list):
                                cnt_content += len(v)
                            else:
                                cnt_content += 1
                    if len(pdf[ObjName]) != cnt_content: #the number of content  != the number of  cnt_content 
                        pdf['IsDamaged'] = True
                        if len(pdf[ObjName]) > cnt_content: 
                            pdf['DamagedObj'].append('Page')
                        else:
                            pdf['DamagedObj'].append('Content')
            elif ObjName == "Font":
                if len(pdf[ObjName]) == 0: 
                    pdf['IsDamaged'] = True
                    pdf['DamagedObj'].append('ToUnicode')
                    pdf['DamagedObj'].append('DescendantFonts')
                    continue
                objlist[b'ToUnicode'] = []
                objlist[b'DescendantFonts'] = []
                des_idx = 0
                for j in pdf[ObjName]: 
                    objData = decompressObj[j][2]
                    stream = re.compile(rb'\/([a-zA-Z]+)\s(\d+)\s+(\d+)\sR', re.S)
                    repl = stream.findall(objData)
                    cnt = 0
                    for j in repl:
                        if j[0] == b'ToUnicode':
                            objlist[b'ToUnicode'].append(j[1])
                        elif j[0] == b'DescendantFonts':
                            objlist[b'DescendantFonts'].append(j[1])
                            des_idx+=1
                        else:
                            continue
                if len(objlist[b'ToUnicode']) != len(pdf['CMap']) or len(objlist[b'ToUnicode']) == 0:
                    pdf['IsDamaged'] = True
                    if len(objlist[b'ToUnicode']) == 0:
                        pdf['DamagedObj'].append('ToUnicode')
                    elif len(objlist[b'ToUnicode']) > len(pdf['CMap']):
                        pdf['DamagedObj'].append('CMap')
                    else:
                        pdf['DamagedObj'].append('ToUnicode')
                if des_idx == 0 or des_idx < len(objlist[b'ToUnicode']):
                    pdf['DamagedObj'].append('DescendantFonts')
            elif ObjName == 'Metadata':
                if pdf['Metadata'] == None:
                    pdf['IsDamaged'] = True
                    pdf['DamagedObj'].append('Metadata')
                    continue
            elif ObjName == 'Resources':
                if len(pdf[ObjName]) == 0:
                    pdf['IsDamaged'] = True
                    pdf['DamagedObj'].append('Resources')
                    continue
            else: #CMap
                if len(pdf[ObjName]) == 0:
                    pdf['IsDamaged'] = True
                    pdf['DamagedObj'].append('CMap')
                else: 
                    if 'ToUnicode' in objlist.keys():
                        if len(objlist[b'ToUnicode']) != 0:
                            errflag = False
                            if len(pdf[ObjName]) != len(objlist[b'ToUnicode']):
                                for k in pdf[ObjName]:
                                    objnum = decompressObj[k][0]
                                    for j in objlist[b'ToUnicode']:
                                        if j == objnum:
                                            errflag==False
                                            break
                                        else:
                                            errflag = True
                                    if errflag :
                                        pdf['IsDamaged'] = True
                                        break
                                if len(pdf[ObjName]) > len(objlist[b'ToUnicode']):
                                    pdf['DamagedObj'].append('ToUnicode')
                                else:
                                    pdf['DamagedObj'].append('CMap')
                        else:
                            continue
        else:
            pdf['IsDamaged'] = True
            pdf['DamagedObj'].append(ObjName)

    #Compare Pages' Kids with Page search results.
    if 'Kids' in objlist.keys(): 
        kids = objlist['Kids']
        if objlist['Pages count'] == len(kids):#kids
            pdfPage = pdf['Page'] 
            if pdfPage != [] and len(pdfPage) == len(kids): 
                for k in pdfPage: 
                    pageNum = decompressObj[k][0]
                    if pageNum not in kids:
                        print(f"⚠️ PageNum {pageNum} not in Kids!")
                        pdf["DamagedObj"].append("Page")
                        break
            elif pdfPage == []:
                pdf["DamagedObj"].append("Page")
            elif len(pdfPage)>len(kids):
                pdf["DamagedObj"].append("Pages")
            else:
                pdf["DamagedObj"].append("Page")
        else:
            pdf["DamagedObj"].append("Pages")
    else:#No Pages
        pdf["DamagedObj"].append("Pages")
    
    if pdf["DamagedObj"] == []:
        pdf['IsDamaged'] = False    
    else:
        pdf['IsDamaged'] = True

    pdf["DamagedObj"] = list(set(pdf["DamagedObj"]))

    return objlist

def c_savemethod_classify(decompressObj, pdf):
    content_objs = []

    # Content 객체 목록 수집
    if 'Content_p' in pdf and pdf['Content_p'] is not None:
        for page_idx, content_ids in pdf['Content_p'].items():
            for i in content_ids:
                content_objs.append(decompressObj[i][2])  # Content data
    else:
        for i in pdf['Content']:
            content_objs.append(decompressObj[i][2])  # Content data

    # 조건 3: /P <</MCID 2회 이상 #위로 순서 올리기
    for c in content_objs:
        matches = re.findall(rb"/P\s*<</MCID", c)
        if len(matches) >= 2:
            pdf['SaveMethod'] = "Adobe"
            print("content obj에서 저장방식 Adobe 식별")
            return
    # 조건 1: /Span, Lang, EMC 문자열이 모두 있는 경우
    for c in content_objs:
        if b"/Span" in c and b"Lang" in c and b"EMC" in c:
            pdf['SaveMethod'] = "Microsoft Save as"
            print("content obj에서 저장방식 Microsoft Save as 식별")
            return

    # 조건 2: "0.750000"으로 시작하는 줄, BT/ET 2회 이상, <####> 존재
    for c in content_objs:
        c_text = c.decode(errors='ignore')
        if any(line.strip().startswith("0.750000 0.000000 0.000000 -0.750000 0.000000") for line in c_text.splitlines()):
            # bt_count = c_text.count("BT")
            # et_count = c_text.count("ET")
            # angle_brackets = re.findall(r"<[^>]{1,10}>", c_text)
            # if bt_count >= 2 and et_count >= 2 and len(angle_brackets) >= 1:
            pdf['SaveMethod'] = "Microsoft Print to PDF"
            print("content obj에서 저장방식 Microsoft Print to PDF 식별")
            return
    
        # 조건 4: MAC
    for c in content_objs:
        c_text = c.decode(errors='ignore')
        if any(line.strip().startswith("q Q q /Cs1 cs 0 0 0") for line in c_text.splitlines()):
            pdf['SaveMethod'] = "MAC"
            print("content obj에서 저장방식 MAC 식별")
            return
        
def font_change_check(decompressObj_checked, pdf):
    page_font_map = {}                 # 임시 저장
    font_change = False
    pdf['Font'] = list(set(pdf['Font']))
    if len(pdf['Font']) == 0: # If all font-related objects are missing -> need modification
        if pdf['SaveMethod'] == '한PDF' or pdf['SaveMethod'] == 'Mac': 
            pdf['IsRecoverable'] = False
        else: #If using other methods, map to DB (code to be added).
            font_change = None #Fontchange 알 수 없음 
            pass
    else: 
        stream = re.compile(rb'(\/Font)\s*\<{2}\s*([A-z0-9\\\/\s]+)\>{2}', re.S) #Font name
        stream2 = re.compile(rb'(\/Font)\s*([A-z0-9\\\/\s]+)\>{2}', re.S)
        font_name = []
        for i in pdf['Font']:
            tmp= stream.findall(decompressObj_checked[i][2])
            tmp2 = stream2.findall(decompressObj_checked[i][2])
            stream_FontN = re.compile(rb'\/BaseFont\s*\/([A-z\+]+)', re.S) #/Font 13 0 R
            font_ref = re.search(rb'/Font\s+(\d+)\s+0\s+R', decompressObj_checked[i][2])
            if font_ref: #알PDF의 경우 추가
                ref_obj_num = font_ref.group(1).decode()
                for entry in decompressObj_checked:
                    if entry[0].decode() == ref_obj_num:
                        ref_obj_data = entry[2]
                        # 내부에 또 객체 참조가 있는 경우
                        matches = re.findall(rb'/[A-Za-z0-9_]+\s+\d+\s+0\s+R', ref_obj_data)
                        for m in matches:
                            font_name.append(["/Font", m])
            else:
                if stream_FontN.search(decompressObj_checked[i][2]) is not None:
                    basefont_raw = stream_FontN.search(decompressObj_checked[i][2]).group(1).decode('utf-8')  # 캡처된 그룹만
                    if '+' in basefont_raw:
                        basefont_clean = basefont_raw.split('+')[1]  # subset prefix 제거
                    else:
                        basefont_clean = basefont_raw
                    pdf['FontName'].append(basefont_clean)
                if len(tmp) != 0:
                    font_name.append([tmp[0][0], tmp[0][1]])#Store extracted font names in a list -> ['/Font' , 'C2_0 46 0 R']
                if len(tmp2) != 0:
                    font_name.append([tmp2[0][0], tmp2[0][1]])                

        font_line_pat = re.compile(rb'/([A-Z0-9_]{2,})\s+(\d+)\s+0\s+R')
        page_idx = -1
        for _, raw_line in font_name:                  # raw_line = b'/C2_0 89 0 R/...'
            if font_line_pat.search(raw_line):
                # 새 페이지 시작으로 간주
                page_idx += 1
                page_font_map[page_idx] = {}

                # 태그·객체번호 추출
                for tag, num in font_line_pat.findall(raw_line):
                    page_font_map[page_idx][tag] = num # b'89'

        # 3) 태그별 “obj 번호 집합” 계산
        from collections import defaultdict
        tag_usage = defaultdict(set)                   # {b'TT1': {b'103', b'110'}, ...}
        for pidx, mapping in page_font_map.items():
            for tag, num in mapping.items():
                tag_usage[tag].add(num)
        
        # 4) 페이지별 폰트 번호가 달라지는지 여부 확인
        if len(tag_usage) > 0:
            for tag, nums in tag_usage.items():
                if len(nums) > 1:
                    font_change = True # 폰트 변경 발생
                    break
                else:
                    font_change = False

    if 'Resources' in pdf['DamagedObj']:
        font_change = None # 폰트 변경 여부 알 수 없음
        
    pdf['FontChange'] = font_change
    return font_change

def parse_content_page(decompressObj, pdf, objlist):
    pdf['Content_p'] = {}  # page_idx: [content_obj_nums]
    pdf['Resource_p'] = {}

    if not objlist: # ✅ objlist가 None이면 함수 종료
        print("⚠️ objlist is None or empty. Skipping content/resource parsing.")
        return pdf

    for page_idx, page_num in enumerate(pdf['Page'], start=1000):
        page_tag = f'Page{page_idx - 999}_'.encode()  # e.g., b'Page1_'

        content_key = page_tag + b'Content'         # ✅ 1. Content 매핑
        if content_key in objlist:
            content_refs = objlist[content_key]
            if not isinstance(content_refs, list):
                content_refs = [content_refs]

            for num in content_refs:
                for cnt, obj in enumerate(decompressObj):
                    if obj[0] == num:
                        pdf['Content_p'].setdefault(page_idx, []).append(cnt)
                        break

        resource_key = page_tag + b'Resources' # ✅ 2. Resources 매핑
        if resource_key in objlist:
            resource_refs = objlist[resource_key]
            if not isinstance(resource_refs, list):
                resource_refs = [resource_refs]

            for num in resource_refs:
                for cnt, obj in enumerate(decompressObj):
                    if obj[0] == num:
                        pdf['Resource_p'].setdefault(page_idx, []).append(cnt)
                        break

        # ✅ 3) objlist에 Resources가 없을 때 → Page 객체 번호와 Resource 객체 번호가 동일한 경우
        elif resource_key not in objlist:
            # Page 번호와 Resource 번호가 동일한 경우 확인
            if 'Resources' in pdf:
                for res_num in pdf['Resources']:
                    if res_num == page_num:
                        pdf['Resource_p'].setdefault(page_idx, []).append(res_num)  # 동일 번호 발견
    return pdf

#Font name parser -> output : {FontName : CMapObj Num}
def parse_FontName(decompressObj_checked, pdf):
    #check Font object -> out : {Font Name : number of ToUnicode object} 
    pdf['Font'] = list(set(pdf['Font']))
    if len(pdf['Font']) == 0: # If all font-related objects are missing -> need modification
        if pdf['SaveMethod'] == '한PDF' or pdf['SaveMethod'] == 'Mac': 
            pdf['IsRecoverable'] = False
        else: #If using other methods, map to DB (code to be added).
            pass
    else: 
        stream = re.compile(rb'(\/Font)\s*\<{2}\s*([A-z0-9\\\/\s]+)\>{2}', re.S) #Font name
        stream2 = re.compile(rb'(\/Font)\s*([A-z0-9\\\/\s]+)\>{2}', re.S)
        font_name = []
        for i in pdf['Font']:
            tmp= stream.findall(decompressObj_checked[i][2])
            tmp2 = stream2.findall(decompressObj_checked[i][2])
            stream_FontN = re.compile(rb'\/BaseFont\s*\/([A-z\+]+)', re.S) #/Font 13 0 R
            font_ref = re.search(rb'/Font\s+(\d+)\s+0\s+R', decompressObj_checked[i][2])
            if font_ref: #알PDF의 경우 추가
                ref_obj_num = font_ref.group(1).decode()
                for entry in decompressObj_checked:
                    if entry[0].decode() == ref_obj_num:
                        ref_obj_data = entry[2]
                        # 내부에 또 객체 참조가 있는 경우
                        matches = re.findall(rb'/[A-Za-z0-9_]+\s+\d+\s+0\s+R', ref_obj_data)
                        for m in matches:
                            font_name.append(["/Font", m])
            else:
                if stream_FontN.search(decompressObj_checked[i][2]) is not None:
                    basefont_raw = stream_FontN.search(decompressObj_checked[i][2]).group(1).decode('utf-8')  # 캡처된 그룹만
                    if '+' in basefont_raw:
                        basefont_clean = basefont_raw.split('+')[1]  # subset prefix 제거
                    else:
                        basefont_clean = basefont_raw
                    pdf['FontName'].append(basefont_clean)
                if len(tmp) != 0:
                    font_name.append([tmp[0][0], tmp[0][1]])#Store extracted font names in a list -> ['/Font' , 'C2_0 46 0 R']
                if len(tmp2) != 0:
                    font_name.append([tmp2[0][0], tmp2[0][1]])                

        fontName_dict = {} #Font name - font object 
        for i in font_name:
            font = i[1].split(b'/') #/C2_0 46 0 R -> " ", "C2_0 46 0 R", "?"
            if len(font) == 2:
                tmp = font[1].split(b' ')
                if re.match(rb'\b[A-Z]+[0-9_]+\b', tmp[0]) != None:
                    if b'File' in tmp[0]:
                        continue
                    if len(tmp) >= 2:
                        if not(tmp[0] in fontName_dict.keys()): 
                            fontName_dict[tmp[0]] = tmp[1]
            elif len(font) > 2: 
                for f in font:
                    if len(f) > 1: 
                        tmp = f.split(b' ')
                        if re.match(rb'\b[A-Z]+[0-9_]+\b', tmp[0]) != None:
                            if b'File' in tmp[0]:
                                continue
                            if len(tmp) >= 2:
                                if not(tmp[0] in fontName_dict.keys()):
                                    fontName_dict[tmp[0]] = tmp[1]
            else:
                tmp = font[0].split(b' ')
                if re.match(rb'\b[A-Z]+[0-9_]+\b', tmp[0]) != None: 
                    if not(tmp[0] in fontName_dict.keys()):
                        fontName_dict[tmp[0]] = tmp[1]
                else: #/Font 13 0 R 
                    for k in decompressObj_checked:#fint object related font name
                        if tmp[0] == k[0]:
                            font_d = k[2].split(b'/') #need modification 
                            if len(font_d) == 2:
                                tmp2 = font_d[1].split(b' ')
                                if re.match(rb'\b[A-Z]+[0-9_]+\b', tmp2[0]) != None: 
                                    if not(tmp[0] in fontName_dict.keys()):
                                        fontName_dict[tmp2[0]] = tmp2[1]
                            break
       
        #fontName_dict: {font name - the number of object related font} 
        #-> fontCmap_dict2 : {font name - the number of CMap object}
        fontCmap_dict2 = {}
        for i in fontName_dict.keys():
            TouniNum = b''
            for j in range(len(decompressObj_checked)-1):
                if fontName_dict[i] == decompressObj_checked[j][0]:
                    data = decompressObj_checked[j][2]
                    stream = re.compile(rb'\/ToUnicode\s(\d+)\s+(\d+)\sR', re.S)
                    stream2 = re.compile(rb'\/Encoding\s+(\d+)\s+(\d+)\sR', re.S) #알PDF의 경우 추가
                    repl = stream.findall(data)
                    repl2 = stream2.findall(data)
                    if len(repl) != 0:
                        TouniNum = repl[0][0]
                        fontCmap_dict2[i] = TouniNum  
                        break
                    elif re.search(rb'\/Subtype\s*\/Type1', data) != None:
                        fontCmap_dict2[i] = b'Type1'
                        break
                    elif len(repl2) != 0:
                        TouniNum = repl2[0][0]
                        fontCmap_dict2[i] = TouniNum
                        break
                    elif re.search(rb'\/Encoding\s\/MacRomanEncoding', data) != None:
                        #Mac Roman Character Set
                        TouniNum = j
                    else:
                        try:
                            rel = re.search(rb'\#6 0 R', data)
                        except:
                            pass
                    fontCmap_dict2[i] = TouniNum
            if i in fontCmap_dict2 and fontCmap_dict2[i] is None:
                fontCmap_dict2[i] = TouniNum

        #compare CMap and font name
        for i in fontCmap_dict2.keys():
            for j in pdf['CMap']:
                value = list(fontCmap_dict2.values())
                while b'' in value:
                    value.remove(b'')
                if fontCmap_dict2[i] == b'': #missing font
                    if len(value) == len(pdf['CMap']):
                        continue
                    pdf['isDamaged'] = True
                    pdf['DamagedObj'].append('Font')
                elif fontCmap_dict2[i] == decompressObj_checked[j][0]:
                    continue
                elif len(value) >len(pdf['CMap']): #missing cmap
                    pdf['isDamaged'] = True
                    pdf['DamagedObj'].append('CMap')
        pdf['FontCMap'] = fontCmap_dict2
        pdf["FontName"] = list(set(pdf["FontName"]))

def parse_FontName_p(decompressObj_checked, pdf):  

    pdf['Font'] = list(set(pdf['Font']))
    if len(pdf['Font']) == 0: # If all font-related objects are missing -> need modification
        if pdf['SaveMethod'] == '한PDF' or pdf['SaveMethod'] == 'Mac': 
            pdf['IsRecoverable'] = False
        else: #If using other methods, map to DB (code to be added).
            pass
    else: 
        stream = re.compile(rb'(\/Font)\s*\<{2}\s*([A-z0-9\\\/\s]+)\>{2}', re.S) #Font name
        stream2 = re.compile(rb'(\/Font)\s*([A-z0-9\\\/\s]+)\>{2}', re.S)
        font_name = []
        for i in pdf['Font']:
            tmp= stream.findall(decompressObj_checked[i][2])
            tmp2 = stream2.findall(decompressObj_checked[i][2])
            stream_FontN = re.compile(rb'\/BaseFont\s*\/([A-z\+]+)', re.S) #/Font 13 0 R
            font_ref = re.search(rb'/Font\s+(\d+)\s+0\s+R', decompressObj_checked[i][2])
            if font_ref: #알PDF의 경우 추가
                ref_obj_num = font_ref.group(1).decode()
                for entry in decompressObj_checked:
                    if entry[0].decode() == ref_obj_num:
                        ref_obj_data = entry[2]
                        # 내부에 또 객체 참조가 있는 경우
                        matches = re.findall(rb'/[A-Za-z0-9_]+\s+\d+\s+0\s+R', ref_obj_data)
                        for m in matches:
                            font_name.append(["/Font", m])
            else:
                basefont_match = stream_FontN.search(decompressObj_checked[i][2])
                if basefont_match is not None:
                    basefont_val = basefont_match.group().decode('utf-8').split('/')[2]
                    if not basefont_val.startswith("CIDFont") and len(basefont_val) > 1:  # CIDFont로 시작하면 무시
                        pdf['FontName'].append(basefont_val)
                if len(tmp) != 0:
                    font_name.append([tmp[0][0], tmp[0][1]])#Store extracted font names in a list -> ['/Font' , 'C2_0 46 0 R']
                if len(tmp2) != 0:
                    font_name.append([tmp2[0][0], tmp2[0][1]])
    if not pdf['FontName'] or any(len(x) == 1 for x in pdf['FontName']):
        fontfilename = parse_FontName_fontfile(decompressObj_checked)
        if fontfilename:
            for name in fontfilename:
                if name not in pdf['FontName']:
                   pdf['FontName'].append(name)         

def parse_FontName_fontfile(decompressObj):  

    def run_ttx_extract(file_path, tables=["name"], font_index=None, output_dir=None): # TTX 실행 함수
        cmd = ["ttx"]
        for t in tables:
            cmd.extend(["-t", t])
        if font_index is not None:
            cmd.extend(["-y", str(font_index)])
        if output_dir:
            basename = os.path.basename(file_path)
            name = os.path.splitext(basename)[0]
            if font_index is not None:
                output_name = f"{name}#{font_index}.ttx"
            else:
                output_name = f"{name}.ttx"
            output_file = os.path.join(output_dir, output_name)
            cmd.extend(["-o", output_file])
        cmd.append(file_path)

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return output_file
        except subprocess.CalledProcessError:
            return None

    def extract_postscript_name(ttx_path): # nameid=6 추출 함수
        try:
            tree = ET.parse(ttx_path)
            root = tree.getroot()
            name_table = root.find("name")
            if name_table is not None:
                for record in name_table.findall("namerecord"):
                    if record.get("nameID") == "6":
                        return record.text.strip()
        except Exception:
            pass
        return None
    """
    streams: list of bytes (이미 decompressed된 PDF stream 데이터)
    반환값: PostScript name 문자열 리스트
    """
    psnames = []
    for obj in decompressObj:
        if len(obj) < 3:
            continue

        data = obj[2]  # 이미 decompressed된 바이트 데이터

        # hex signature 검사
        signatures = [
            b"\x44\x53\x49\x47",  # DSIG
            b"\x63\x6d\x61\x70",  # cmap
            b"\x67\x6c\x79\x66"   # glyf
        ]
        if not all(sig in data for sig in signatures):
            continue  # TTF 아님

        # 임시 디렉토리 생성
        temp_root = tempfile.mkdtemp(prefix="pdf_ttf_")
        try:
            ttf_path = os.path.join(temp_root, "font.ttf")
            with open(ttf_path, "wb") as f:
                f.write(data)

            # TTX 추출
            ttx_path = run_ttx_extract(ttf_path, tables=["name"], output_dir=temp_root)
            if not ttx_path:
                continue

            # nameID=6 추출
            ps_name = extract_postscript_name(ttx_path)
            if ps_name:
                psnames.append(ps_name)
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    return psnames


def parse_FontName_pidx(decompressObj_checked, pdf):
    fontName_dictp = {}  # 최종 결과: {pidx: {fonttag: objnum}}
    used_pidx = set()
    font_line_pat = re.compile(rb'/([A-Z0-9_]+)\s+(\d+)\s+0\s+R')
    resource_p_all_indices = set()

    if 'Resource_p' in pdf and pdf['Resource_p']:
        for pidx, obj_indices in pdf['Resource_p'].items():
            for i in obj_indices:
                obj_num = decompressObj_checked[i][0]
                data = decompressObj_checked[i][2]
                for tag, num in font_line_pat.findall(data):
                    fontName_dictp.setdefault(pidx, {})[tag] = num
                resource_p_all_indices.add(i)
            used_pidx.add(pidx)

    # ✅ Resource 전체 중 Resource_p에 없는 인덱스는 따로 처리
    next_pidx = 0
    for i in pdf.get('Resources', []):
        if i in resource_p_all_indices:
            continue  # 이미 Resource_p에서 처리된 객체이므로 skip

        data = decompressObj_checked[i][2]
        obj_num = decompressObj_checked[i][0]
        tags_found = False

        for tag, num in font_line_pat.findall(data):
            # 새 pidx 부여
            while next_pidx in used_pidx:
                next_pidx += 1

            fontName_dictp.setdefault(next_pidx, {})[tag] = num
            tags_found = True

        if tags_found:
            used_pidx.add(next_pidx)

    #fontName_dictp: {font name - the number of object related font} 
    #-> fontCmap_dictp2 : {font name - the number of CMap object}
    fontCmap_dictp2 = {}
    for pidx, font_map in fontName_dictp.items():
        fontCmap_dictp2[pidx] = {}
        for font_name, obj_num in font_map.items():
            TouniNum = b''
            for j in range(len(decompressObj_checked)-1):
                if decompressObj_checked[j][0] == obj_num:
                    data = decompressObj_checked[j][2]
                    stream = re.compile(rb'\/ToUnicode\s(\d+)\s+(\d+)\sR', re.S)
                    stream2 = re.compile(rb'\/Encoding\s+(\d+)\s+(\d+)\sR', re.S) #알PDF의 경우 추가
                    repl = stream.findall(data)
                    repl2 = stream2.findall(data)
                    if len(repl) != 0:
                        TouniNum = repl[0][0]
                        fontCmap_dictp2[pidx][font_name] = TouniNum  
                        break
                    elif re.search(rb'\/Subtype\s*\/Type1', data) != None:
                        fontCmap_dictp2[pidx][font_name] = b'Type1'
                        break
                    elif len(repl2) != 0:
                        TouniNum = repl2[0][0]
                        fontCmap_dictp2[pidx][font_name] = TouniNum
                        break
                    elif re.search(rb'\/Encoding\s\/MacRomanEncoding', data) != None:
                        #Mac Roman Character Set
                        TouniNum = j
                        fontCmap_dictp2[pidx][font_name] = TouniNum
                    else:
                        try:
                            rel = re.search(rb'\#6 0 R', data)
                        except:
                            pass
                    fontCmap_dictp2[pidx][font_name] = TouniNum
                
            if font_name in fontCmap_dictp2[pidx] and fontCmap_dictp2[pidx][font_name] == None:
                fontCmap_dictp2[pidx][font_name] = TouniNum

        #compare CMap and font name
        # for i in fontCmap_dictp2.keys():
        #     for j in pdf['CMap']:
        #         value = list(fontCmap_dictp2.values())
        #         while b'' in value:
        #             value.remove(b'')
        #         if fontCmap_dictp2[i] == b'': #missing font
        #             if len(value) == len(pdf['CMap']):
        #                 continue
        #             pdf['isDamaged'] = True
        #             pdf['DamagedObj'].append('Font')
        #         elif fontCmap_dictp2[i] == decompressObj_checked[j][0]:
        #             continue
        #         elif len(value) >len(pdf['CMap']): #missing cmap
        #             pdf['isDamaged'] = True
        #             pdf['DamagedObj'].append('CMap')
        pdf['FontCMap'] = fontCmap_dictp2
        # pdf["FontName"] = list(set(pdf["FontName"]))

#CMap parser
def parse_CMap(decompressObj, pdf):
    font_CidUnicode = {} #output : {fontname : {CID : unicode}}
    eng_table = pd.read_csv(os.path.dirname(os.path.realpath(__file__))+"\\eng_mapping_table.csv", header = None, names = ['cid', 'char', 'nothing'])
    eng_table = eng_table.drop('nothing', axis='columns')
    cmap = {}
    for i in range(52):
        cmap[eng_table['cid'][i]] = eng_table['char'][i]
    uni2_table = pd.read_csv(os.path.dirname(os.path.realpath(__file__))+"\\uni2_table.csv", header = None, names = ['cid', 'char'])
    uni2_cmap = {}
    for i in range(len(uni2_table)):
        uni2_cmap[uni2_table['cid'][i]] = uni2_table['char'][i]
    font_CidUnicode[b'eng'] = cmap
    font_CidUnicode[b'uni2'] = uni2_cmap
    # Extract and store CMap data.
    checked_cmap = []
    cnt = 0
    ran_cnt = 0
    FontCnt = 0
    CharStream = re.compile(rb'beginbfchar([\s\S]*?)endbfchar') #one
    RangeStream = re.compile(rb'beginbfrange([\s\S]*?)endbfrange') #range
    RangeStream2 = re.compile(rb'begincidrange([\s\S]*?)endcidrange') #range2 #알PDF의 경우 추가 
    for num in pdf['CMap']:
        if decompressObj[num][0] in pdf['FontCMap'].values():
            for font in pdf['FontCMap'].keys():
                if type(pdf['FontCMap'][font]) == int:
                    c = decompressObj[pdf['FontCMap'][font]][2]
                    if re.search(rb'\/Encoding\s\/MacRomanEncoding', c) != None:
                        MacRoman = pd.read_csv(os.path.dirname(os.path.realpath(__file__))+"\\Mac_Roman_character.csv", header = None, names = ['code', 'mean', 'nothing'])
                        MacRoman = MacRoman.drop('nothing', axis='columns')
                        CidUnicode = {}
                        #fontCmap_dict2에 저장함
                        for i in range(0, 255):
                            CidUnicode[MacRoman['code'][i]] = chr(MacRoman['mean'][i])
                        font_CidUnicode[font] = CidUnicode
                        continue

                if decompressObj[num][0] == pdf['FontCMap'][font]:
                    checked_cmap.append(num)
                    font_CidUnicode[font] = {}
                    CMap_data = {}
                    c = decompressObj[num][2] 

                    
                    repl = CharStream.findall(c) #one
                    for j in repl:
                        pattern_bfchar = re.compile(rb'<([A-Fa-f0-9]+)>\s*<([A-Fa-f0-9]+)>')
                        li = pattern_bfchar.findall(j)
                        for h in li:
                            pdf_code = h[0].upper()
                            uni_code = h[1]
                            if len(uni_code) >4:
                                uni_code = uni_code[-4:]
                            font_CidUnicode[font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                    
                    repl = RangeStream.findall(c) #range
                    if len(repl) != 0:
                        for j in repl:
                            for k in j.split(b'\n'):
                                cnt = 0
                                if len(k) == 0:
                                    continue
                                #<0496> <0497> <B4DC>
                                #<07C7> <07C9> <C548> -> <07C7> <C548> / <07C8> <C549> / <07C9> <C550>
                                pattern_bfrange3 = re.compile(rb'\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>')
                                li = pattern_bfrange3.findall(k)
                                if not(b'[' in k) and len(li) != 0:
                                    num = int(li[0][1], 16) - int(li[0][0], 16)
                                    pdf_code = li[0][0]
                                    uni_code = li[0][2]
                                    font_CidUnicode[font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                    for h in range(0, num):
                                        uni_code = str(hex(int(uni_code, 16)+1))
                                        if len(uni_code) == 6:
                                            uni_code = uni_code.replace("0X","")
                                        elif len(uni_code) == 5:
                                            uni_code = uni_code.replace("X","")
                                        if len(pdf_code) == 4:
                                            pdf_code = format(int(pdf_code, 16)+1, '04x')
                                        elif len(pdf_code) == 2: #알PDF, mac의 경우 2자리로 출력
                                            pdf_code = format(int(pdf_code, 16)+1, '02x')
                                        font_CidUnicode[font][pdf_code.upper()] = chr(int(uni_code, 16))
                                    cnt+=1
                                else:
                                    #<058B> <058B> [<B9DB>]
                                    pattern_bfrange1 = re.compile(rb'\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>\s*\[\<([A-Fa-f0-9]+)\>\]')
                                    li = pattern_bfrange1.findall(k)
                                    if len(li) != 0:
                                        for h in li:
                                            if h[0] == h[1]:
                                                pdf_code = h[0].upper()
                                                uni_code = h[2]
                                                font_CidUnicode[font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                            else:
                                                pdf_code = h[0].upper()
                                                uni_code = h[2]
                                                font_CidUnicode[font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                                pdf_code = h[1].upper()
                                                font_CidUnicode[font][pdf_code.decode().upper()] = chr(int(uni_code, 16)+1)
                                        cnt+=1
                                    #b'<0396> <0397> [<B05D> <B07C>]'
                                    #b'<0478> <047A> [<B418> <B41C> <B420>]'
                                    if cnt == 0:
                                        noBrace = k.split(b"[")[0]
                                        yesBrace = k.split(b"[")[1]
                                        noBrace = noBrace.split(b"<")
                                        yesBrace = yesBrace.split(b"<")
                                        if len(noBrace) == len(yesBrace):
                                            for u in range(1, len(noBrace)):
                                                pdf_code = noBrace[u][0:4].upper()
                                                uni_code = yesBrace[u][0:4]
                                                font_CidUnicode[font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                        else:
                                            num = int(noBrace[2][0:4], 16)-int(noBrace[1][0:4], 16)
                                            pdf_code = noBrace[1][0:4].decode()
                                            for u in range(0, num+1):
                                                uni_code = yesBrace[u+1][0:4]
                                                font_CidUnicode[font][pdf_code.upper()] = chr(int(uni_code, 16))
                                                pdf_code = f"{int(pdf_code, 16) + 1:04X}"
                                                if len(pdf_code) == 6:
                                                    pdf_code = pdf_code.replace("0X","").upper()
                                                elif len(pdf_code) == 5:
                                                    pdf_code = pdf_code.replace("X","").upper()

                    repl = RangeStream2.findall(c) #range2
                    if len(repl) != 0:
                        for j in repl:
                            for k in j.split(b'\n'):
                                cnt = 0
                                if len(k) == 0:
                                    continue
                                #<8000><80ff>256 -> <8000><0100> / <8001><0101> /.../ <80ff><01FF>
                                pattern_cidrange = re.compile(rb'\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>\s*([A-Fa-f0-9]+)')
                                li = pattern_cidrange.findall(k)
                                if not (b'[' in k) and len(li) != 0:
                                    start_code = li[0][0]  # 예: b'8000'
                                    end_code   = li[0][1]  # 예: b'80ff'
                                    base_code  = li[0][2]  # 예: b'0100' (또는 b'256' 등)

                                    cidnum = int(end_code, 16) - int(start_code, 16)
                                    
                                    pdf_code = start_code
                                    uni_code = base_code
                                    font_CidUnicode[font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                    
                                    for _ in range(cidnum):
                                        pdf_code_val = int(pdf_code, 16) + 1
                                        uni_code_val = int(uni_code, 16) + 1
                                        pdf_code = format(pdf_code_val, '04x').encode()   # b'8001', b'8002' ...
                                        uni_code = format(uni_code_val, '04x').encode()   # b'0101', b'0102' ...
                                        
                                        font_CidUnicode[font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                    
                                    cnt += 1
                    FontCnt+=1

                elif pdf['FontCMap'][font] == b'Type1':
                    font_CidUnicode[font] = {"__Type1__": True}

                    FontCnt+=1
        else: #If CMap is missing from values()
            if not(num in checked_cmap) :
                ran_cnt+=1
                name = bytes("Random"+str(ran_cnt),'utf-8')
                CMap_data = {}
                c = decompressObj[num][2]
                
                repl = CharStream.findall(c) # one
                for j in repl:
                    pattern_bfchar = re.compile(rb'<([A-Fa-f0-9]+)>\s*<([A-Fa-f0-9]+)>')
                    li = pattern_bfchar.findall(j)
                    for h in li:
                        pdf_code = h[0].upper()
                        uni_code = h[1]
                        if len(uni_code)>4:
                            uni_code = uni_code[-4:]
                        CMap_data[pdf_code.decode().upper()] = chr(int(uni_code, 16))
                
                repl = RangeStream.findall(c)# range
                if len(repl) != 0:
                    for j in repl:
                        for k in j.split(b'\n'):
                            cnt = 0
                            if len(k) == 0:
                                continue
                            #<0496> <0497> <B4DC>
                            #<07C7> <07C9> <C548> -> <07C7> <C548> / <07C8> <C549> / <07C9> <C550>
                            pattern_bfrange3 = re.compile(rb'\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>')
                            li = pattern_bfrange3.findall(k)
                            if not(b'[' in k) and len(li) != 0:
                                num = int(li[0][1], 16) - int(li[0][0], 16)
                                pdf_code = li[0][0].upper()
                                uni_code = li[0][2]
                                CMap_data[pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                for h in range(0, num):
                                    uni_code = str(hex(int(uni_code, 16)+1))
                                    if len(uni_code) == 6:
                                        uni_code = uni_code.replace("0X","")
                                    elif len(uni_code) == 5:
                                        uni_code = uni_code.replace("X","")
                                    elif len(pdf_code) == 2:
                                        pdf_code = format(int(pdf_code, 16)+1, '02x')
                                    else:
                                        pdf_code = format(int(pdf_code, 16)+1, '04x').upper()
                                    CMap_data[pdf_code.upper()] = chr(int(uni_code, 16))
                                cnt+=1
                            else:
                                #<058B> <058B> [<B9DB>]
                                pattern_bfrange1 = re.compile(rb'\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>\s*\[\<([A-Fa-f0-9]+)\>\]')
                                li = pattern_bfrange1.findall(k)
                                if len(li) != 0:
                                    for h in li:
                                        if h[0] == h[1]:
                                            pdf_code = h[0].upper()
                                            uni_code = h[2]
                                            CMap_data[pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                        else:
                                            pdf_code = h[0].upper()
                                            uni_code = h[2]
                                            CMap_data[pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                            pdf_code = h[1].upper()
                                            CMap_data[pdf_code.decode().upper()] = chr(int(uni_code, 16)+1)
                                    cnt+=1
                                #b'<0396> <0397> [<B05D> <B07C>]'
                                #b'<0478> <047A> [<B418> <B41C> <B420>]'
                                if cnt == 0:
                                    noBrace = k.split(b"[")[0]
                                    yesBrace = k.split(b"[")[1]
                                    noBrace = noBrace.split(b"<")
                                    yesBrace = yesBrace.split(b"<")
                                    if len(noBrace) == len(yesBrace):
                                        for u in range(1, len(noBrace)):
                                            pdf_code = noBrace[u][0:4].upper()
                                            uni_code = yesBrace[u][0:4]
                                            CMap_data[pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                    else:
                                        num = int(noBrace[2][0:4], 16)-int(noBrace[1][0:4], 16)
                                        pdf_code = noBrace[1][0:4].decode().upper()
                                        for u in range(0, num+1):
                                            uni_code = yesBrace[u+1][0:4]
                                            CMap_data[pdf_code.upper()] = chr(int(uni_code, 16))
                                            pdf_code = format(int(pdf_code, 16) + 1, "04X")
                                            if len(pdf_code) == 6:
                                                pdf_code = pdf_code.replace("0X","").upper()
                                            elif len(pdf_code) == 5:
                                                pdf_code = pdf_code.replace("X","").upper()
                font_CidUnicode[name] = CMap_data
    return font_CidUnicode

def parse_CMap_p(decompressObj, pdf):
    font_CidUnicode = {} #output : {fontname : {CID : unicode}}
    eng_table = pd.read_csv(os.path.dirname(os.path.realpath(__file__))+"\\eng_mapping_table.csv", header = None, names = ['cid', 'char', 'nothing'])
    eng_table = eng_table.drop('nothing', axis='columns')
    eng_cmap = {}
    for i in range(52):
        eng_cmap[eng_table['cid'][i]] = eng_table['char'][i]

    uni2_table = pd.read_csv(os.path.dirname(os.path.realpath(__file__))+"\\uni2_table.csv", header = None, names = ['cid', 'char'])
    uni2_cmap = {}
    for i in range(len(uni2_table)):
        uni2_cmap[uni2_table['cid'][i]] = uni2_table['char'][i]
    CharStream = re.compile(rb'beginbfchar([\s\S]*?)endbfchar') #one
    RangeStream = re.compile(rb'beginbfrange([\s\S]*?)endbfrange') #range
    RangeStream2 = re.compile(rb'begincidrange([\s\S]*?)endcidrange') #range2 #알PDF의 경우 추가    
    for pidx in pdf['FontCMap']:
        font_CidUnicode[pidx] = {}
        font_CidUnicode[pidx][b'eng'] = eng_cmap
        font_CidUnicode[pidx][b'uni2'] = uni2_cmap
        for font, num in pdf['FontCMap'][pidx].items():
            if type(num) == int:
                c = decompressObj[num][2]
                if re.search(rb'\/Encoding\s\/MacRomanEncoding', c) != None:
                    MacRoman = pd.read_csv(os.path.dirname(os.path.realpath(__file__))+"\\Mac_Roman_character.csv", header = None, names = ['code', 'mean', 'nothing'])
                    MacRoman = MacRoman.drop('nothing', axis='columns')
                    CidUnicode = {}
                    #fontCmap_dict2에 저장함
                    for i in range(0, 255):
                        CidUnicode[MacRoman['code'][i]] = chr(MacRoman['mean'][i])
                    font_CidUnicode[pidx][font] = CidUnicode
                    continue

            if pdf['FontCMap'][pidx][font] == b'Type1':
                font_CidUnicode[pidx][font] = {"__Type1__": True}
                continue
            
            for i in range(len(decompressObj)):
                if decompressObj[i][0] == num:
                    font_CidUnicode[pidx][font] = {}
                    CMap_data = {}
                    c = decompressObj[i][2] 
                    
                    repl = CharStream.findall(c)
                    for j in repl:
                        pattern_bfchar = re.compile(rb'<([A-Fa-f0-9]+)>\s*<([A-Fa-f0-9]+)>')
                        li = pattern_bfchar.findall(j)
                        for h in li: 
                            pdf_code = h[0].upper()
                            uni_code = h[1]
                            if len(uni_code) > 4:
                                uni_code = uni_code[-4:]
                            font_CidUnicode[pidx][font][pdf_code.decode().upper()] = chr(int(uni_code, 16))

                    repl = RangeStream.findall(c)
                    if len(repl) != 0:
                        for j in repl:
                            for k in j.split(b'\n'):
                                cnt = 0
                                if len(k) == 0:
                                    continue
                                #<0496> <0497> <B4DC>
                                #<07C7> <07C9> <C548> -> <07C7> <C548> / <07C8> <C549> / <07C9> <C550>
                                pattern_bfrange3 = re.compile(rb'\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>')
                                li = pattern_bfrange3.findall(k)
                                if not(b'[' in k) and len(li) != 0:
                                    num = int(li[0][1], 16) - int(li[0][0], 16)
                                    pdf_code = li[0][0]
                                    uni_code = li[0][2]
                                    font_CidUnicode[pidx][font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                    for h in range(0, num):
                                        uni_code = str(hex(int(uni_code, 16)+1))
                                        if len(uni_code) == 6:
                                            uni_code = uni_code.replace("0X","")
                                        elif len(uni_code) == 5:
                                            uni_code = uni_code.replace("X","")
                                        if len(pdf_code) == 4:
                                            pdf_code = format(int(pdf_code, 16)+1, '04x')
                                        elif len(pdf_code) == 2: #알PDF, mac의 경우 2자리로 출력
                                            pdf_code = format(int(pdf_code, 16)+1, '02x')
                                        font_CidUnicode[pidx][font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                    cnt+=1
                                else:
                                    #<058B> <058B> [<B9DB>]
                                    pattern_bfrange1 = re.compile(rb'\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>\s*\[\<([A-Fa-f0-9]+)\>\]')
                                    li = pattern_bfrange1.findall(k)
                                    if len(li) != 0:
                                        for h in li:
                                            if h[0] == h[1]:
                                                pdf_code = h[0].upper()
                                                uni_code = h[2]
                                                font_CidUnicode[pidx][font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                            else:
                                                pdf_code = h[0].upper()
                                                uni_code = h[2]
                                                font_CidUnicode[pidx][font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                                pdf_code = h[1].upper()
                                                font_CidUnicode[pidx][font][pdf_code.decode().upper()] = chr(int(uni_code, 16)+1)
                                        cnt+=1
                                    #b'<0396> <0397> [<B05D> <B07C>]'
                                    #b'<0478> <047A> [<B418> <B41C> <B420>]'
                                    if cnt == 0:
                                        noBrace = k.split(b"[")[0]
                                        yesBrace = k.split(b"[")[1]
                                        noBrace = noBrace.split(b"<")
                                        yesBrace = yesBrace.split(b"<")
                                        if len(noBrace) == len(yesBrace):
                                            for u in range(1, len(noBrace)):
                                                pdf_code = noBrace[u][0:4].upper()
                                                uni_code = yesBrace[u][0:4]
                                                font_CidUnicode[pidx][font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                        else:
                                            num = int(noBrace[2][0:4], 16)-int(noBrace[1][0:4], 16)
                                            pdf_code = noBrace[1][0:4].decode()
                                            for u in range(0, num+1):
                                                uni_code = yesBrace[u+1][0:4]
                                                font_CidUnicode[pidx][font][pdf_code.upper()] = chr(int(uni_code, 16))
                                                pdf_code = str(hex(int(pdf_code, 16)+1)).upper()
                                                if len(pdf_code) == 6:
                                                    pdf_code = pdf_code.replace("0X","").upper()
                                                elif len(pdf_code) == 5:
                                                    pdf_code = pdf_code.replace("X","").upper()                    

                    repl = RangeStream2.findall(c) #range2
                    if len(repl) != 0:
                        for j in repl:
                            for k in j.split(b'\n'):
                                cnt = 0
                                if len(k) == 0:
                                    continue
                                #<8000><80ff>256 -> <8000><0100> / <8001><0101> /.../ <80ff><01FF>
                                pattern_cidrange = re.compile(rb'\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>\s*([A-Fa-f0-9]+)')
                                li = pattern_cidrange.findall(k)
                                if not (b'[' in k) and len(li) != 0:
                                    start_code = li[0][0]  # 예: b'8000'
                                    end_code   = li[0][1]  # 예: b'80ff'
                                    base_code  = li[0][2]  # 예: b'0100' (또는 b'256' 등)

                                    cidnum = int(end_code, 16) - int(start_code, 16)
                                    
                                    pdf_code = start_code
                                    uni_code = base_code
                                    font_CidUnicode[font][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                    
                                    for _ in range(cidnum):
                                        pdf_code_val = int(pdf_code, 16) + 1
                                        uni_code_val = int(uni_code, 16) + 1
                                        pdf_code = format(pdf_code_val, '04x').encode()   # b'8001', b'8002' ...
                                        uni_code = format(uni_code_val, '04x').encode()   # b'0101', b'0102' ...
                                        
                                        font_CidUnicode[pidx][font][pdf_code.decode().upper()] = chr(int(uni_code, 16))

        # ✅ pidx 없이 전역적으로 존재하는 CMap 객체 처리
    if 'CMap' in pdf:
        for idx, cmap_obj_idx in enumerate(pdf['CMap']):
            key = f"Random{idx}".encode()
            font_CidUnicode[key] = {}

            c = decompressObj[cmap_obj_idx][2]
            CMap_data = {}

            # bfchar 처리
            repl = CharStream.findall(c)
            for j in repl:
                pattern_bfchar = re.compile(rb'<([A-Fa-f0-9]+)>\s*<([A-Fa-f0-9]+)>')
                li = pattern_bfchar.findall(j)
                for h in li: 
                    pdf_code = h[0].upper()
                    uni_code = h[1]
                    if len(uni_code) > 4:
                        uni_code = uni_code[-4:]
                    font_CidUnicode[key][pdf_code.decode().upper()] = chr(int(uni_code, 16))

            # bfrange 처리
            repl = RangeStream.findall(c)
            if len(repl) != 0:
                for j in repl:
                    for k in j.split(b'\n'):
                        cnt = 0
                        if len(k) == 0:
                            continue
                        pattern_bfrange3 = re.compile(rb'\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>')
                        li = pattern_bfrange3.findall(k)
                        if not(b'[' in k) and len(li) != 0:
                            num = int(li[0][1], 16) - int(li[0][0], 16)
                            pdf_code = li[0][0]
                            uni_code = li[0][2]
                            font_CidUnicode[key][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                            for h in range(0, num):
                                uni_code = str(hex(int(uni_code, 16)+1))
                                uni_code = uni_code.replace("0X","").zfill(4).upper()
                                pdf_code = format(int(pdf_code, 16)+1, '04x')
                                font_CidUnicode[key][pdf_code.upper()] = chr(int(uni_code, 16))
                            cnt += 1
                        # 배열형 bfrange도 처리 (생략 가능)

            # begincidrange 처리
            repl = RangeStream2.findall(c)
            if len(repl) != 0:
                for j in repl:
                    for k in j.split(b'\n'):
                        if len(k) == 0:
                            continue
                        pattern_cidrange = re.compile(rb'\<([A-Fa-f0-9]+)\>\s*\<([A-Fa-f0-9]+)\>\s*([A-Fa-f0-9]+)')
                        li = pattern_cidrange.findall(k)
                        if not (b'[' in k) and len(li) != 0:
                            start_code = li[0][0]
                            end_code   = li[0][1]
                            base_code  = li[0][2]
                            cidnum = int(end_code, 16) - int(start_code, 16)

                            pdf_code = start_code
                            uni_code = base_code
                            font_CidUnicode[key][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                            
                            for _ in range(cidnum):
                                pdf_code_val = int(pdf_code, 16) + 1
                                uni_code_val = int(uni_code, 16) + 1
                                pdf_code = format(pdf_code_val, '04x').encode()
                                uni_code = format(uni_code_val, '04x').encode()
                                font_CidUnicode[key][pdf_code.decode().upper()] = chr(int(uni_code, 16))
                                    
    return font_CidUnicode

def extract_font_tag_to_realname(decompressObj_checked, pdf):
    """
    Extract mapping from font tags (e.g., F1, F2) to actual BaseFont names,
    using /Resources -> /Font << /F1 5 0 R ... >> found in pdf['Resources'] objects only.
    Result is stored in pdf['FontNameMap']
    """
    import re

    font_tag_pattern = re.compile(rb'/([A-Z]+\d+)\s+\d+\.?\d*\s+Tf')     # /F1 12 Tf
    resources_font_dict_pattern = re.compile(rb'/Font\s*<<?(.*?)>>', re.S)  # /Font<</F1 5 0 R ... >>
    font_entry_pattern = re.compile(rb'/([A-Z]+\d+)\s+(\d+)\s+0\s+R')    # /F1 5 0 R
    basefont_pattern = re.compile(rb'/BaseFont\s*/([A-Za-z0-9\+]+)')     # /BaseFont /AAAAAA+Gungsuh

    font_name_map = {}

    # 1. 모든 content stream에서 사용된 font tags 수집
    used_tags = set()
    for content_idx in pdf.get('Content', []):
        content_stream = decompressObj_checked[content_idx][2]
        font_tags = font_tag_pattern.findall(content_stream)
        used_tags.update(tag.decode() for tag in font_tags)

    # 2. Resource object 내 Font dictionary 추출
    tag_to_objnum = {}
    for res_idx in pdf.get('Resources', []):
        resource_data = decompressObj_checked[res_idx][2]
        match = resources_font_dict_pattern.search(resource_data)
        if not match:
            continue

        font_dict_raw = match.group(1)
        for tag, objnum in font_entry_pattern.findall(font_dict_raw):
            tag_str = tag.decode()
            objnum_str = objnum.decode()
            if tag_str in used_tags and tag_str not in tag_to_objnum:
                tag_to_objnum[tag_str] = objnum_str

    # 3. Font object에서 BaseFont 추출
    for tag_str, ref_objnum in tag_to_objnum.items():
        for obj in decompressObj_checked:
            if obj[0].decode() == ref_objnum:
                font_obj_data = obj[2]
                basefont_match = basefont_pattern.search(font_obj_data)
                if basefont_match:
                    basefont = basefont_match.group(1).decode('utf-8')
                    if '+' in basefont:
                        basefont = basefont.split('+')[1]  # subset 제거
                    font_name_map[tag_str] = basefont
                break

    # 결과 저장
    pdf['FontNameMap'] = font_name_map

def decode_bytes_dict(obj):
    if isinstance(obj, dict):
        return {k.decode() if isinstance(k, bytes) else k:
                decode_bytes_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decode_bytes_dict(i) for i in obj]
    elif isinstance(obj, bytes):
        return obj.decode(errors="replace")
    else:
        return obj

#[Main]
def Parsing(decompressObj, pdf):
    objlist = CheckEssential(decompressObj, pdf)
    if pdf['SaveMethod'] == "Unknown":
        c_savemethod_classify(decompressObj, pdf)
    font_change = font_change_check(decompressObj, pdf)
    if font_change == True:
        parse_content_page(decompressObj, pdf, objlist)
        parse_FontName_p(decompressObj, pdf)
        parse_FontName_pidx(decompressObj, pdf)
        pdf['FontCMap'] = parse_CMap_p(decompressObj, pdf)
    else:
        parse_FontName(decompressObj, pdf)
        pdf['FontCMap'] = parse_CMap(decompressObj, pdf)
    extract_font_tag_to_realname(decompressObj, pdf)
>>>>>>> 77c3de1 (Code Upload)
    return pdf