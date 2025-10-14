<<<<<<< HEAD
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
=======
import re
import os
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from llmquery import query_ollama
import sqlite3
from time import time
from datetime import datetime, timezone, timedelta

import cmap_error_S
import cmap_error_P

class RetryFontMappingException(Exception):
    def __init__(self, font, excluded_fonts):
        self.font = font
        self.excluded_fonts = excluded_fonts
        super().__init__(f"Retry font mapping for {font}")

def Error_main_S(c, pdf):
    result = []
    font_cid_map = clist_integrate(c)  # (b'F1', [...]) 또는 일반 문자열 포함
    font_CidUnicode = pdf['FontCMap']

    for item in font_cid_map:
        # ✅ (b'F1', [...]) 형태인지 확인
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], bytes) and isinstance(item[1], list):
            font, cids = item

            # CMap이 없는 경우 → cmap_total_damage
            if font not in font_CidUnicode:
                print(f"[ERROR: MissingCMap] font: {font}")
                mapped = cmap_error_S.cmap_total_damage(font, cids, pdf)
                if isinstance(mapped, list):
                    mapped = ''.join(mapped)
                result.append(mapped)
            else:
                # ✅ 폰트는 있으나 개별 CID 확인
                mapped_text = []
                for cid in cids:
                    try:
                        if cid not in font_CidUnicode[font]:
                            print(f"[ERROR: MissingCID] font: {font}, cid: {cid}")
                            mapped, return_flag = cmap_error_S.cmap_part_damage(font, cid, pdf)
                            if mapped is not None:
                                mapped_text.append(mapped)
                                if return_flag:
                                    raise RetryFontMappingException(font, pdf['dbmapresult']['exclude'].get(font, []))
                            else:
                                mapped_text.append(f"[{font.decode()}:Cid_{cid}]")
                        else:
                            mapped_text.append(font_CidUnicode[font][cid])
                    except KeyError:
                        print(f"[ERROR: MissingCMapAccess] font: {font}, cid: {cid}")
                        mapped_text.append(f"[{font}:Cid_{cid}]")

                result.append(''.join(mapped_text))

        else:
            # ✅ tuple이 아니면 그대로 추가
            result.append(item)

    return ''.join(result)

def Error_main_P(c, pdf, pidx):
    result = []
    font_cid_map = clist_integrate(c)
    dbmapresult = pdf.setdefault('dbmapresult', {})
    exclude_map = dbmapresult.setdefault('exclude', {})
    forced_marker_fonts = set()

    # 1. content에 pidx가 부여되어 있고 & FontCMap에도 해당 pidx가 존재할 때
    if pidx is not None and pidx in pdf.get("FontCMap", {}): #[✅ 정상 매핑] pidx와 FontCMap 모두 존재
        print("[✅ 정상 매핑] pidx와 FontCMap 모두 존재")
        for item in font_cid_map:
            if isinstance(item, tuple):
                font_tag, cid_group = item
                merged_result = cmap_error_P.none_damaged(font_tag, cid_group, pdf, pidx)
                result.append(merged_result)
            else:
                result.append(item)  # 일반 텍스트 그대로 추가
        return result

    # 2. content에 pidx가 부여되어 있고 & FontCMap에는 해당 pidx가 없을 때 (Resources만 손상, Page 살아있음)
    elif pidx is not None and pidx not in pdf.get("FontCMap", {}):
        pdf.setdefault("FontCMap", {})[pidx] = {}
        for item in font_cid_map:
            if isinstance(item, tuple):
                font_tag, cid_group = item
                if font_tag in pdf['FontCMap'].get(pidx, {}):  #폰트 확정 및 cmap 재사용 완료한 경우
                    for cid_raw in cid_group:
                        cid = cid_raw.replace('Cid_', '')  # 접두어 제거
                        try:
                            result.append(pdf['FontCMap'][pidx][font_tag][cid])
                        except KeyError:
                            confirmed_font = None
                            for candidate, stats in dbmapresult.get(font_tag, {}).items():
                                if isinstance(stats, dict):
                                    if stats.get('count', 0) >= 5:
                                        confirmed_font = candidate
                                        break

                            if confirmed_font:
                                print(f"[⚠️ 오류 감지] '{font_tag}'에 대해 이전에 확정된 폰트 '{confirmed_font}'에서 CID '{cid}'가 누락됨")
                                # ❗ 제외 목록에 추가
                                font_b = font_tag
                                confirmed_b = confirmed_font if isinstance(confirmed_font, bytes) else confirmed_font.encode()
                                excluded_fonts = dbmapresult.setdefault('exclude', {}).setdefault(font_b, [])
                                if confirmed_b not in excluded_fonts:
                                    excluded_fonts.append(confirmed_b)
                            raise RetryFontMappingException(font_tag, pdf['dbmapresult']['exclude'].get(font_tag, []))
                else:
                    merged_result = cmap_error_P.resource_damaged(font_tag, cid_group, pdf, pidx)
                    result.append(merged_result)
            else:
                result.append(item)  # 일반 텍스트 그대로 추가
        return result
    
    # 3. content에 pidx가 부여되어 있지 않을 때 (None)
    else:
        print("[⚠️ Content 손상] pidx가 없음")
        result = cmap_error_P.page_damaged(font_cid_map, pdf, pidx)
        if result is not None:
            return result
        else:
            print(f"[📛 page_damaged 실패 → damaged 로 fallback]")
            result = []

        for item in font_cid_map:
            if isinstance(item, tuple):
                font_tag, cid_group = item
                if (cid_group[:3] == ["0001", "0002", "0003"]) and (not font_cid_map): #자체 CID + FontCMap이 아예 없는 경우
                    forced_marker_fonts.add(font_tag)
                    formatted = [f"Cid_{cid_raw.replace('Cid_', '')}" for cid_raw in cid_group]
                    marker = f"[{font_tag}:" + ', '.join(formatted) + "]"
                    print(f"[🔎 매핑 실패 후 CID 목록 마커]: {marker}")
                    result.append(marker)
                else:
                    merged_result = cmap_error_P.damaged(font_tag, cid_group, pdf, pidx)
                    result.append(merged_result)
            else:
                result.append(item)  # 일반 텍스트 그대로 추가
        return result

def Error_main_PP(c, pdf, pidx):
    result = []
    font_cid_map = clist_integrate(c)
    dbmapresult = pdf.setdefault('dbmapresult', {})
    exclude_map = dbmapresult.setdefault('exclude', {})
    forced_marker_fonts = set()
    for item in font_cid_map:
        if isinstance(item, tuple):
            font_tag, cid_group = item
            if font_tag in pdf['FontCMap'].get(pidx, {}):  #폰트 확정 및 cmap 재사용 완료한 경우
                for cid_raw in cid_group:
                    cid = cid_raw.replace('Cid_', '')  # 접두어 제거
                    try:
                        result.append(pdf['FontCMap'][pidx][font_tag][cid])
                    except KeyError:
                        confirmed_font = None
                        for candidate, stats in dbmapresult.get(font_tag, {}).items():
                            if isinstance(stats, dict):
                                if stats.get('count', 0) >= 5:
                                    confirmed_font = candidate
                                    break

                        if confirmed_font:
                            print(f"[⚠️ 오류 감지] '{font_tag}'에 대해 이전에 확정된 폰트 '{confirmed_font}'에서 CID '{cid}'가 누락됨")
                            # ❗ 제외 목록에 추가
                            font_b = font_tag
                            confirmed_b = confirmed_font if isinstance(confirmed_font, bytes) else confirmed_font.encode()
                            excluded_fonts = dbmapresult.setdefault('exclude', {}).setdefault(font_b, [])
                            if confirmed_b not in excluded_fonts:
                                excluded_fonts.append(confirmed_b)
                        raise RetryFontMappingException(font_tag, pdf['dbmapresult']['exclude'].get(font_tag, []))
            else:
                if (cid_group[:3] == ["0001", "0002", "0003"]) and (not font_cid_map): #자체 CID + FontCMap이 아예 없는 경우
                    forced_marker_fonts.add(font_tag)
                    formatted = [f"Cid_{cid_raw.replace('Cid_', '')}" for cid_raw in cid_group]
                    marker = f"[{font_tag}:" + ', '.join(formatted) + "]"
                    print(f"[🔎 매핑 실패 후 CID 목록 마커]: {marker}")
                    result.append(marker)
                else: 
                    merged_result = cmap_error_P.none_damaged(font_tag, cid_group, pdf, pidx)
                    result.append(merged_result)
        else:
            result.append(item)  # 일반 텍스트 그대로 추가
    return result

