import re
import os
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path

def CMap_Error(font_CidUnicode, CID1, data):
        past_length = len(data)
        for i in font_CidUnicode.keys():
            if i[0:6] == b'Random':  # Mapping CID1 with Ramdom#
                if CID1 in font_CidUnicode[i].keys():
                    if isinstance(data, list):
                        data.append(font_CidUnicode[i][CID1])
                        return data

                    elif isinstance(data, str):
                        data = data + font_CidUnicode[i][CID1]
                    break
                else:
                    #Check if CID1 is a valid hexadecimal value
                    try:
                        cid_value = int(CID1, 16)
                        if cid_value in range(24, 94):
                            if CID1 in font_CidUnicode['eng'].keys():
                                if isinstance(data, list):
                                    data.append(font_CidUnicode['eng'][CID1])
                                    return data

                                elif isinstance(data, str):
                                    data = data + font_CidUnicode['eng'][CID1]
                    except ValueError:
                        print(f"Invalid CID1 value: {CID1}")
                        if isinstance(data, list):
                            data.append(f"Invalid_CID_{CID1}")
                            return data

                        elif isinstance(data, str):
                            data = data + f"Invalid_CID_{CID1}"
        for i in font_CidUnicode.keys(): #Not mapping CID1 with Random#
            if i[0:6] != b'Random':  # 랜덤이랑 매핑X
                if CID1 in font_CidUnicode[i].keys():
                    if isinstance(data, list):
                        data.append(font_CidUnicode[i][CID1])
                        return data

                    elif isinstance(data, str):
                        data = data + font_CidUnicode[i][CID1]
                    break
        now_length = len(data)
        if past_length == now_length: 
            try:
                if isinstance(CID1, int):  # Process only if CID1 is a number
                    if isinstance(data, list):
                        data.append("Cid_" + format(CID1, '02x'))
                        return data
                    elif isinstance(data, str):
                        data = data + "Cid_" + format(CID1, '02x')
                else:
                    if isinstance(data, list):
                        data.append(f"Cid_{CID1}")
                        return data

                    elif isinstance(data, str):
                        data = data + f"Cid_{CID1}"
            except Exception as e:
                print(f"Error formatting CID: {e}")

        return data

