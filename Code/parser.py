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
    return pdf