def Error_main(c, pdf):
    result = []
    font_cid_map = clist_integrate_m(c)
    font_CidUnicode = pdf['FontCMap']

    for item in font_cid_map:
        if isinstance(item, tuple):
            font, cid_group = item

            if font not in font_CidUnicode:
                merged_result = cmap_error_S.damage_mac(font, cid_group, pdf)
                if isinstance(merged_result, list):
                    merged_result = ''.join(merged_result)
                result.append(merged_result)
            else:
                # ✅ 폰트는 있으나 개별 CID 확인
                mapped_text = []
                for cid in cid_group:
                    try:
                        mapped_text.append(font_CidUnicode[font][cid])
                    except KeyError:
                        print(f"[ERROR: MissingCMapAccess] font: {font}, cid: {cid}")
                        mapped_text.append(f"[{font}:Cid_{cid}]")

                result.append(''.join(mapped_text))   
        else:
            result.append(item)  # 일반 텍스트 그대로 추가

    return result

def clist_integrate_m(c):
    pattern = re.compile(r"\[b?'?(?P<font>C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':(?P<cids>.+?)\]")
    cid_pattern = re.compile(r"Cid_([0-9A-Fa-f]{4})")
    cid_pattern2 = re.compile(r"(?<![0-9A-Fa-f])Cid_([0-9A-Fa-f]{2})(?![0-9A-Fa-f])")

    result = []
    last_font = None
    current_cids = []

    for item in c:
        text = item.decode() if isinstance(item, bytes) else str(item)
        pos = 0

        for match in pattern.finditer(text):
            start, end = match.span()

            # 🔸 일반 문자열이 있으면 (공백 포함 무조건 추가)
            if start > pos:
                plain_text = text[pos:start]
                if last_font is not None and current_cids:
                    result.append((last_font, current_cids))
                    last_font, current_cids = None, []
                result.append(plain_text)  # strip() 없이 무조건 append

            # 🔸 CID 블록 처리
            font_tag = match.group('font').encode()
            cids_raw = match.group('cids')
            cids = [cid.upper() for cid in cid_pattern.findall(cids_raw)]
            cids += [cid.upper() for cid in cid_pattern2.findall(cids_raw) if cid.upper() not in cids]

            if last_font == font_tag:
                current_cids.extend(cids)
            else:
                if last_font is not None and current_cids:
                    result.append((last_font, current_cids))
                last_font = font_tag
                current_cids = cids

            pos = end

        # 🔸 남은 일반 텍스트 처리 (공백 포함)
        if pos < len(text):
            plain_text = text[pos:]
            if last_font is not None and current_cids:
                result.append((last_font, current_cids))
                last_font, current_cids = None, []
            result.append(plain_text)

    # 🔸 마지막 CID 처리
    if last_font is not None and current_cids:
        result.append((last_font, current_cids))

    # ✅ 동일 font_tag끼리 post-merge (CID 연속 병합)
    merged = []
    for item in result:
        if isinstance(item, tuple):
            if merged and isinstance(merged[-1], tuple) and merged[-1][0] == item[0]:
                merged[-1][1].extend(item[1])
            else:
                merged.append((item[0], item[1][:]))
        else:
            merged.append(item)

    return merged

def clist_integrate(c):
    pattern = re.compile(r"\[b?'?(?P<font>C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':(?P<cids>.+?)\]")
    cid_pattern = re.compile(r"Cid_([0-9A-Fa-f]{4})")
    cid_pattern2 = re.compile(r"(?<![0-9A-Fa-f])Cid_([0-9A-Fa-f]{2})(?![0-9A-Fa-f])")

    result = []
    last_font = None
    current_cids = []

    for item in c:
        text = item.decode() if isinstance(item, bytes) else str(item)
        matches = pattern.findall(text)

        if matches:
            for font_str, cids_raw in matches:
                font_tag = font_str.encode()

                # CID 추출 (4자리 → 2자리 순서로)
                cids = [cid.upper() for cid in cid_pattern.findall(cids_raw)]
                cids += [cid.upper() for cid in cid_pattern2.findall(cids_raw) if cid.upper() not in cids]

                if font_tag == last_font:
                    current_cids.extend(cids)
                else:
                    if last_font is not None:
                        result.append((last_font, current_cids))
                    last_font = font_tag
                    current_cids = cids
        else:
            if last_font is not None:
                result.append((last_font, current_cids))
                last_font, current_cids = None, []
            result.append(item)

    if last_font is not None:
        result.append((last_font, current_cids))

    return result
    
def CMap_Error(font_CidUnicode, CID1, data):
    past_length = len(data)
    for i in font_CidUnicode.keys():
        if isinstance(i, bytes) and i[:6] == b'Random':  # Mapping CID1 with Ramdom#
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
        if isinstance(i, bytes) and i[:6] != b'Random':  # 랜덤이랑 매핑X
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
                elif isinstance(data, str):
                    data = data + "Cid_" + format(CID1, '02x')
                return data
            else:
                if isinstance(data, list):
                    data.append(f"Cid_{CID1}")
                elif isinstance(data, str):
                    data = data + f"Cid_{CID1}"
                return data
        except Exception as e:
            print(f"Error formatting CID: {e}")

    return data

def font_cid_grouped(c):
    font_regex = re.compile(rb'/(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)\s+\d+\.?\d*\s+Tf')
    cid_regex = re.compile(rb'<([A-Fa-f0-9\s\\n]+)>')

    result = []
    current_font = None
    current_cids = []

    lines = c.split(b'\n')

    for line in lines:
        font_match = font_regex.search(line)
        if font_match:
            new_font = font_match.group(1)
            if current_font != new_font:
                if current_font and current_cids:
                    marker = f"[{current_font}:" + ", ".join(f"Cid_{cid}" for cid in current_cids) + "]"
                    result.append(marker)
                current_font = new_font
                current_cids = []

        cid_matches = cid_regex.findall(line)
        for cid in cid_matches:
            if current_font:
                cid_clean = cid.decode('utf-8').replace('\n', '').replace(' ', '').upper()
                for i in range(0, len(cid_clean), 4):
                    if i + 4 <= len(cid_clean):
                        current_cids.append(cid_clean[i:i+4])

    if current_font and current_cids:
        marker = f"[{current_font}:" + ", ".join(f"Cid_{cid}" for cid in current_cids) + "]"
        result.append(marker)

    return result