#Visualization -> Need Modification.
def print_to_png(data, pdf, cnt):
    result_path = os.path.dirname(os.path.realpath(__file__))+"\\export"+"\\"+pdf['Title']+"\\"
    fig, ax = plt.subplots(figsize=(9, 12)) #A4 size
    ax.set_xlim(-100, 700)
    ax.set_ylim(-900, 100)

    verts = []
    codes = []

    q_index = []

    # Initialize starting point
    start_x, start_y = 0, 0

    max_y = 0
    next_line = 0
    y_length = 0
    try:
        if b"\\n" in data:
            for idx, sent in enumerate(data.split(b"\\n")):
                j = sent.strip().split()
                j = [v for v in j if v]
                if idx == 0:
                    max_y = float(j[1]) #Max Y-axis length.
                    next_line = float(j[0]) #Current X-axis position.
                if len(j) <= 1: #q, h, ...
                    if j:
                        if j[0] == b'q':
                            y_length += max_y
                            final = True
                            q_index.append(idx)
                    continue
                elif len(j)>1:
                    cmd = j[-1]
                    try:
                        if j[-1] not in [b'm', b'l', b'c', b'q']:
                            continue
                        if max_y-float(j[1])>=0:
                            max_y = float(j[1])
                        if next_line-float(j[0])>=0:
                            next_line = float(j[0])
                            y_length += max_y
                            max_y = 0
                        if cmd == b"m": # move
                            params = list(map(float, j[:-1]))
                            start_x, start_y = params
                            start_y += y_length
                            verts.append((start_x, start_y))
                            codes.append(Path.MOVETO)
                        elif cmd == b'l': #line
                            params = list(map(float, j[:-1]))
                            x, y = params
                            y = y+y_length
                            verts.append((x, y))
                            codes.append(Path.LINETO)
                        elif cmd == b'c': #curve
                            params = list(map(float, j[:-1]))
                            x1, y1, x2, y2, x3, y3 = params
                            y1 = y1+y_length
                            y2 = y2+y_length
                            y3 = y3+y_length
                            verts.extend([(x1, y1), (x2, y2), (x3, y3)])
                            codes.extend([Path.CURVE4] * 3)
                        elif j[-1] == b'cm':
                            verts.append((start_x, start_y))
                            codes.append(Path.CLOSEPOLY)
                    except ValueError:
                        continue
        else:
            for idx, sent in enumerate(data.split(b"\n")):
                j = sent.strip().split()
                j = [v for v in j if v]
                if idx == 0:
                    max_y = float(j[1]) #Max Y-axis length.
                    next_line = float(j[0]) #Current X-axis position.
                if len(j) <= 1: #q, h, ...
                    if j:
                        if j[0] == b'q':
                            y_length += max_y
                            final = True
                    continue
                elif len(j)>1:
                    cmd = j[-1]
                    try:
                        if j[-1] not in [b'm', b'l', b'c', b'h']:
                            continue
                        if max_y-float(j[1])>0:
                            max_y = float(j[1])
                        if next_line-float(j[0])>0:
                            next_line = float(j[0])
                            y_length += max_y
                            max_y = 0
                        if cmd == b"m": # move
                            params = list(map(float, j[:-1]))
                            start_x, start_y = params
                            start_y += y_length
                            verts.append((start_x, start_y))
                            codes.append(Path.MOVETO)
                        elif cmd == b'l': #line
                            params = list(map(float, j[:-1]))
                            x, y = params
                            y = y+y_length
                            verts.append((x, y))
                            codes.append(Path.LINETO)
                        elif cmd == b'c': #curve
                            params = list(map(float, j[:-1]))
                            x1, y1, x2, y2, x3, y3 = params
                            y1 = y1+y_length
                            y2 = y2+y_length
                            y3 = y3+y_length
                            verts.extend([(x1, y1), (x2, y2), (x3, y3)])
                            codes.extend([Path.CURVE4] * 3)
                        elif cmd == b'h':
                            final = True
                        elif j[-1] == b'cm':
                            verts.append((start_x, start_y))
                            codes.append(Path.CLOSEPOLY)
                    except ValueError:
                        continue
        path = Path(verts, codes)
        patch = PathPatch(path, facecolor='none', lw=1)

        ax.add_patch(patch)

        #Draw points and lines.
        for vert in verts:
            ax.plot(vert[0], vert[1], 'k-')

        #Display the graph.
        ax.set_aspect('equal', 'datalim')
        ax.invert_yaxis()
        plt.grid(True)
        plt.savefig(result_path+"Content"+str(cnt)+".png")
        print("Content image : "+result_path+"Content"+str(cnt)+".png")
        plt.close(fig)
    except:
        plt.close(fig)
        return