#Visualization -> Need Modification.
def print_to_png(data, pdf, cnt):
    result_path = os.path.dirname(os.path.realpath(__file__))+"\\export"+"\\"+pdf['Title']+"\\"

    fig, ax = plt.subplots(figsize=(9, 12)) #A4 size

    verts = []
    codes = []

    has_started_path = False
    gflag = False
    start_x, start_y = 0, 0
    max_y = 0
    next_line = 0
    y_length = 0

    # (1) b"\\n" 또는 b"\n"으로 분기하여 라인 분리
    if b"\\n" in data:
        lines = data.split(b"\\n")
    else:
        lines = data.split(b"\n")

    for idx, sent in enumerate(lines):
        # 각 라인 파싱 부분
        try:
            tokens = sent.strip().split()
            tokens = [v for v in tokens if v]  # 공백 제거

            if not tokens:
                continue

            # 첫 줄: max_y, next_line 세팅
            if idx == 0 and len(tokens) >= 2:
                try:
                    max_y = float(tokens[1])
                    next_line = float(tokens[0])
                except ValueError:
                    pass

            cmd = tokens[-1]  # PDF 명령어 후보

            # --- 첫 MOVETO(m) 나오기 전까지는 경로 시작 X ---
            if not has_started_path:
                if cmd == b'm' and len(tokens) >= 3:
                    # 'm'은 보통 x, y 뒤에 오는 형태이므로 최소 3개 이상의 토큰 필요
                    x, y = map(float, tokens[:-1])
                    start_x, start_y = x, y + y_length
                    verts.append((start_x, start_y))
                    codes.append(Path.MOVETO)
                    has_started_path = True
                # 경로가 열리지 않았으므로 다음 라인으로
                continue

            # --- 경로가 열린 상태(has_started_path=True) ---
            # (2) x,y 좌표 비교 (토큰 길이가 충분할 때만)
            if len(tokens) >= 2:
                try:
                    x_val = float(tokens[0])
                    y_val = float(tokens[1])
                    # 단순 비교 로직: 새 줄인지 판별
                    if y_val <= max_y:
                        max_y = y_val
                    if x_val <= next_line:
                        next_line = x_val
                        y_length += max_y
                        max_y = 0
                except ValueError:
                    pass

            # (3) 명령어별 처리
            if cmd == b'l' and len(tokens) >= 3:
                # 선(LINETO)
                x, y = map(float, tokens[:-1])
                y += y_length
                verts.append((x, y))
                codes.append(Path.LINETO)

            elif cmd == b'c' and len(tokens) >= 7:
                # 베지어 곡선(CURVE4)
                x1, y1, x2, y2, x3, y3 = map(float, tokens[:-1])
                y1 += y_length
                y2 += y_length
                y3 += y_length
                verts.extend([(x1, y1), (x2, y2), (x3, y3)])
                codes.extend([Path.CURVE4] * 3)

            elif cmd == b'h':
                # 경로 닫기(CLOSEPOLY)
                codes.append(Path.CLOSEPOLY)
                verts.append((verts[-1][0], verts[-1][1]))

            elif cmd == b'm' and len(tokens) >= 3:
                # 새 MOVETO가 나왔을 때, 이전 경로를 닫고 새 경로 시작
                codes.append(Path.CLOSEPOLY)
                verts.append((verts[-1][0], verts[-1][1]))

                x, y = map(float, tokens[:-1])
                y += y_length
                verts.append((x, y))
                codes.append(Path.MOVETO)

            elif cmd == b'cm':
                # 변환 행렬 명령 -> 여기서는 단순히 CLOSEPOLY로 처리
                codes.append(Path.CLOSEPOLY)
                verts.append((verts[-1][0], verts[-1][1]))

            elif cmd == b're': #직사각형 
                x, y, w, h = map(float, tokens[:-1])
                y += y_length

                verts.extend([
                    (x, y),
                    (x + w, y),
                    (x + w, y + h),
                    (x, y + h),
                    (x, y)
                ])
                codes.extend([
                    Path.MOVETO,
                    Path.LINETO,
                    Path.LINETO,
                    Path.LINETO,
                    Path.CLOSEPOLY
                ])

            # q, Q 등 그래픽 상태 관련 명령은 생략

        except Exception as e:
            # ★ 에러가 발생하면, 지금까지 누적된 경로(verts, codes)로만 그린 뒤 종료
            print(f"에러 발생 (라인 {idx}): {e}")
            break

    # --- for 루프 끝 (또는 break로 탈출) ---
    if not codes:
        # print("경로가 없어 이미지를 생성하지 않습니다.")
        plt.close(fig)
        return gflag

    # 부분적으로라도 생성된 경로가 있으면 그린다
    try:
        path = Path(verts, codes)
        patch = PathPatch(path, facecolor='none', lw=0.5)
        ax.add_patch(patch)

        if path:
            ETC.makeDir(result_path+"\\graphics")
        # 디버깅용 좌표
        for vert in verts:
            ax.plot(vert[0], vert[1], 'k-')

        ax.set_aspect('equal', 'datalim')
        ax.set_xlim(-100, 700)
        ax.autoscale(enable=True, axis='y')  # ✅ Y축은 데이터에 따라 자동 조정
        ax.invert_yaxis()
        plt.grid(False)

        plt.savefig(os.path.join(result_path, "graphics", f"Graphic{cnt}.png"))
        print("Content image : "+os.path.join(result_path, "graphics", f"Graphic{cnt}.png"))
        gflag = True
        plt.close(fig)
        return gflag
    except:
        plt.close(fig)
        return

def Mapping_MSsaveas(pdf, c, pidx, prev_font_tag=None):
    font_CidUnicode = pdf['FontCMap']
    content = ""
    data =  ''

    stream = re.compile(rb'\<([A-Fa-f0-9\\n]+\s*)\>') #format <0000>
    stream2 = re.compile(rb'\([]\\\\().\?\,!\^\$\|\*\+\/]*[0-9]*\s*\)') #Only whitespace and numeric characters.
    stream3 = re.compile(rb'\/(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)') #Font name
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
                                        data = font_cid_grouped(c)
                                else:
                                    try:
                                        CID1 = text[start+1:end+1].decode()
                                        end+=5
                                        start+=5
                                        data.append(font_CidUnicode[Current_F][CID1])
                                    except KeyError:
                                        data = font_cid_grouped(c)
                        else:
                            try:
                                CID1 = text[start:end].decode()
                                end+=4
                                start+=4
                                data.append(font_CidUnicode[Current_F][CID1]) 
                            except KeyError:
                                data = font_cid_grouped(c)
        
    if isinstance(data, list):
        data = ''.join(data)
    content = data
    last_tag = None
    return content, last_tag

def Mapping_MSprint_p(pdf, c, pidx, prev_font_tag=None):
    font_CidUnicode = pdf['FontCMap']
    s1, s2 = [], []
    font = []
    content = ""

    data =  ''

    stream = re.compile(rb'\<([A-Fa-f0-9\\n]+\s*)\>') #format <0000>
    stream2 = re.compile(rb'\([]\\\\().\?\,!\^\$\|\*\+\/]*[0-9]*\s*\)') #Only whitespace and numeric characters.
    stream3 = re.compile(rb'\/(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)') #Font name
    stream4 = re.compile(rb'Lang\s\([^\s]+\)')#forma 'lang () '
    stream5 = re.compile(rb'\((.*?)\)')


    for i in stream.finditer(c): #Character
        s1.append(i)
    for i in stream2.finditer(c): #whitespace or Non-alphanumeric characters
        s2.append(i)
    for i in stream3.finditer(c): #Font name
        font.append(i)
    if len(stream4.findall(c)) != 0 :
        for i in stream4.finditer(c):
            #lang.append(i)
            print("ERROR: MS Print to PDF에서 LANG 발견")
    else:
        pass                    

    if pidx != None and pidx in pdf['FontCMap']:    
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
                                                data.append(font_CidUnicode[pidx][FontNow][CID1])
                                            except KeyError:
                                                # print(f"[ERROR: MissingCID] font: {FontNow}, cid: {CID1}")
                                                try:
                                                    data = font_cid_grouped(c)
                                                except RetryFontMappingException as e:
                                                    raise e  # 상위에서 처리
                                        else:
                                            try:
                                                CID1 = text[start+1:end+1].decode()
                                                end+=5
                                                start+=5
                                                data.append(font_CidUnicode[pidx][FontNow][CID1])
                                            except KeyError:
                                                # print(f"[ERROR: MissingCID] font: {FontNow}, cid: {CID1}")
                                                try:
                                                    data = font_cid_grouped(c)
                                                except RetryFontMappingException as e:
                                                    raise e  # 상위에서 처리
                                else:
                                    try:
                                        CID1 = text[start:end].decode()
                                        end+=4
                                        start+=4
                                        data.append(font_CidUnicode[pidx][FontNow][CID1])  
                                    except KeyError:
                                        # print(f"[ERROR: MissingCID] font: {FontNow}, cid: {CID1}")
                                        try:
                                            data = font_cid_grouped(c)
                                        except RetryFontMappingException as e:
                                            raise e  # 상위에서 처리
                            cntS1-=1
                            l+=1
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
                print("무한루프 진입")
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
                data = []
            else:
                cntF -=1
                StartF+=1

        if isinstance(data, list):
            data = ''.join(data)
        content = data
        last_tag = None
        return content, last_tag
    
    else:
        data = font_cid_grouped(c)
        if isinstance(data, list):
            data = ''.join(data)
        content = data
        last_tag = None
        return content, last_tag

def Mapping_MSprint(pdf, c, pidx, prev_font_tag=None):
    font_CidUnicode = pdf['FontCMap']
    s1, s2 = [], []
    font = []
    content = ""

    data =  ''

    stream = re.compile(rb'\<([A-Fa-f0-9\\n]+\s*)\>') #format <0000>
    stream2 = re.compile(rb'\([]\\\\().\?\,!\^\$\|\*\+\/]*[0-9]*\s*\)') #Only whitespace and numeric characters.
    stream3 = re.compile(rb'\/(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)') #Font name
    stream4 = re.compile(rb'Lang\s\([^\s]+\)')#forma 'lang () '
    stream5 = re.compile(rb'\((.*?)\)')

    for i in stream.finditer(c): #Character
        s1.append(i)
    for i in stream2.finditer(c): #whitespace or Non-alphanumeric characters
        s2.append(i)
    for i in stream3.finditer(c): #Font name
        font.append(i)
    if len(stream4.findall(c)) != 0 :
        for i in stream4.finditer(c):
            #lang.append(i)
            print("ERROR: MS Print to PDF에서 LANG 발견")
    else:
        pass                    

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
                                            if pidx == None: 
                                                data.append(font_CidUnicode[FontNow][CID1])
                                            else:
                                                data.append(font_CidUnicode[pidx][FontNow][CID1])
                                        except KeyError:
                                            # print(f"[ERROR: MissingCID] font: {FontNow}, cid: {CID1}")
                                            try:
                                                data = font_cid_grouped(c)
                                                break
                                            except RetryFontMappingException as e:
                                                raise e  # 상위에서 처리
                                    else:
                                        try:
                                            CID1 = text[start+1:end+1].decode()
                                            end+=5
                                            start+=5
                                            if pidx == None: 
                                                data.append(font_CidUnicode[FontNow][CID1])
                                            else:
                                                data.append(font_CidUnicode[pidx][FontNow][CID1])
                                        except KeyError:
                                            # print(f"[ERROR: MissingCID] font: {FontNow}, cid: {CID1}")
                                            try:
                                                data = font_cid_grouped(c)
                                                break
                                            except RetryFontMappingException as e:
                                                raise e  # 상위에서 처리
                            else:
                                try:
                                    CID1 = text[start:end].decode()
                                    end+=4
                                    start+=4
                                    if pidx == None: 
                                        data.append(font_CidUnicode[FontNow][CID1])
                                    else:
                                        data.append(font_CidUnicode[pidx][FontNow][CID1])  
                                except KeyError:
                                    # print(f"[ERROR: MissingCID] font: {FontNow}, cid: {CID1}")
                                    try:
                                        data = font_cid_grouped(c)
                                        break
                                    except RetryFontMappingException as e:
                                        raise e  # 상위에서 처리
                        cntS1-=1
                        l+=1
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
            print("무한루프 진입")
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
            data = []
        else:
            cntF -=1
            StartF+=1

    if isinstance(data, list):
        data = ''.join(data)
    content = data
    last_tag = None
    return content, last_tag

def Mapping_adobe(pdf, c, pidx, prev_font_tag=None):

    font_CidUnicode = pdf['FontCMap']
    content = []
    data =  ''
    adobe_content = []
    adobe_font = []

    stream1 = re.compile(rb'\(([^\)]*\)*)\)', re.S)
    stream2 = re.compile(rb'\<([A-Fa-f0-9\\n]+\s*)\>', re.S)
    font_regex = re.compile(rb'\/(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)', re.S)

    repl1 = []
    pos = 0
    while pos < len(c):
        m = stream1.search(c, pos)
        if not m:
            break

        block = m.group(0)

        # ✅ block이 \)로 끝나면 → 진짜 닫는 괄호까지 확장
        while block.endswith(b'\\)') and m.end() < len(c):
            next_close = c.find(b')', m.end())
            if next_close == -1:
                break
            block = c[m.start():next_close+1]
            # 새로운 Match 객체처럼 동작하도록 StubMatch 생성
            class _StubMatch:
                def __init__(self, s, start):
                    self._s = s
                    self._start = start
                def group(self):
                    return self._s
                def start(self):
                    return self._start

            m = _StubMatch(block, m.start())

        repl1.append(m)
        pos = m.start() + len(block)  # ✅ pos를 block 끝까지 이동

    repl2 = list(stream2.finditer(c))

    # (매치 시작 위치, 구분자, 매치객체) 형태로 저장
    adobe_content = (
        [(m.start(), 'stream1', m) for m in repl1] +
        [(m.start(), 'stream2', m) for m in repl2]
    )

    adobe_content = [
    item for item in adobe_content 
    if item[2].group() != b'(ko-KR)'
    if item[2].group() != b'(en-US)' # ko-KR 제거
    ]
    # 시작 위치 기준으로 정렬
    adobe_content.sort(key=lambda x: x[0])

    # 폰트 매치 객체 모으기
    for h in font_regex.finditer(c):
        adobe_font.append(h)


    af = 0
    ac = 0
    len_F = len(adobe_font)-1
    len_C = len(adobe_content)

# 🔹 폰트 정보가 중간에 짤렸거나, 아예 식별되지 않은 경우 prev_font_tag 사용
    if ((len(adobe_font) > 0 and adobe_font[0].start() > adobe_content[0][2].start() and prev_font_tag is not None)
            or (len(adobe_font) == 0 and prev_font_tag is not None)):
        
        class _StubMatch:
            def __init__(self, tag):     # tag = b'TT1'
                self._tag = tag
            def start(self):             # 폰트가 텍스트보다 앞에 있어야 하므로 0
                return 0
            def span(self):
                return (0, len(self._tag))  # self._group 대신 self._tag로 수정
            def group(self):
                tag = self._tag
                if not tag.startswith(b'/'):
                    tag = b'/' + tag
                return tag + b' '

        # 기존 폰트 리스트가 비어있다면 새 리스트 생성
        if len(adobe_font) == 0:
            adobe_font = []

        # prev_font_tag를 가장 앞에 삽입
        adobe_font.insert(0, _StubMatch(prev_font_tag))
        len_F = len(adobe_font) - 1

    while len_C > 0:
        if len_F != -1:
            while len_F > -1:
                start = adobe_font[af].start()
                if af == len(adobe_font)-1:
                    next = 99999
                else:
                    next = adobe_font[af+1].start()
                if start <= adobe_content[ac][2].start():
                    if next > adobe_content[ac][2].start(): #start = current font
                        Current_F = adobe_font[af].group()
                        Current_F = Current_F.replace(b"\n",b" ").split(b' ')[0][1:]

                        if adobe_content[ac][1] == 'stream1':  # ( ) 형태 처리 로직 #CID 2글자
                            data = adobe_content[ac][2].group()[1:-1] #remove brackets
                            if b'\\(' in data:
                                data = data.replace(b'\\(', b'(')
                            if b'\\)' in data:
                                data = data.replace(b'\\)', b')')
                            if b'\\[' in data:
                                data = data.replace(b'\\[', b'[')
                            if b'\\]' in data:
                                data = data.replace(b'\\]', b']')                            
                            pattern_list = []
                            pattern = re.compile(rb'(\\\d{3})', re.DOTALL) #이스케이프 8진수 처리 
                            if pattern.search(data):
                                parts = pattern.split(data)
                                for p in parts:
                                    if p == b'':
                                        continue
                                    if b'\\\r' in p:
                                        p = p.replace(b'\\\r', b' ')
                                    if b'\\(' in p:
                                        p = p.replace(b'\\(', b'(')
                                    if b'\\)' in p:
                                        p = p.replace(b'\\)', b')')
                                    if b'\\[' in p:
                                        p = p.replace(b'\\[', b'[')
                                    if b'\\]' in p:
                                        p = p.replace(b'\\]', b']')
                                    pattern_list.append(p)
                                for p in pattern_list:
                                    if pattern.fullmatch(p):
                                        p = p.replace(b"\\", b"")
                                        try:
                                            unicode_char = bytes([int(p, 8)]).decode('cp1252')  # 정확한 문자인 ‘’, “ 등 반환
                                            content.append(unicode_char)
                                        except:
                                            print(f" → CP1252 decoding failed: {p}")
                                            content.append(f"[Escape:{p}]")
                                    else: 
                                        try:
                                            content.append(p.decode())
                                        except UnicodeDecodeError:
                                            print(f" → Decode failed for: {p}")
                                            content.append(f"[{Current_F}:{p}]")
                                ac+=1
                                len_C-=1
                                if len_C == 0:
                                    break

                            else:
                                if b'\\' in data:
                                    data = data.replace(b'\\', b'')
                                try:
                                    content.append(data.decode())
                                except UnicodeDecodeError:
                                    print(f" → Decode failed for: {data}.")
                                    content.append(f"[{Current_F}:{data}]")
                                ac+=1
                                len_C-=1
                                if len_C == 0:
                                    break

                        elif adobe_content[ac][1] == 'stream2':
                            text = adobe_content[ac][2].group()
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
                                                if pidx == None: 
                                                    content.append(font_CidUnicode[Current_F][CID1])
                                                else:
                                                    content.append(font_CidUnicode[pidx][Current_F][CID1])
                                            except KeyError:
                                                content.append(f"[{Current_F}:Cid_{CID1}]")
                                        else:
                                            try:
                                                CID1 = text[start+1:end+1].decode()
                                                end+=5
                                                start+=5
                                                if pidx == None: 
                                                    content.append(font_CidUnicode[Current_F][CID1])
                                                else:
                                                    content.append(font_CidUnicode[pidx][Current_F][CID1])
                                            except KeyError:
                                                content.append(f"[{Current_F}:Cid_{CID1}]")
                                else:
                                    try:
                                        CID1 = text[start:end].decode()
                                        end+=4
                                        start+=4
                                        if pidx == None: 
                                            content.append(font_CidUnicode[Current_F][CID1])
                                        else:
                                            content.append(font_CidUnicode[pidx][Current_F][CID1])
                                    except KeyError:
                                        content.append(f"[{Current_F}:Cid_{CID1}]")
                            ac+=1
                            len_C-=1
                            if len_C == 0:
                                break
                        else:
                            len_F -=1
                    else:
                        af+=1
                        len_F-=1
                else:
                    af+=1
                    len_F-=1
        else:
            for k in adobe_content:
                data = adobe_content[ac][2].group()[1:-1] #remove brackets
                if len(data) != 0:
                    for cids in data:
                        try:
                            if cids == 32:
                                content = content + " " 
                            else:
                                CID1 = format(cids,'02x')
                                if pidx == None: 
                                    content.append(font_CidUnicode[Current_F][CID1])
                                else:
                                    content.append(font_CidUnicode[pidx][Current_F][CID1])
                        except: #If CMap is missing and causes a font error, store it in the form of Cid_2e.
                            content.append(f"[{Current_F}:Cid_{format(cids, '02x').upper()}]")
                    len_C -=1
                    if len_C == 0:
                        break
                else:
                    len_C -=1
                    break

    if adobe_font:
        prev_font_tag = adobe_font[-1].group().split(b' ')[0].strip()   # b'/TT2 ' → b'/TT2'

    # if isinstance(content, list):
    #     content = ''.join(content)

    return content, prev_font_tag