def MappingText(decompressObj, pdf):
    print("Performing text mapping...")
    font_CidUnicode = pdf['FontCMap']
    content = '' 
    idx = 0
    for i in pdf['Content']: #Mapping per page
        c = decompressObj[i][2] # Content data
        idx+=1
        s1, s2 = [], []
        font = []
        Page_content = ""
        other = re.search(rb'\<([A-Fa-f0-9\\n]+\s*)\>', c) #format <0000>
        alpdf = re.search(rb'\(([^)]*)\)', c) #format (/00)
        mac = re.search(rb'\([!@#$%^&*()_+-={}\[\]:;"\'<>,.?/\\\|0-9A-z]*\s*\)', c) #format (?!@)
        data =  ''
        if other != None or (pdf['SaveMethod'] != "알PDF" and pdf['SaveMethod'] != "MAC"):
            stream = re.compile(rb'\<([A-Fa-f0-9\\n]+\s*)\>') #format <0000>
            stream2 = re.compile(rb'\([]\\\\().\?\,!\^\$\|\*\+\/]*[0-9]*\s*\)') #Only whitespace and numeric characters.
            stream3 = re.compile(rb'\/([A-Z]+[0-9]+)') #Font name
            stream4 = re.compile(rb'Lang\s\([^\s]+\)')#forma 'lang () '
            stream5 = re.compile(rb'\((.*?)\)')
            
            if len(stream4.findall(c)) != 0 :
                langlist = c.split(rb'Lang')
                for lang in langlist: 
                    data = []
                    notSmall = stream.findall(lang) #0000 or 00001111
                    if len(notSmall) == 0:  #en-US ver.
                        yesSmall = stream5.findall(lang[5:])
                        data = b"".join(yesSmall).decode()
                        if '\\(' in data:
                            data = data.replace('\\(', "(")
                        if '\\)' in data:
                            data = data.replace('\\)', ")")
                        if '\\[' in data:
                            data = data.replace('\\[', "[")
                        if '\\]' in data:
                            data = data.replace('\\]', "]")
                        if '\\' in data:
                            data = data.replace('\\', ")")
                        Page_content = Page_content+ "".join(data)
                    else : #ko-KR ver.
                        if len(stream3.findall(lang)) != 0:
                            Current_F = stream3.findall(lang)[0]
                            CID1 = ''
                            text = b"".join(notSmall).upper()
                            start, end = 0, 4
                            while end <= len(text):
                                if b"\n" in text[start:end]:
                                    data.append("\n") # 00\n
                                    if end+1 < len(text):
                                        p = re.compile(b'\n', re.S)
                                        m = p.search(text[start:end])
                                        if m.start() != start:
                                            try:
                                                uptext = text[start:start+m.start()]
                                                downtext = text[start+m.end():end+1]
                                                CID1 = (uptext+downtext).decode()
                                                start = end+1
                                                end +=5
                                                data.append(font_CidUnicode[Current_F][CID1])
                                            except KeyError:
                                                data = CMap_Error(font_CidUnicode, CID1, data)
                                        else:
                                            try:
                                                CID1 = text[start+1:end+1].decode()
                                                end+=5
                                                start+=5
                                                data.append(font_CidUnicode[Current_F][CID1])
                                            except KeyError:
                                                data = CMap_Error(font_CidUnicode, CID1, data)
                                else:
                                    try:
                                        CID1 = text[start:end].decode()
                                        end+=4
                                        start+=4
                                        data.append(font_CidUnicode[Current_F][CID1])  
                                    except KeyError:
                                        data = CMap_Error(font_CidUnicode, CID1, data)
                            Page_content = Page_content+ "".join(data)
                            data = []

                Page_content = Page_content+ "".join(data)


            else: #No 'Lang'
                for i in stream.finditer(c): #Character
                    s1.append(i)
                for i in stream2.finditer(c): #whitespace or Non-alphanumeric characters
                    s2.append(i)
                for i in stream3.finditer(c): #Font name
                    font.append(i)
                if len(stream4.findall(c)) != 0 :
                    for i in stream4.finditer(c):
                        lang.append(i)
                else:
                    pass                    

                #CID Mapping
                cntS1, cntS2 = len(s1), len(s2)
                l, k= 0, 0
                cntF = len(font)
                StartF = 0
                while cntS1  != 0 or cntS2 != 0:
                    data = []
                    while cntF != 0:
                        if cntS1 == 0 and cntS2 == 0:
                            break
                        if cntS1 == 0:
                            StartS1 = 999999
                        else:
                            StartS1 = s1[l].start()
                        if cntS2 == 0:
                            StartS2 = 999999
                        else:
                            StartS2 = s2[k].start()
                        Current_F = font[StartF].start()
                        if cntF <= 1:
                            Next_F = min(StartS2,StartS2)+3
                        else:
                            Next_F  = font[StartF+1].start()
                        CID1 = ''
                        if StartS1 < StartS2: #Prioritize text data.
                            if Current_F < StartS1: 
                                if Next_F > StartS1: #Compare font positions.
                                    FontNow = font[StartF].group().split(b' ')[0][1:]
                                    text = s1[l].group()
                                    text = text[1:-1].upper()
                                    start, end = 0, 4
                                    while end <= len(text):
                                        if b"\n" in text[start:end]:
                                            data.append("\n") # 00\n
                                            if end+1 < len(text):
                                                p = re.compile(b'\n', re.S)
                                                m = p.search(text[start:end])
                                                if m.start() != start: 
                                                    try:
                                                        uptext = text[start:start+m.start()]
                                                        downtext = text[start+m.end():end+1]
                                                        CID1 = (uptext+downtext).decode()
                                                        start = end+1
                                                        end +=5
                                                        data.append(font_CidUnicode[FontNow][CID1])
                                                    except KeyError:
                                                        data = CMap_Error(font_CidUnicode, CID1, data)
                                                else:
                                                    try:
                                                        CID1 = text[start+1:end+1].decode()
                                                        end+=5
                                                        start+=5
                                                        data.append(font_CidUnicode[FontNow][CID1])
                                                    except KeyError:
                                                        data = CMap_Error(font_CidUnicode, CID1, data)
                                        else:
                                            try:
                                                CID1 = text[start:end].decode()
                                                end+=4
                                                start+=4
                                                data.append(font_CidUnicode[FontNow][CID1])  
                                            except KeyError:
                                                data = CMap_Error(font_CidUnicode, CID1, data)
                                    cntS1-=1
                                    l+=1
                                    Page_content = Page_content+"".join(data)
                                    data = []
                                else:
                                    cntF -=1
                                    StartF+=1
                        else: #Whitespace and numeric data come first.
                            if Current_F < StartS2:
                                if Next_F > StartS2: 
                                    text = s2[k].group()
                                    if b'\\(' in text:
                                        text = text.replace(b'\\(', b"(")
                                    elif b'\\)' in text:
                                        text = text.replace(b'\\)', b")")
                                    elif b'\\[' in text:
                                        text = text.replace(b'\\[', b"[")
                                    elif b'\\]' in text:
                                        text = text.replace(b'\\]', b"]")
                                    
                                    text = text[1:-1]
                                    text = text.decode()
                                    data.append(text)
                                    cntS2-=1
                                    k+=1
                                    Page_content = Page_content+"".join(data)
                                    data = []
                                else:
                                    cntF -=1
                                    StartF+=1
                                    continue
                    if cntF == 0 and len(data) == 0:
                        if cntS1 == 0 or cntS2 == 0:
                            break
                        text = s1[l].group()
                        text = text[1:-1].upper()
                        start, end = 0, 4
                        if len(text)>end:
                            while end <= len(text):
                                if b"\n" in text[start:end]:
                                    data.append("\n") # 00\n
                                    if end+1 < len(text):
                                        p = re.compile(b'\n', re.S)
                                        m = p.search(text[start:end])
                                        if m.start() != start: ###무한루프
                                            uptext = text[start:start+m.start()]
                                            downtext = text[start+m.end():end+1]
                                            CID1 = (uptext+downtext).decode()
                                            start = end+1
                                            end +=5
                                            data = CMap_Error(font_CidUnicode, CID1, data)
                                        else:
                                            CID1 = text[start+1:end+1].decode()
                                            end+=5
                                            start+=5
                                            data = CMap_Error(font_CidUnicode, CID1, data)
                                else:
                                    CID1 = text[start:end].decode()
                                    end+=4
                                    start+=4
                                    data = CMap_Error(font_CidUnicode, CID1, data)    
                        else:
                            data.append(text.decode())
                        cntS1-=1
                        l+=1
                        Page_content = Page_content+"".join(data)
                        data = []
                    else:
                        cntF -=1
                        StartF+=1
            Page_content = Page_content+"".join(data)
        elif alpdf != None and not(b"!" in alpdf.group()): #AlPDF
            c = decompressObj[i][2]
            stream = re.compile(rb'\(([^\)]*\)*)\)', re.S)
            s=[]
            for i in stream.finditer(c):#CID
                s.append(i)
            Font = []
            ContentCid = [] 
            stream2 = re.compile(rb'\/([A-Z]+[0-9]+)\s')
            Current_F = ''
            for j in stream2.finditer(c): #Font
                Font.append(j)
            for h in s: #One page
                if pdf['CMap'] != []:
                    nowIdx = 0 
                    rest = len(Font)
                    while rest >=1:
                        if nowIdx == len(Font)-1:
                            Current_F = Font[nowIdx].group().split(b' ')[0][1:]
                            break
                        else:
                            if Font[nowIdx+1].start() > h.start():
                                Current_F = Font[nowIdx].group().split(b' ')[0][1:]
                                break
                            else:
                                rest-=1
                                nowIdx+=1
                    num = 0
                    text = str(h.group())[3:-2]
                    while num < len(text):
                        if text[num] == "\\":
                            try:
                                if text[num+1] == "x":  
                                    ContentCid.append(text[num+2:num+4])  # \\x07 -> 07
                                    num += 4
                                elif text[num+1] == 't':
                                    ContentCid.append(format(ord("\t"), '02x'))
                                    num += 2
                                elif text[num+1] == 'r':
                                    ContentCid.append(format(ord("\r"), '02x'))
                                    num += 2
                                elif text[num+1] == 'n':
                                    ContentCid.append(format(ord("\n"), '02x'))
                                    num += 2
                                elif text[num+1] == 'b':
                                    ContentCid.append(format(ord("\b"), '02x'))
                                    num += 2
                                elif text[num+1] == 'f':
                                    ContentCid.append(format(ord("\f"), '02x'))
                                    num += 2
                                elif text[num+1] == '\\':
                                    ContentCid.append(format(ord("\\"), '02x'))
                                    num += 2
                                elif text[num+1] == ')':
                                    ContentCid.append(format(ord(")"), '02x'))
                                    num += 2
                                elif text[num+1] == '(':
                                    ContentCid.append(format(ord("("), '02x'))
                                    num += 2
                                else:
                                    ContentCid.append(text[num+2:num+4])
                                    num += 4
                            except IndexError:
                                num += 2
                        else:  # H -> ord(H)
                            ContentCid.append(format(ord(text[num]), '02x'))
                            num += 1

                        # CID1 Processing: Ensure ContentCid is not empty
                        if len(ContentCid) == 2:
                            CID1 = (ContentCid[0] + ContentCid[1]).upper()
                            if Current_F not in font_CidUnicode.keys():  # If not found, map to random data
                                Page_content = CMap_Error(font_CidUnicode, CID1, Page_content)
                            else:
                                Page_content = Page_content + font_CidUnicode[Current_F][CID1]
                            ContentCid = []
                        elif len(ContentCid) < 2 and len(text) <= num:
                            if len(ContentCid) > 0:  # Process only if ContentCid is not empty
                                CID1 = ContentCid[0].upper()
                                try:
                                    Page_content = Page_content + font_CidUnicode[Current_F][CID1]
                                except KeyError:
                                    Page_content = CMap_Error(font_CidUnicode, CID1, Page_content)
                                ContentCid = []

                    if len(ContentCid) > 2:
                        if text != b'(en-US)':
                            try:
                                Page_content = Page_content + text
                            except UnicodeDecodeError:
                                pass
                    else:  # if not found CMap
                        if h.group() != b'(en-US)':
                            try:
                                Page_content = Page_content + h.group()[1:-1].decode()
                            except UnicodeDecodeError:
                                pass

        elif mac != None: #mac
            mac_content = []
            mac_font = []
            stream = re.compile(rb'\(([!@#$%^&*()_+-={}\[\]:;"\'<>,.?/\\\|0-9A-z]*\s*)\)', re.S)
            stream2 = re.compile(rb'\/([A-Z]+[0-9]+)\s\d', re.S) #Font name
            for h in stream.finditer(c):
                mac_content.append(h)
            for h in stream2.finditer(c):
                mac_font.append(h)
            
            mf = 0
            mc = 0
            len_F = len(mac_font)-1
            len_C = len(mac_content)
            while len_C > 0:
                if len_F != -1:
                    while len_F > -1:
                        start = mac_font[mf].start()
                        if mf == len(mac_font)-1:
                            next = 99999
                        else:
                            next = mac_font[mf+1].start()
                        if start < mac_content[mc].start():
                            if next > mac_content[mc].start(): #start = current font
                                Current_F = mac_font[mf].group()
                                Current_F = Current_F.replace(b"\n",b" ").split(b' ')[0][1:]
                                data = mac_content[mc].group()[1:-1] #remove brackets
                                data = data.replace(b"\\x",b"")
                                data = data.replace(b"\\",b"")
                                for cids in data:
                                    try:
                                        if cids == 32:
                                            Page_content = Page_content + " "
                                        else:
                                            CID1 = format(cids,'02x')
                                            Page_content = Page_content + font_CidUnicode[Current_F][CID1]
                                    except:
                                        Page_content = Page_content + "Cid_"+format(cids,'02x')
                                mc+=1
                                len_C-=1
                                if len_C == 0:
                                    break
                            else:
                                mf+=1
                                len_F-=1
                        else:
                            mf+=1
                            len_F-=1
                else:
                    for k in mac_content:
                        data = k.group()[1:-1] #remove brackets
                        data = data.replace(b"\\x",b"")
                        data = data.replace(b"\\",b"")
                        if len(data) != 0:
                            for cids in data:
                                try:
                                    if cids == 32:
                                        Page_content = Page_content + " "
                                    else:
                                        CID1 = format(cids,'02x')
                                        Page_content = Page_content + font_CidUnicode[Current_F][CID1]
                                except: #If CMap is missing and causes a font error, store it in the form of Cid_2e.
                                    Page_content = Page_content + "Cid_"+format(cids,'02x')
                        else:
                            len_C -=1
                            break
        print_to_png(c, pdf, idx)
        content = content+ Page_content
    pdf['Text'] = content
    return pdf