def Mapping_Alpdf(pdf, c, prev_font_tag=None):
    font_CidUnicode = pdf['FontCMap']
    content = ""
    data =  ''
    stream = re.compile(rb'\(([^\)]*\)*)\)', re.S)
    s=[]
    for i in stream.finditer(c):#CID
        s.append(i)
    Font = []
    ContentCid = [] 
    stream2 = re.compile(rb'\/(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)')
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
            if font_CidUnicode.get(Current_F, {}).get("__Type1__") == True: #Type1 font 추가 
                data = text
                if '\\x' in data:
                    byte_data = bytes.fromhex(data.replace('\\x', ''))
                    try:
                        data = byte_data.decode('windows-1252')
                    except UnicodeDecodeError:
                        data = byte_data.decode('utf-16')
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
                content = content + data
                processed = True
            else:
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
                            elif text[num+1:num+4] == '\\\\\\':
                                ContentCid.append(format(ord("\\"), '02x'))
                                num += 4
                            elif text[num+1] == '\\':
                                num += 1
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
                    processed = False
                    if len(ContentCid) == 2:
                        CID1 = (ContentCid[0] + ContentCid[1]).upper()
                        if Current_F not in font_CidUnicode.keys():  # If not found, map to random data
                            content = CMap_Error(font_CidUnicode, CID1, content)
                        else:
                            content = content + font_CidUnicode[Current_F][CID1]
                        ContentCid = []
                        processed = True
                    elif len(ContentCid) < 2 and len(text) <= num:
                        if len(ContentCid) > 0:  # Process only if ContentCid is not empty
                            CID1 = ContentCid[0].upper()
                            try:
                                content = content + font_CidUnicode[Current_F][CID1]
                                processed = True
                            except KeyError:
                                content = CMap_Error(font_CidUnicode, CID1, content)
                            ContentCid = []
                            processed = True #CMap_Error에서 처리됐을 경우에만 True로 수정필요 

            if len(ContentCid) > 2 and processed == False:
                if text != b'(en-US)':
                    try:
                        content = content + text
                    except UnicodeDecodeError:
                        pass
            else:  # if not found CMap
                if h.group() != b'(en-US)' and processed == False:
                    try:
                        content = content + h.group()[1:-1].decode()
                    except UnicodeDecodeError:
                        pass

    return content, prev_font_tag

def Mapping_MAC(pdf, c, prev_font_tag=None):
    font_CidUnicode = pdf['FontCMap']
    content = []
    data =  ''
    mac_content = []
    mac_font = []
    stream1 = re.compile(rb'\(([!@#$%^&*()_+-={}\[\]:;"\'<>,.?/\\\|0-9A-z]*\s*)\)', re.S)
    stream2 = re.compile(rb'\(([^\)]*\)*)\)', re.S)
    stream3 = re.compile(rb'\/(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)', re.S) #Font name

    stream1_matches = list(stream1.finditer(c))
    stream2_matches = list(stream2.finditer(c))

    final_matches = stream1_matches.copy() #stream1의 범위 우선적으로 채택 

    occupied = [(m.start(), m.end()) for m in stream1_matches] # stream1 범위 목록 저장 (start~end 튜플)
    for m in stream2_matches: # stream2의 각 match가 기존 stream1과 겹치는지 확인
        s2_start, s2_end = m.start(), m.end()
        overlapped = False
        for s1_start, s1_end in occupied:
            if not (s2_end <= s1_start or s2_start >= s1_end): # 겹침 판단 (부분이라도 겹치면 True)
                overlapped = True
                break
        if not overlapped:
            final_matches.append(m)

    final_matches.sort(key=lambda x: x.start()) #정렬: 원본 기준 위치 
    mac_content = final_matches

    for h in stream3.finditer(c):
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
                if start <= mac_content[mc].start(): #7.Kor_궁서,레코체.pdf에서 2페이지 479번째 block에서 start가 78인데, 기존에는 start < ~ 이어서 else문으로 처리됨. 따라서 <=로 수정함함
                    if next > mac_content[mc].start(): #start = current font
                        Current_F = mac_font[mf].group()
                        Current_F = Current_F.replace(b"\n",b" ").split(b' ')[0][1:]
                        data = mac_content[mc].group()[1:-1] #remove brackets
                        data = data.replace(b"\\x",b"")
                        if b"\\\\" in data: #\\x5c로 처리할 수 있도록 코드 추가 
                            data = data.replace(b"\\\\",b"\\")
                        else:
                            data = data.replace(b"\\",b"")
                        for cids in data:
                            try:
                                if cids == 32:
                                    content.append(" ")
                                else:
                                    CID1 = format(cids,'02x')
                                    try: 
                                        content.append(font_CidUnicode[Current_F][CID1])
                                    except:
                                        CID1 = CID1.upper() #대문자로 처리 추가 (2a, 2A 모두 시도하기 위해)
                                        content.append(font_CidUnicode[Current_F][CID1])
                            except:
                                CID1 = format(cids,'02x').upper()
                                content.append(f"[{Current_F}:Cid_{CID1}]")
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
                                content.append(" ")
                            else:
                                CID1 = format(cids,'02x')
                                content.append(font_CidUnicode[Current_F][CID1])
                        except: #If CMap is missing and causes a font error, store it in the form of Cid_2e.
                            CID1 = format(cids,'02x').upper()
                            content.append(f"[{Current_F}:Cid_{CID1}]")
                else:
                    len_C -=1
                    break

    return content, prev_font_tag

# def check_pageidx(pdf):
#     if 'Page' not in pdf['DamagedObj'] and 'Resources' in pdf['DamagedObj']:
#         dflag = "damaged"
#     elif 'Page' in pdf['DamagedObj']: 
#         dflag = "page_damaged"
#     elif 'Resources' in pdf['DamagedObj']:
#         dflag = "resource_damaged"
#     else:
#         dflag = None

#     return dflag

def blocksplit(pdf, c):
    block_list = []
    last_end = 0

    if pdf['SaveMethod'] == "Microsoft Save as":
        for match in re.finditer(rb'/Span(.*?)EMC', c, re.DOTALL):
            if match.start() > last_end:
                block_list.append(c[last_end:match.start()].strip())  # /Span-EMC 외 텍스트
            block_list.append(match.group().strip())
            last_end = match.end()
        if last_end < len(c):
            block_list.append(c[last_end:].strip())        
        return block_list
    
    elif pdf['SaveMethod'] == "Microsoft Print to PDF":
        for match in re.finditer(rb'BT(.*?)ET', c, re.DOTALL):
            if match.start() > last_end:
                block_list.append(c[last_end:match.start()].strip())
            block_list.append(match.group().strip())
            last_end = match.end()
        if last_end < len(c):
            block_list.append(c[last_end:].strip()) 
        return block_list

    else: 
        if b"/Lang" in c and b'/Span' in c: 
            for match in re.finditer(rb'/Span(.*?)EMC', c, re.DOTALL):
                if match.start() > last_end:
                    block_list.append(c[last_end:match.start()].strip())  # /Span-EMC 외 텍스트
                block_list.append(match.group().strip())
                last_end = match.end()
            if last_end < len(c):
                block_list.append(c[last_end:].strip())
            return block_list

        else:
            for match in re.finditer(rb'BT(.*?)ET', c, re.DOTALL):
                if match.start() > last_end:
                    block_list.append(c[last_end:match.start()].strip())
                block_list.append(match.group().strip())
                last_end = match.end()
            if last_end < len(c):
                block_list.append(c[last_end:].strip())  
            return block_list             

def saveas_main(decompressObj, pdf):
    all_result = []  # 모든 페이지 결과 저장 리스트
    cnt = 0
    prev_tag = None
    retry_flag = False  # 전체 재시도 트리거

    for i in pdf['Content']:  # Mapping per page
        c = decompressObj[i][2]  # Content data

        result = []  # 이 페이지의 결과
        page_idx = None
        block_list = blocksplit(pdf, c)

        for _, block in enumerate(block_list):
            if re.search(rb'BT(.*?)ET', block, re.DOTALL):  # 텍스트 데이터
                try: 
                    if pdf['SaveMethod'] == "Microsoft Save as":
                        text, prev_tag = Mapping_MSsaveas(pdf, block, page_idx, prev_font_tag=prev_tag)
                    text = ''.join(str(t) for t in text)
                    result.append(text)
                except RetryFontMappingException as e:
                    font = e.font
                    excluded_fonts = e.excluded_fonts
                    print(f"[↩ 재매핑 트리거] '{font}' → 제외된 폰트: {excluded_fonts}")
                    pdf.setdefault("dbmapresult", {}).setdefault("exclude", {}).setdefault(font, []).extend(excluded_fonts)
                    retry_flag = True
                    break  # block_list loop 탈출
            else:
                matches = list(re.finditer(rb'/(\w+)\sDo', block))
                last_pos = 0
                for match in matches:
                    image_name = match.group(1).decode()
                    do_start = match.start()
                    
                    # Do 연산자 이전 영역 추출
                    pre_do_block = block[last_pos:do_start]

                    # 그래픽 연산자 조건 검사
                    if (
                        re.search(rb'(?<![a-zA-Z])re', pre_do_block) or
                        re.search(rb'(?<![a-zA-Z])m', pre_do_block)
                    ):
                        paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
                        if any(op in pre_do_block for op in paint_ops):
                            cnt += 1
                            gflag = print_to_png(block, pdf, cnt)
                            if gflag == True:
                                result.append(f"Graphic{cnt}")

                    result.append(image_name)
                    last_pos = match.end()
                    
                if not matches:
                    if re.search(rb'(?<![a-zA-Z])re', block) or re.search(rb'(?<![a-zA-Z])m', block): #그래픽 데이터
                        paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
                        if any(op in block for op in paint_ops):
                            cnt += 1
                            gflag = print_to_png(block, pdf, cnt)
                            if gflag == True:
                                result.append(f"Graphic{cnt} ")
                    else:
                        pass
                else:
                    pass  # 무시

        if retry_flag:
            print("[🔁 전체 ContentStream 재처리]")
            return Mapping(decompressObj, pdf)  # 재귀 호출로 전체 페이지 재처리
        
        pattern = re.compile(r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':\s*(Cid_[0-9A-Fa-f]{4}(?:,\s*Cid_[0-9A-Fa-f]{4})*)\]")
        if any(pattern.search(text) for text in result):
            result = Error_main_S(result, pdf)
        else:
            pass

        page_text = ''.join(result) # 페이지별 content를 하나의 문자열로 병합하여 저장
        all_result.append(page_text)

    text_with_placeholders, text_cleaned = resolve_failed_cid_markers(all_result, pdf)
    pdf["Text"] = text_with_placeholders
    pdf["Text_clean"] = text_cleaned
    return pdf

def printtopdf_main(decompressObj, pdf):
    all_result = []  # 모든 페이지 결과 저장 리스트
    cnt = 0
    prev_tag = None
    retry_flag = False  # 전체 재시도 트리거

    if 'Content_p' in pdf or 'Resouces_p' in pdf:
        for i in pdf['Content']:  # Mapping per page
            c = decompressObj[i][2]
            result = []  # 이 페이지의 결과
            block_list = blocksplit(pdf, c)
            page_idx = None
            for pidx, obj_list in pdf.get('Content_p', {}).items():
                if i in obj_list:
                    page_idx = pidx
                    break
            for _, block in enumerate(block_list): #블록별로 데이터 처리
                if re.search(rb'BT(.*?)ET', block, re.DOTALL):  # text object
                    try: 
                        text, prev_tag = Mapping_MSprint_p(pdf, block, page_idx, prev_font_tag=prev_tag)
                        text = ''.join(str(t) for t in text)
                        result.append(text)
                    except Exception as e:
                        print(f"error: {e}")

                else:
                    matches = list(re.finditer(rb'/(\w+)\sDo', block)) # Xobject
                    last_pos = 0
                    for match in matches:
                        image_name = match.group(1).decode()
                        do_start = match.start()
                        
                        # Do 연산자 이전 영역 추출
                        pre_do_block = block[last_pos:do_start]

                        # 그래픽 연산자 조건 검사(Path object)
                        if (
                            re.search(rb'(?<![a-zA-Z])re', pre_do_block) or
                            re.search(rb'(?<![a-zA-Z])m', pre_do_block)
                        ):
                            paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
                            if any(op in pre_do_block for op in paint_ops):
                                cnt += 1
                                gflag = print_to_png(block, pdf, cnt)
                                if gflag == True:
                                    result.append(f"Graphic{cnt}")

                        result.append(image_name)
                        last_pos = match.end()

                if not matches:
                    if re.search(rb'(?<![a-zA-Z])re', block) or re.search(rb'(?<![a-zA-Z])m', block): #Path object
                        paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
                        if any(op in block for op in paint_ops):
                            cnt += 1
                            gflag = print_to_png(block, pdf, cnt)
                            if gflag == True:
                                result.append(f"Graphic{cnt} ")
                    else:
                        pass
                else:
                    pass  # 무시

            pattern = re.compile(r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':\s*(Cid_[0-9A-Fa-f]{4}(?:,\s*Cid_[0-9A-Fa-f]{4})*)\]")
            if any(pattern.search(text) for text in result):
                result = Error_main_P(result, pdf, page_idx)
            else:
                pass
            
            # 페이지별 content를 하나의 문자열로 병합하여 저장
            if isinstance(result, list):
                result = ''.join(result)
            all_result.append(result)

        text_with_placeholders, text_cleaned = resolve_failed_cid_markers(all_result, pdf)
        pdf["Text"] = text_with_placeholders
        pdf["Text_clean"] = text_cleaned
        return pdf

    elif 'Page' in pdf['DamagedObj'] or 'Resources' in pdf['DamagedObj']: #pidx가 없는 게 손상되서인 경우 
        for i in pdf['Content']:  # Mapping per page
            c = decompressObj[i][2]
            result = []  # 이 페이지의 결과
            block_list = blocksplit(pdf, c)
            page_idx = None

            for _, block in enumerate(block_list): #블록별로 데이터 처리
                if re.search(rb'BT(.*?)ET', block, re.DOTALL):  # text object
                    try: 
                        text, prev_tag = Mapping_MSprint_p(pdf, block, page_idx, prev_font_tag=prev_tag)
                        text = ''.join(str(t) for t in text)
                        result.append(text)
                    except Exception as e:
                        print("error")

                else:
                    matches = list(re.finditer(rb'/(\w+)\sDo', block)) # Xobject
                    last_pos = 0
                    for match in matches:
                        image_name = match.group(1).decode()
                        do_start = match.start()
                        
                        # Do 연산자 이전 영역 추출
                        pre_do_block = block[last_pos:do_start]

                        # 그래픽 연산자 조건 검사(Path object)
                        if (
                            re.search(rb'(?<![a-zA-Z])re', pre_do_block) or
                            re.search(rb'(?<![a-zA-Z])m', pre_do_block)
                        ):
                            paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
                            if any(op in pre_do_block for op in paint_ops):
                                cnt += 1
                                gflag = print_to_png(block, pdf, cnt)
                                if gflag == True:
                                    result.append(f"Graphic{cnt}")

                        result.append(image_name)
                        last_pos = match.end()

                if not matches:
                    if re.search(rb'(?<![a-zA-Z])re', block) or re.search(rb'(?<![a-zA-Z])m', block): #Path object
                        paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
                        if any(op in block for op in paint_ops):
                            cnt += 1
                            gflag = print_to_png(block, pdf, cnt)
                            if gflag == True:
                                result.append(f"Graphic{cnt} ")
                    else:
                        pass
                else:
                    pass  # 무시

            pattern = re.compile(r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':\s*(Cid_[0-9A-Fa-f]{4}(?:,\s*Cid_[0-9A-Fa-f]{4})*)\]")
            if any(pattern.search(text) for text in result):
                result = Error_main_P(result, pdf, page_idx)
            else:
                pass
            
            # 페이지별 content를 하나의 문자열로 병합하여 저장
            if isinstance(result, list):
                result = ''.join(result)
            all_result.append(result)

        text_with_placeholders, text_cleaned = resolve_failed_cid_markers(all_result, pdf)
        pdf["Text"] = text_with_placeholders
        pdf["Text_clean"] = text_cleaned
        return pdf

    else: #pidx없는 정상파일인 경우 (CMap 손상의 경우만 존재)
        for i in pdf['Content']:  # Mapping per page
            c = decompressObj[i][2]
            result = []  # 이 페이지의 결과
            block_list = blocksplit(pdf, c)
            page_idx = None

            for _, block in enumerate(block_list): #블록별로 데이터 처리
                if re.search(rb'BT(.*?)ET', block, re.DOTALL):  # text object
                    try: 
                        text, prev_tag = Mapping_MSprint(pdf, block, page_idx, prev_font_tag=prev_tag)
                        text = ''.join(str(t) for t in text)
                        result.append(text)
                    except Exception as e:
                        print("error")

                else:
                    matches = list(re.finditer(rb'/(\w+)\sDo', block)) # Xobject
                    last_pos = 0
                    for match in matches:
                        image_name = match.group(1).decode()
                        do_start = match.start()
                        
                        # Do 연산자 이전 영역 추출
                        pre_do_block = block[last_pos:do_start]

                        # 그래픽 연산자 조건 검사(Path object)
                        if (
                            re.search(rb'(?<![a-zA-Z])re', pre_do_block) or
                            re.search(rb'(?<![a-zA-Z])m', pre_do_block)
                        ):
                            paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
                            if any(op in pre_do_block for op in paint_ops):
                                cnt += 1
                                gflag = print_to_png(block, pdf, cnt)
                                if gflag == True:
                                    result.append(f"Graphic{cnt}")

                        result.append(image_name)
                        last_pos = match.end()

                if not matches:
                    if re.search(rb'(?<![a-zA-Z])re', block) or re.search(rb'(?<![a-zA-Z])m', block): #Path object
                        paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
                        if any(op in block for op in paint_ops):
                            cnt += 1
                            gflag = print_to_png(block, pdf, cnt)
                            if gflag == True:
                                result.append(f"Graphic{cnt} ")
                    else:
                        pass
                else:
                    pass  # 무시

            pattern = re.compile(r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':\s*(Cid_[0-9A-Fa-f]{4}(?:,\s*Cid_[0-9A-Fa-f]{4})*)\]")
            if any(pattern.search(text) for text in result):
                result = Error_main_PP(result, pdf, page_idx)
            else:
                pass
            
            # 페이지별 content를 하나의 문자열로 병합하여 저장
            if isinstance(result, list):
                result = ''.join(result)
            all_result.append(result)

        text_with_placeholders, text_cleaned = resolve_failed_cid_markers(all_result, pdf)
        pdf["Text"] = text_with_placeholders
        pdf["Text_clean"] = text_cleaned
        return pdf

def adobe_main(decompressObj, pdf):
    all_result = []  # 모든 페이지 결과 저장 리스트
    cnt = 0
    prev_tag = None
    retry_flag = False  # 전체 재시도 트리거

    if 'Content_p' in pdf or 'Resouces_p' in pdf:
        for i in pdf['Content']:  # Mapping per page index
            page_idx = None
            for pidx, obj_list in pdf.get('Content_p', {}).items():
                if i in obj_list:
                    page_idx = pidx
                    break
            c = decompressObj[i][2]  # Content data
            result = []  # 이 content 블록의 결과

            result, prev_tag = Mapping_adobe(pdf, c, page_idx, prev_font_tag=prev_tag)  # page_idx 전달

            pattern = re.compile(
                r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':\s*(Cid_[0-9A-Fa-f]{2,4}(?:,\s*Cid_[0-9A-Fa-f]{2,4})*)\]"
            )
            if any(pattern.search(text) for text in result):
                try:
                    result = Error_main_P(result, pdf, page_idx)
                except RetryFontMappingException as e:
                    font = e.font
                    excluded_fonts = e.excluded_fonts
                    print(f"[↩ 재매핑 트리거] '{font}' → 제외된 폰트: {excluded_fonts}")
                    result = Error_main_P(result, pdf, page_idx)
                if isinstance(result, list):
                    result = ''.join(result)
            else:
                if isinstance(result, list):
                    result = ''.join(result)
            
            all_result.append(result)
            continue

        text_with_placeholders, text_cleaned = resolve_failed_cid_markers(all_result, pdf)
        pdf["Text"] = text_with_placeholders
        pdf["Text_clean"] = text_cleaned
        return pdf

    else:
        for i in pdf['Content']:  # Mapping per page
            c = decompressObj[i][2]  # Content data
            result = []  # 이 페이지의 결과
            page_idx = None

            result, prev_tag = Mapping_adobe(pdf, c, page_idx, prev_font_tag=prev_tag)
            
            pattern = re.compile(
                r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':\s*(Cid_[0-9A-Fa-f]{2,4}(?:,\s*Cid_[0-9A-Fa-f]{2,4})*)\]"
            )
            if any(pattern.search(text) for text in result):
                try:
                    result = Error_main_PP(result, pdf, page_idx)
                except RetryFontMappingException as e:
                    font = e.font
                    excluded_fonts = e.excluded_fonts
                    print(f"[↩ 재매핑 트리거] '{font}' → 제외된 폰트: {excluded_fonts}")
                    result = Error_main_P(result, pdf, page_idx)
                if isinstance(result, list):
                    result = ''.join(result)
            else:
                if isinstance(result, list):
                    result = ''.join(result)
            
            all_result.append(result)
            continue

        text_with_placeholders, text_cleaned = resolve_failed_cid_markers(all_result, pdf)
        pdf["Text"] = text_with_placeholders
        pdf["Text_clean"] = text_cleaned
        return pdf
    
def MAC_main(decompressObj, pdf):
    all_result = []  # 모든 페이지 결과 저장 리스트
    cnt = 0
    prev_tag = None
    retry_flag = False  # 전체 재시도 트리거

    for i in pdf['Content']:  # Mapping per page
        print(f"Content {i} 처리 시작")
        c = decompressObj[i][2]  # Content data

        result = []  # 이 페이지의 결과
        block_list = blocksplit(pdf, c)

        for _, block in enumerate(block_list):
            if re.search(rb'BT(.*?)ET', block, re.DOTALL):  # 텍스트 데이터
                try: 
                    text, prev_tag = Mapping_MAC(pdf, block, prev_font_tag=prev_tag)
                    text = ''.join(str(t) for t in text)
                    result.append(text)
                except Exception as e:
                    break  # block_list loop 탈출
            else:
                matches = list(re.finditer(rb'/(\w+)\sDo', block))
                last_pos = 0
                for match in matches:
                    image_name = match.group(1).decode()
                    do_start = match.start()
                    
                    # Do 연산자 이전 영역 추출
                    pre_do_block = block[last_pos:do_start]

                    # 그래픽 연산자 조건 검사
                    if (
                        re.search(rb'(?<![a-zA-Z])re', pre_do_block) or
                        re.search(rb'(?<![a-zA-Z])m', pre_do_block)
                    ):
                        paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
                        if any(op in pre_do_block for op in paint_ops):
                            cnt += 1
                            gflag = print_to_png(block, pdf, cnt)
                            if gflag == True:
                                result.append(f"Graphic{cnt}")

                    result.append(image_name)
                    last_pos = match.end()
                    
                if not matches:
                    if re.search(rb'(?<![a-zA-Z])re', block) or re.search(rb'(?<![a-zA-Z])m', block): #그래픽 데이터
                        paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
                        if any(op in block for op in paint_ops):
                            cnt += 1
                            gflag = print_to_png(block, pdf, cnt)
                            if gflag == True:
                                result.append(f"Graphic{cnt} ")
                    else:
                        pass
                else:
                    pass  # 무시

        pattern = re.compile(
            r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':\s*(Cid_[0-9A-Fa-f]{2,4}(?:,\s*Cid_[0-9A-Fa-f]{2,4})*)\]"
        )                
        if any(pattern.search(text) for text in result):
            result = Error_main(result, pdf)
            if isinstance(result, list):
                result = ''.join(result)
        else:
            if isinstance(result, list):
                result = ''.join(result)

        all_result.append(result)
        continue

    text_with_placeholders, text_cleaned = resolve_failed_cid_markers(all_result, pdf)
    pdf["Text"] = text_with_placeholders
    pdf["Text_clean"] = text_cleaned
    return pdf

# def AlPDF_main(decompressObj, pdf):
#     all_result = []  # 모든 페이지 결과 저장 리스트
#     cnt = 0
#     prev_tag = None
#     retry_flag = False  # 전체 재시도 트리거    
    # for i in pdf['Content']:  # Mapping per page
    #     print(f"Content {i} 처리 시작")
    #     c = decompressObj[i][2]  # Content data

    #     result = []  # 이 페이지의 결과
    #     block_list = blocksplit(pdf, c)

    #     for _, block in enumerate(block_list):
    #         if re.search(rb'BT(.*?)ET', block, re.DOTALL):  # 텍스트 데이터
    #             try: 
    #                 text, prev_tag = Mapping_Alpdf(pdf, block, prev_font_tag=prev_tag)
    #                 text = ''.join(str(t) for t in text)
    #                 result.append(text)
    #             except Exception as e:
    #                 break  # block_list loop 탈출
    #         else:
    #             matches = list(re.finditer(rb'/(\w+)\sDo', block))
    #             last_pos = 0
    #             for match in matches:
    #                 image_name = match.group(1).decode()
    #                 do_start = match.start()
                    
    #                 # Do 연산자 이전 영역 추출
    #                 pre_do_block = block[last_pos:do_start]

    #                 # 그래픽 연산자 조건 검사
    #                 if (
    #                     re.search(rb'(?<![a-zA-Z])re', pre_do_block) or
    #                     re.search(rb'(?<![a-zA-Z])m', pre_do_block)
    #                 ):
    #                     paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
    #                     if any(op in pre_do_block for op in paint_ops):
    #                         cnt += 1
    #                         gflag = print_to_png(block, pdf, cnt)
    #                         if gflag == True:
    #                             result.append(f"Graphic{cnt}")

    #                 result.append(image_name)
    #                 last_pos = match.end()
                    
    #             if not matches:
    #                 if re.search(rb'(?<![a-zA-Z])re', block) or re.search(rb'(?<![a-zA-Z])m', block): #그래픽 데이터
    #                     paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
    #                     if any(op in block for op in paint_ops):
    #                         cnt += 1
    #                         gflag = print_to_png(block, pdf, cnt)
    #                         if gflag == True:
    #                             result.append(f"Graphic{cnt} ")
    #                 else:
    #                     pass
    #             else:
    #                 pass  # 무시

    #     pattern = re.compile(
    #         r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':\s*(Cid_[0-9A-Fa-f]{2,4}(?:,\s*Cid_[0-9A-Fa-f]{2,4})*)\]"
    #     )                
    #     if any(pattern.search(text) for text in result):
    #         result = Error_main(result, pdf)
    #         if isinstance(result, list):
    #             result = ''.join(result)
    #     else:
    #         if isinstance(result, list):
    #             result = ''.join(result)

    #     all_result.append(result)
    #     continue

    # final_result = resolve_failed_cid_markers(all_result, pdf)
    # pdf['Text'] = final_result
    # return pdf

# Main    
def Mapping(decompressObj, pdf):
  
    if pdf['SaveMethod'] == "Microsoft Save as":
        pdf = saveas_main(decompressObj, pdf)
    elif pdf['SaveMethod'] == "Microsoft Print to PDF":
        pdf = printtopdf_main(decompressObj, pdf)
    elif pdf['SaveMethod'] == "Adobe":
        pdf = adobe_main(decompressObj, pdf)                    
    elif pdf['SaveMethod'] == "MAC":
        pdf = MAC_main(decompressObj, pdf)
    # elif pdf['SaveMethod'] == "AlPDF":
    #     pdf = AlPDF_main(decompressObj, pdf)
    elif pdf['SaveMethod'] != "Microsoft Save as" and pdf['SaveMethod'] != "Microsoft Print to PDF" and pdf['SaveMethod'] != "Adobe" and pdf['SaveMethod'] != "MAC": #and pdf['SaveMethod'] != "AlPDF":
        print("📌 SaveMethod가 Unknown입니다. 가능한 모든 방법을 시도합니다.")
        candidates = [
            ("Microsoft Save as", saveas_main),
            ("Microsoft Print to PDF", printtopdf_main),
            ("Adobe", adobe_main),
            ("MAC", MAC_main),
            # ("AlPDF", AlPDF_main)  # 필요시 추가
        ]

        all_results = []

        for name, func in candidates:
            try:
                temp_pdf = pdf.copy()
                temp_pdf['SaveMethod'] = name
                temp_pdf = func(decompressObj, temp_pdf)

                result_text = temp_pdf.get('Text', '')
                if isinstance(result_text, list):
                    result_text = ''.join(result_text)
                all_results.append((name, result_text)) 
                print(f"✅ {name} 방식 시도 성공")
            except Exception as e:
                print(f"❌ {name} 방식 실패: {e}")

        pdf['CandidateResults'] = all_results  # 모든 성공한 결과 저장

    else: #pdf['SaveMethod'] == "Unknown"
        print("❗ Mapping단계 오류: Mapping단계에서 SaveMethod 인식 실패")
    return pdf

def resolve_failed_cid_markers(text_input, pdf):
    """CID 매핑 실패 항목을 font_CidUnicode 또는 DB 기반으로 보완
    Returns:
        tuple: (text_with_placeholders, text_cleaned)
    """

    # ex: [F4:Cid_0019, Cid_0023, Cid_003E]
    pattern = re.compile(
        r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':\s*(Cid_[0-9A-Fa-f]{2,4}(?:,\s*Cid_[0-9A-Fa-f]{2,4})*)\]"
    )

    font_CidUnicode = pdf.get("FontCMap", {})

    def resolve_in_text(text):
        text_with_placeholders = text
        text_cleaned = text

        for match in pattern.finditer(text):
            full_match = match.group(0)
            font_tag = match.group(1)
            cid_string = match.group(2)
            cid_list = [cid.strip().replace("Cid_", "").upper() for cid in cid_string.split(",")]

            font_tag_b = font_tag.encode() if isinstance(font_tag, str) else font_tag

            resolved_chars = []
            cleaned_chars = []
            for cid in cid_list:
                if font_tag_b in font_CidUnicode and cid in font_CidUnicode[font_tag_b]:
                    replacement = font_CidUnicode[font_tag_b][cid]
                    print(f"[✅ 기존 cmap 매핑] [{font_tag}:Cid_{cid}] → '{replacement}'")
                    resolved_chars.append(replacement)
                    cleaned_chars.append(replacement)
                else:
                    # 실패 → placeholder 그대로 vs 공백
                    resolved_chars.append(f"[{font_tag}:Cid_{cid}]")
                    cleaned_chars.append(" ")

            # 치환
            text_with_placeholders = text_with_placeholders.replace(full_match, ''.join(resolved_chars))
            text_cleaned = text_cleaned.replace(full_match, ''.join(cleaned_chars))

        return text_with_placeholders, text_cleaned

    # ✅ 문자열이면 그대로, 리스트면 각 항목 처리
    if isinstance(text_input, str):
        return resolve_in_text(text_input)
    elif isinstance(text_input, list):
        placeholders, cleaned = zip(*(resolve_in_text(t) for t in text_input))
        return list(placeholders), list(cleaned)
    else:
        raise TypeError("Input text must be str or list of str")
                
>>>>>>> 77c3de1 (Code Upload)
