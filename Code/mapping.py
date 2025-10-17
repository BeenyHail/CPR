import re
import os
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path
import ETC
from time import time
import error_main

class RetryFontMappingException(Exception):
    def __init__(self, font, excluded_fonts):
        self.font = font
        self.excluded_fonts = excluded_fonts
        super().__init__(f"Retry font mapping for {font}")

def CMap_Error(c, pdf, pidx=None):
    result = []
    font_cid_map = error_main.clist_integrate(c)  # [(fonttag, [cid, cid, ...]), ...]
    font_CidUnicode = pdf['FontCMap']

    # Get the appropriate font map based on pidx
    if pidx is not None and pidx in font_CidUnicode:
        font_map = font_CidUnicode[pidx]
    else:
        font_map = font_CidUnicode

    # Group items by font tag while preserving original order
    from collections import defaultdict
    font_groups = defaultdict(list)

    for idx, item in enumerate(font_cid_map):
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], bytes) and isinstance(item[1], list):
            font, cids = item
            font_groups[font].append((idx, item, cids))

    # Determine best Random font for each font tag
    font_tag_strategy = {}  # {font_tag: best_random_font or None}
    for font_tag, group_items in font_groups.items():
        # Collect all CIDs for this font tag
        all_cids = []
        for _, _, cids in group_items:
            all_cids.extend(cids)
        all_cids_set = set(all_cids)

        # Find Random font that contains ALL CIDs for this font tag
        best_random_font = None
        for font_key in font_map.keys():
            if isinstance(font_key, bytes) and font_key[:6] == b'Random':
                # Check if this Random font contains all CIDs
                if all(cid in font_map[font_key] for cid in all_cids_set):
                    best_random_font = font_key
                    break

        font_tag_strategy[font_tag] = best_random_font

    # Process items in original order
    for item in font_cid_map:
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], bytes) and isinstance(item[1], list):
            font_tag, cids = item
            best_random_font = font_tag_strategy.get(font_tag)

            # If we found a matching Random font, use it for all CIDs
            if best_random_font:
                mapped_text = []
                for cid in cids:
                    try:
                        mapped_char = font_map[best_random_font][cid]
                        mapped_text.append(mapped_char)
                    except KeyError:
                        mapped_text.append(f"[{font_tag}:Cid_{cid}]")
                result.append(''.join(mapped_text))
            else:
                # No complete Random font found, process each CID individually
                mapped_text = []
                for cid in cids:
                    # Check if pidx exists and call appropriate function
                    if pidx is not None:
                        mapped_char = CMap_Error_fix_p(font_CidUnicode, cid, "", pidx)
                    else:
                        mapped_char = CMap_Error_fix(font_CidUnicode, cid, "")

                    # If mapping failed and returned placeholder with "Cid_", replace with font-specific placeholder
                    if isinstance(mapped_char, str):
                        if mapped_char.startswith("Cid_"):
                            mapped_text.append(f"[{font_tag}:{mapped_char}]")
                        else:
                            mapped_text.append(mapped_char)
                    else:
                        mapped_text.append(str(mapped_char))

                result.append(''.join(mapped_text))
        else:
            # Non-tuple items (like text or graphics)
            result.append(item)

    return result

def CMap_Error_fix(font_CidUnicode, CID1, data):
    """CMap error fix function without pidx (direct font_CidUnicode access)"""
    past_length = len(data)

    # Check if 'eng' key exists in font_CidUnicode
    has_eng = 'eng' in font_CidUnicode

    for i in font_CidUnicode.keys():
        if isinstance(i, bytes) and i[:6] == b'Random':  # Mapping CID1 with Ramdom#
            if CID1 in font_CidUnicode[i].keys():
                if isinstance(data, list):
                    data.append(font_CidUnicode[i][CID1])
                    return data

                elif isinstance(data, str):
                    data = data + font_CidUnicode[i][CID1]
                    return data
            else:
                #Check if CID1 is a valid hexadecimal value
                try:
                    cid_value = int(CID1, 16)
                    if cid_value in range(24, 94) and has_eng:
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
        if isinstance(i, bytes) and i[:6] != b'Random':  # Not mapping with Random
            if CID1 in font_CidUnicode[i].keys():
                if isinstance(data, list):
                    data.append(font_CidUnicode[i][CID1])
                    return data

                elif isinstance(data, str):
                    data = data + font_CidUnicode[i][CID1]
                    return data
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

def CMap_Error_fix_p(font_CidUnicode, CID1, data, pidx):
    """CMap error fix function with pidx (page-specific font_CidUnicode[pidx] access)"""
    past_length = len(data)

    # Check if pidx exists in font_CidUnicode
    if pidx not in font_CidUnicode:
        # If pidx doesn't exist, fallback to non-pidx version
        return CMap_Error_fix(font_CidUnicode, CID1, data)

    font_map = font_CidUnicode[pidx]

    for i in font_map.keys():
        if isinstance(i, bytes) and i[:6] == b'Random':  # Mapping CID1 with Random#
            if CID1 in font_map[i].keys():
                if isinstance(data, list):
                    data.append(font_map[i][CID1])
                    return data

                elif isinstance(data, str):
                    data = data + font_map[i][CID1]
                break
            else:
                #Check if CID1 is a valid hexadecimal value
                try:
                    cid_value = int(CID1, 16)
                    if cid_value in range(24, 94):
                        if 'eng' in font_map and CID1 in font_map['eng'].keys():
                            if isinstance(data, list):
                                data.append(font_map['eng'][CID1])
                                return data

                            elif isinstance(data, str):
                                data = data + font_map['eng'][CID1]
                except ValueError:
                    print(f"Invalid CID1 value: {CID1}")
                    if isinstance(data, list):
                        data.append(f"Invalid_CID_{CID1}")
                        return data

                    elif isinstance(data, str):
                        data = data + f"Invalid_CID_{CID1}"

    for i in font_map.keys(): #Not mapping CID1 with Random#
        if isinstance(i, bytes) and i[:6] != b'Random':  # Not mapping with Random
            if CID1 in font_map[i].keys():
                if isinstance(data, list):
                    data.append(font_map[i][CID1])
                    return data

                elif isinstance(data, str):
                    data = data + font_map[i][CID1]
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

#Visualization
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
    path_start_idx = 0  # Track where current path started

    # (1) split by b"\\n" or b"\n"
    if b"\\n" in data:
        lines = data.split(b"\\n")
    else:
        lines = data.split(b"\n")

    for idx, sent in enumerate(lines):

        try:
            tokens = sent.strip().split()
            tokens = [v for v in tokens if v] 

            if not tokens:
                continue

            if idx == 0 and len(tokens) >= 2:
                try:
                    max_y = float(tokens[1])
                    next_line = float(tokens[0])
                except ValueError:
                    pass

            cmd = tokens[-1]  # PDF 명령어 후보

            # --- has_started_path check ---
            if not has_started_path:
                if cmd == b'm' and len(tokens) >= 3:
                    path_start_idx = len(verts)  # Mark path start position
                    x, y = map(float, tokens[:-1])
                    start_x, start_y = x, y + y_length
                    verts.append((start_x, start_y))
                    codes.append(Path.MOVETO)
                    has_started_path = True
                elif cmd == b're' and len(tokens) >= 5:
                    path_start_idx = len(verts)  # Mark path start position
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
                    has_started_path = True
                else:
                    continue

            # --- (has_started_path=True) ---
            if len(tokens) >= 2:
                try:
                    x_val = float(tokens[0])
                    y_val = float(tokens[1])
                    # compare: new line check
                    if y_val <= max_y:
                        max_y = y_val
                    if x_val <= next_line:
                        next_line = x_val
                        y_length += max_y
                        max_y = 0
                except ValueError:
                    pass

            # (3) operate by cmd
            if cmd == b'l' and len(tokens) >= 3:
                # (LINETO)
                x, y = map(float, tokens[:-1])
                y += y_length
                verts.append((x, y))
                codes.append(Path.LINETO)

            elif cmd == b'c' and len(tokens) >= 7:
                # (CURVE4)
                x1, y1, x2, y2, x3, y3 = map(float, tokens[:-1])
                y1 += y_length
                y2 += y_length
                y3 += y_length
                verts.extend([(x1, y1), (x2, y2), (x3, y3)])
                codes.extend([Path.CURVE4] * 3)

            elif cmd == b'h':
                # close path (CLOSEPOLY)
                codes.append(Path.CLOSEPOLY)
                verts.append((verts[-1][0], verts[-1][1]))

            elif cmd == b'm' and len(tokens) >= 3:
                # new MOVETO
                codes.append(Path.CLOSEPOLY)
                verts.append((verts[-1][0], verts[-1][1]))

                x, y = map(float, tokens[:-1])
                y += y_length
                verts.append((x, y))
                codes.append(Path.MOVETO)

            elif cmd == b'cm':
                codes.append(Path.CLOSEPOLY)
                verts.append((verts[-1][0], verts[-1][1]))

            elif cmd == b're': #rectangle
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

            # Path painting operators
            elif cmd in [b'S', b's']:
                # S: Stroke 
                # s: Close and stroke
                if cmd == b's' and verts:
                    codes.append(Path.CLOSEPOLY)
                    verts.append((verts[-1][0], verts[-1][1]))

            elif cmd in [b'f', b'F', b'f*']:
                # f: Fill (nonzero winding number rule)
                # F: Fill 
                # f*: Fill (even-odd rule)
                pass

            elif cmd in [b'B', b'B*', b'b', b'b*']:
                # B: Fill and stroke (nonzero winding)
                # B*: Fill and stroke (even-odd)
                # b: Close, fill and stroke (nonzero winding)
                # b*: Close, fill and stroke (even-odd)
                if cmd in [b'b', b'b*'] and verts:
                    # 경로 닫기
                    codes.append(Path.CLOSEPOLY)
                    verts.append((verts[-1][0], verts[-1][1]))

            elif cmd in [b'n', b'W*', b'W']:
                # End path without filling or stroking (clipping path)
                # Remove the path from path_start_idx to current position
                if path_start_idx < len(verts):
                    del verts[path_start_idx:]
                    del codes[path_start_idx:]
                has_started_path = False  # Reset path flag

        except Exception as e:
            break

    # --- loop end ---
    if not codes:
        plt.close(fig)
        return gflag

    # visualize path 
    try:
        path = Path(verts, codes)
        patch = PathPatch(path, facecolor='none', lw=0.5)
        ax.add_patch(patch)

        if path:
            ETC.makeDir(result_path+"\\graphics")

        for vert in verts:
            ax.plot(vert[0], vert[1], 'k-')

        ax.set_aspect('equal', 'datalim')
        ax.set_xlim(-100, 700)
        ax.autoscale(enable=True, axis='y') 
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
    content = []
    data =  ''
    ms_content = []
    ms_font = []

    stream1 = re.compile(rb'\(([^\)]*\)*)\)', re.S)
    stream2 = re.compile(rb'\<([A-Fa-f0-9\\n]+\s*)\>', re.S)
    font_regex = re.compile(rb'\/(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)', re.S)
    lang_pattern = re.compile(rb'^\([a-z]{2}-[A-Z]{2}\)$')

    repl1 = []
    pos = 0
    while pos < len(c):
        m = stream1.search(c, pos)
        if not m:
            break

        block = m.group(0)

        while block.endswith(b'\\)') and m.end() < len(c):
            next_close = c.find(b')', m.end())
            if next_close == -1:
                break
            block = c[m.start():next_close+1]

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
        pos = m.start() + len(block)  

    repl2 = list(stream2.finditer(c))


    ms_content = (
        [(m.start(), 'stream1', m) for m in repl1] +
        [(m.start(), 'stream2', m) for m in repl2]
    )

    ms_content = [
        item for item in ms_content
        if not lang_pattern.match(item[2].group())
    ]

    ms_content.sort(key=lambda x: x[0])


    for h in font_regex.finditer(c):
        ms_font.append(h)

    af = 0
    ac = 0
    len_F = len(ms_font)-1
    len_C = len(ms_content)

    if ((len(ms_font) > 0 and ms_font[0].start() > ms_content[0][2].start() and prev_font_tag is not None)
            or (len(ms_font) == 0 and prev_font_tag is not None)):
        
        class _StubMatch:
            def __init__(self, tag):     
                self._tag = tag
            def start(self):             
                return 0
            def span(self):
                return (0, len(self._tag))  
            def group(self):
                tag = self._tag
                if not tag.startswith(b'/'):
                    tag = b'/' + tag
                return tag + b' '

        if len(ms_font) == 0:
            ms_font = []

        ms_font.insert(0, _StubMatch(prev_font_tag))
        len_F = len(ms_font) - 1

    while len_C > 0:
        if len_F != -1:
            while len_F > -1:
                start = ms_font[af].start()
                if af == len(ms_font)-1:
                    next = 99999
                else:
                    next = ms_font[af+1].start()
                if start <= ms_content[ac][2].start():
                    if next > ms_content[ac][2].start(): #start = current font
                        Current_F = ms_font[af].group()
                        Current_F = Current_F.replace(b"\n",b" ").split(b' ')[0][1:]

                        if ms_content[ac][1] == 'stream1':
                            data = ms_content[ac][2].group()[1:-1] #remove brackets
                            if b'\\(' in data:
                                data = data.replace(b'\\(', b'(')
                            if b'\\)' in data:
                                data = data.replace(b'\\)', b')')
                            if b'\\[' in data:
                                data = data.replace(b'\\[', b'[')
                            if b'\\]' in data:
                                data = data.replace(b'\\]', b']')
                            pattern_list = []

                            pattern = re.compile(rb'(\\\d{3}|\\x[0-9a-fA-F]{2})', re.DOTALL) 
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
                                        # (\x##) 
                                        if p.startswith(b'\\x'):
                                            hex_value = p[2:]  # \x 제거
                                            try:
                                                unicode_char = chr(int(hex_value, 16))  # U+00## 
                                                content.append(unicode_char)
                                            except:
                                                print(f" → Hex decoding failed: {p}")
                                                content.append(f"[Hex:{p}]")
                                        # (\###) 
                                        else:
                                            p = p.replace(b"\\", b"")
                                            try:
                                                unicode_char = bytes([int(p, 8)]).decode('cp1252') 
                                                content.append(unicode_char)
                                            except:
                                                print(f" → CP1252 decoding failed: {p}")
                                                content.append(f"[Escape:{p}]")
                                    else:
                                        try:
                                            content.append(p.decode())
                                        except UnicodeDecodeError:
                                            # Try Latin-1/cp1252 encoding for bytes like \xe9
                                            try:
                                                content.append(p.decode('latin-1'))
                                            except:
                                                # If Latin-1 fails, try byte-by-byte conversion
                                                for byte in p:
                                                    if byte >= 0x80:
                                                        content.append(chr(byte))
                                                    else:
                                                        try:
                                                            content.append(chr(byte))
                                                        except:
                                                            print(f" → Decode failed for byte: {byte} in {p}.")
                                                            content.append(f"[{Current_F}:{hex(byte)}]")
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
                                    # Try Latin-1/cp1252 encoding for bytes like \xe9
                                    try:
                                        content.append(data.decode('latin-1'))
                                    except:
                                        # If Latin-1 fails, try byte-by-byte conversion
                                        for byte in data:
                                            if byte >= 0x80:
                                                content.append(chr(byte))
                                            else:
                                                try:
                                                    content.append(chr(byte))
                                                except:
                                                    print(f" → Decode failed for: {data}.")
                                                    content.append(f"[{Current_F}:{data}]")
                                ac+=1
                                len_C-=1
                                if len_C == 0:
                                    break

                        elif ms_content[ac][1] == 'stream2':
                            text = ms_content[ac][2].group()
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
            for k in ms_content:
                data = ms_content[ac][2].group()[1:-1] #remove brackets
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
    stream5 = re.compile(rb'\((.*?)\)')


    for i in stream.finditer(c): #Character
        s1.append(i)
    for i in stream2.finditer(c): #whitespace or Non-alphanumeric characters
        s2.append(i)
    for i in stream3.finditer(c): #Font name
        font.append(i)                   

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
                                                    raise e  
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
                                                    raise e  
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
                                            raise e  
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
    stream5 = re.compile(rb'\((.*?)\)')

    for i in stream.finditer(c): #Character
        s1.append(i)
    for i in stream2.finditer(c): #whitespace or Non-alphanumeric characters
        s2.append(i)
    for i in stream3.finditer(c): #Font name
        font.append(i)                 

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
                                                raise e  
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
                                                raise e  
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
                                        raise e  
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
    lang_pattern = re.compile(rb'^\([a-z]{2}-[A-Z]{2}\)$')

    repl1 = []
    pos = 0
    while pos < len(c):
        m = stream1.search(c, pos)
        if not m:
            break

        block = m.group(0)

        while block.endswith(b'\\)') and m.end() < len(c):
            next_close = c.find(b')', m.end())
            if next_close == -1:
                break
            block = c[m.start():next_close+1]
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
        pos = m.start() + len(block) 

    repl2 = list(stream2.finditer(c))

    adobe_content = (
        [(m.start(), 'stream1', m) for m in repl1] +
        [(m.start(), 'stream2', m) for m in repl2]
    )

    adobe_content = [
        item for item in adobe_content
        if not lang_pattern.match(item[2].group())
    ]
    adobe_content.sort(key=lambda x: x[0])

    for h in font_regex.finditer(c):
        adobe_font.append(h)


    af = 0
    ac = 0
    len_F = len(adobe_font)-1
    len_C = len(adobe_content)

# Use prev_font_tag when the font information is truncated or not identified at all.
    if ((len(adobe_font) > 0 and adobe_font[0].start() > adobe_content[0][2].start() and prev_font_tag is not None)
            or (len(adobe_font) == 0 and prev_font_tag is not None)):
        
        class _StubMatch:
            def __init__(self, tag):     # tag = b'TT1'
                self._tag = tag
            def start(self):             
                return 0
            def span(self):
                return (0, len(self._tag))  
            def group(self):
                tag = self._tag
                if not tag.startswith(b'/'):
                    tag = b'/' + tag
                return tag + b' '

        if len(adobe_font) == 0:
            adobe_font = []

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

                        if adobe_content[ac][1] == 'stream1':  # ( ) #CID 2
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

                            pattern = re.compile(rb'(\\\d{3}|\\x[0-9a-fA-F]{2})', re.DOTALL) 
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
                                        # (\x##) 
                                        if p.startswith(b'\\x'):
                                            hex_value = p[2:]  # \x 제거
                                            try:
                                                unicode_char = chr(int(hex_value, 16))  # U+00## 유니코드로 변환
                                                content.append(unicode_char)
                                            except:
                                                #print(f" → Hex decoding failed: {p}")
                                                content.append(f"[Hex:{p}]")
                                        # (\###) 
                                        else:
                                            p = p.replace(b"\\", b"")
                                            try:
                                                unicode_char = bytes([int(p, 8)]).decode('cp1252')  #  '', " 
                                                content.append(unicode_char)
                                            except:
                                                #print(f" → CP1252 decoding failed: {p}")
                                                content.append(f"[Escape:{p}]")
                                    else:
                                        try:
                                            content.append(p.decode())
                                        except UnicodeDecodeError:
                                            # Try Latin-1/cp1252 encoding for bytes like \xe9
                                            try:
                                                content.append(p.decode('latin-1'))
                                            except:
                                                # If Latin-1 fails, try byte-by-byte conversion
                                                for byte in p:
                                                    if byte >= 0x80:
                                                        content.append(chr(byte))
                                                    else:
                                                        try:
                                                            content.append(chr(byte))
                                                        except:
                                                            print(f" → Decode failed for byte: {byte} in {p}.")
                                                            content.append(f"[{Current_F}:{hex(byte)}]")
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
                                    # Try Latin-1/cp1252 encoding for bytes like \xe9
                                    try:
                                        content.append(data.decode('latin-1'))
                                    except:
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

    final_matches = stream1_matches.copy() # Prioritize stream1 ranges 

    occupied = [(m.start(), m.end()) for m in stream1_matches] # Store stream1 range list (start~end tuples)
    for m in stream2_matches: # Check if each match in stream2 overlaps with existing stream1
        s2_start, s2_end = m.start(), m.end()
        overlapped = False
        for s1_start, s1_end in occupied:
            if not (s2_end <= s1_start or s2_start >= s1_end): # Check overlap (True if any part overlaps)
                overlapped = True
                break
        if not overlapped:
            final_matches.append(m)

    final_matches.sort(key=lambda x: x.start()) # Sort by position in original 
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
                if start <= mac_content[mc].start(): 
                    if next > mac_content[mc].start(): #start = current font
                        Current_F = mac_font[mf].group()
                        Current_F = Current_F.replace(b"\n",b" ").split(b' ')[0][1:]
                        data = mac_content[mc].group()[1:-1] #remove brackets
                        data = data.replace(b"\\x",b"")
                        if b"\\\\" in data: #ex: \\x5c
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
                                        CID1 = CID1.upper() 
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

def blocksplit(pdf, c):
    block_list = []
    last_end = 0

    for match in re.finditer(rb'BT(.*?)ET', c, re.DOTALL):
        if match.start() > last_end:
            block_list.append(c[last_end:match.start()].strip())
        block_list.append(match.group().strip())
        last_end = match.end()
    if last_end < len(c):
        block_list.append(c[last_end:].strip())  
    return block_list             

def saveas_main(decompressObj, pdf):
    all_result = []  
    cnt = 0
    prev_tag = None
    retry_flag = False  

    for i in pdf['Content']:  # Mapping per page
        c = decompressObj[i][2]  # Content data

        result = []  
        page_idx = None
        block_list = blocksplit(pdf, c)

        for _, block in enumerate(block_list):
            if re.search(rb'BT(.*?)ET', block, re.DOTALL):  # text object
                try: 
                    text, prev_tag = Mapping_MSsaveas(pdf, block, page_idx, prev_font_tag=prev_tag)
                    text = ''.join(str(t) for t in text)
                    result.append(text)
                except RetryFontMappingException as e:
                    font = e.font
                    excluded_fonts = e.excluded_fonts
                    #print(f"[↩ retry flag] '{font}' → excluded font: {excluded_fonts}")
                    pdf.setdefault("dbmapresult", {}).setdefault("exclude", {}).setdefault(font, []).extend(excluded_fonts)
                    retry_flag = True
                    break  # block_list loop excape
            else:
                matches = list(re.finditer(rb'/(\w+)\sDo', block))
                last_pos = 0
                for match in matches:
                    image_name = match.group(1).decode()
                    do_start = match.start()
                    
                    pre_do_block = block[last_pos:do_start]

                    # path object operator check
                    if (
                        re.search(rb'(?<![a-zA-Z])re', pre_do_block) or
                        re.search(rb'(?<![a-zA-Z])m', pre_do_block)
                    ):
                        # Only treat as graphic if "re\r\nW" pattern is NOT present
                        if not re.search(rb're\r\nW', pre_do_block):
                            paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
                            if any(op in pre_do_block for op in paint_ops):
                                cnt += 1
                                gflag = print_to_png(block, pdf, cnt)
                                if gflag == True:
                                    result.append(f"Graphic{cnt}")

                    result.append(image_name)
                    last_pos = match.end()
                    
                if not matches:
                    if re.search(rb'(?<![a-zA-Z])re', block) or re.search(rb'(?<![a-zA-Z])m', block): #path object
                        # Only treat as graphic if "re\r\nW" pattern is NOT present
                        if not re.search(rb're\r\nW', block):
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
            #print("[🔁 Total ContentStream retry]")
            return Mapping(decompressObj, pdf)  
        
        pattern = re.compile(r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':\s*(Cid_[0-9A-Fa-f]{4}(?:,\s*Cid_[0-9A-Fa-f]{4})*)\]")
        if any(pattern.search(text) for text in result):
            result = CMap_Error(result, pdf)
        else:
            pass

        page_text = ''.join(result) 
        all_result.append(page_text)

    text_with_placeholders, text_cleaned = resolve_failed_cid_markers(all_result, pdf)
    pdf["Text"] = text_with_placeholders
    pdf["Text_clean"] = text_cleaned
    return pdf

def printtopdf_main(decompressObj, pdf):
    all_result = []  
    cnt = 0
    prev_tag = None
    retry_flag = False  

    if 'Content_p' in pdf or 'Resouces_p' in pdf:
        for i in pdf['Content']:  # Mapping per page
            c = decompressObj[i][2]
            result = []  
            block_list = blocksplit(pdf, c)
            page_idx = None
            for pidx, obj_list in pdf.get('Content_p', {}).items():
                if i in obj_list:
                    page_idx = pidx
                    break
            for _, block in enumerate(block_list): 
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
                        
                        pre_do_block = block[last_pos:do_start]

                        # Path object operator check
                        if (
                            re.search(rb'(?<![a-zA-Z])re', pre_do_block) or
                            re.search(rb'(?<![a-zA-Z])m', pre_do_block)
                        ):
                            if not re.search(rb're\r\nW', block):                        
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
                        if not re.search(rb're\r\nW', block):
                            paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
                            if any(op in block for op in paint_ops):
                                cnt += 1
                                gflag = print_to_png(block, pdf, cnt)
                                if gflag == True:
                                    result.append(f"Graphic{cnt} ")
                    else:
                        pass
                else:
                    pass  

            pattern = re.compile(r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':\s*(Cid_[0-9A-Fa-f]{4}(?:,\s*Cid_[0-9A-Fa-f]{4})*)\]")
            if any(pattern.search(text) for text in result):
                result = CMap_Error(result, pdf, page_idx)
            else:
                pass
            
            if isinstance(result, list):
                result = ''.join(result)
            all_result.append(result)

        text_with_placeholders, text_cleaned = resolve_failed_cid_markers(all_result, pdf)
        pdf["Text"] = text_with_placeholders
        pdf["Text_clean"] = text_cleaned
        return pdf

    elif 'Page' in pdf['DamagedObj'] or 'Resources' in pdf['DamagedObj']: #pidx can be absent 
        for i in pdf['Content']:  # Mapping per page
            c = decompressObj[i][2]
            result = []  
            block_list = blocksplit(pdf, c)
            page_idx = None

            for _, block in enumerate(block_list):
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
                        
                        pre_do_block = block[last_pos:do_start]

                        # Path object operator check
                        if (
                            re.search(rb'(?<![a-zA-Z])re', pre_do_block) or
                            re.search(rb'(?<![a-zA-Z])m', pre_do_block)
                        ):
                            if not re.search(rb're\r\nW', block):
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
                        if not re.search(rb're\r\nW', block):
                            paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
                            if any(op in block for op in paint_ops):
                                cnt += 1
                                gflag = print_to_png(block, pdf, cnt)
                                if gflag == True:
                                    result.append(f"Graphic{cnt} ")
                    else:
                        pass
                else:
                    pass  

            pattern = re.compile(r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':\s*(Cid_[0-9A-Fa-f]{4}(?:,\s*Cid_[0-9A-Fa-f]{4})*)\]")
            if any(pattern.search(text) for text in result):
                result = CMap_Error(result, pdf, page_idx)
            else:
                pass
            
            if isinstance(result, list):
                result = ''.join(result)
            all_result.append(result)

        text_with_placeholders, text_cleaned = resolve_failed_cid_markers(all_result, pdf)
        pdf["Text"] = text_with_placeholders
        pdf["Text_clean"] = text_cleaned
        return pdf

    else: #no pidx (only CMap damaged can occur)
        for i in pdf['Content']:  # Mapping per page
            c = decompressObj[i][2]
            result = []  
            block_list = blocksplit(pdf, c)
            page_idx = None

            for _, block in enumerate(block_list): 
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
                        
                        pre_do_block = block[last_pos:do_start]

                        # Path object operator check
                        if (
                            re.search(rb'(?<![a-zA-Z])re', pre_do_block) or
                            re.search(rb'(?<![a-zA-Z])m', pre_do_block)
                        ):
                            if not re.search(rb're\r\nW', block):
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
                        if not re.search(rb're\r\nW', block):
                            paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
                            if any(op in block for op in paint_ops):
                                cnt += 1
                                gflag = print_to_png(block, pdf, cnt)
                                if gflag == True:
                                    result.append(f"Graphic{cnt} ")
                    else:
                        pass
                else:
                    pass 

            pattern = re.compile(r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':\s*(Cid_[0-9A-Fa-f]{4}(?:,\s*Cid_[0-9A-Fa-f]{4})*)\]")
            if any(pattern.search(text) for text in result):
                result = CMap_Error(result, pdf, page_idx)
            else:
                pass
            
            if isinstance(result, list):
                result = ''.join(result)
            all_result.append(result)

        text_with_placeholders, text_cleaned = resolve_failed_cid_markers(all_result, pdf)
        pdf["Text"] = text_with_placeholders
        pdf["Text_clean"] = text_cleaned
        return pdf

def adobe_main(decompressObj, pdf):
    all_result = []  
    cnt = 0
    prev_tag = None
    retry_flag = False  

    if 'Content_p' in pdf or 'Resouces_p' in pdf:
        for i in pdf['Content']:  # Mapping per page index
            page_idx = None
            for pidx, obj_list in pdf.get('Content_p', {}).items():
                if i in obj_list:
                    page_idx = pidx
                    break
            c = decompressObj[i][2]  # Content data
            result = []
            block_list = blocksplit(pdf, c)  

            for _, block in enumerate(block_list): 
                if re.search(rb'BT(.*?)ET', block, re.DOTALL) or (b'TJ' in block and b' Tc' in block and b' Tw' in block):  # text object
                    try: 
                        text, prev_tag = Mapping_adobe(pdf, block, page_idx, prev_font_tag=prev_tag)  # pidx
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
                        
                        pre_do_block = block[last_pos:do_start]

                        # Path object operator check
                        if (
                            re.search(rb'(?<![a-zA-Z])re', pre_do_block) or
                            re.search(rb'(?<![a-zA-Z])m', pre_do_block)
                        ):
                            if not re.search(rb're\r\nW', block):
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
                            if not re.search(rb're\r\nW', block):
                                paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
                                if any(op in block for op in paint_ops):
                                    cnt += 1
                                    gflag = print_to_png(block, pdf, cnt)
                                    if gflag == True:
                                        result.append(f"Graphic{cnt} ")
                        else:
                            pass
                    else:
                        pass 

            pattern = re.compile(
                r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':\s*(Cid_[0-9A-Fa-f]{2,4}(?:,\s*Cid_[0-9A-Fa-f]{2,4})*)\]"
            )
            if any(pattern.search(text) for text in result):
                try:
                    result = CMap_Error(result, pdf, page_idx)
                except RetryFontMappingException as e:
                    font = e.font
                    excluded_fonts = e.excluded_fonts
                    #print(f"[↩ retry flag] '{font}' → excluded font: {excluded_fonts}")
                    result = CMap_Error(result, pdf, page_idx)
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
            result = []
            block_list = blocksplit(pdf, c)
            page_idx = None  

            for _, block in enumerate(block_list): 
                if re.search(rb'BT(.*?)ET', block, re.DOTALL) or (b'TJ' in block and b' Tc' in block and b' Tw' in block):  # text object
                    try: 
                        text, prev_tag = Mapping_adobe(pdf, block, page_idx, prev_font_tag=prev_tag)  # pidx
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
                        
                        pre_do_block = block[last_pos:do_start]

                        # Path object operator check
                        if (
                            re.search(rb'(?<![a-zA-Z])re', pre_do_block) or
                            re.search(rb'(?<![a-zA-Z])m', pre_do_block)
                        ):
                            if not re.search(rb're\r\nW', block):
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
                            if not re.search(rb're\r\nW', block):
                                paint_ops = {b"f", b"f*", b"B", b"B*", b"b", b"b*", b"s", b"S"}
                                if any(op in block for op in paint_ops):
                                    cnt += 1
                                    gflag = print_to_png(block, pdf, cnt)
                                    if gflag == True:
                                        result.append(f"Graphic{cnt} ")
                        else:
                            pass
                    else:
                        pass 

            pattern = re.compile(
                r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':\s*(Cid_[0-9A-Fa-f]{2,4}(?:,\s*Cid_[0-9A-Fa-f]{2,4})*)\]"
            )
            if any(pattern.search(text) for text in result):
                try:
                    result = CMap_Error(result, pdf, page_idx)
                except RetryFontMappingException as e:
                    font = e.font
                    excluded_fonts = e.excluded_fonts
                    #print(f"[↩ retry flag] '{font}' → excluded font: {excluded_fonts}")
                    result = CMap_Error(result, pdf, page_idx)
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
    all_result = [] 
    cnt = 0
    prev_tag = None
    retry_flag = False

    for i in pdf['Content']:  # Mapping per page
        #print(f"Content {i} processing...")
        c = decompressObj[i][2]  # Content data

        result = []  # 이 페이지의 결과
        block_list = blocksplit(pdf, c)

        for _, block in enumerate(block_list):
            if re.search(rb'BT(.*?)ET', block, re.DOTALL):  # text object
                try: 
                    text, prev_tag = Mapping_MAC(pdf, block, prev_font_tag=prev_tag)
                    text = ''.join(str(t) for t in text)
                    result.append(text)
                except Exception as e:
                    break  # block_list loop break
            else:
                matches = list(re.finditer(rb'/(\w+)\sDo', block)) # Xobject
                last_pos = 0
                for match in matches:
                    image_name = match.group(1).decode()
                    do_start = match.start()
                    
                    pre_do_block = block[last_pos:do_start]

                    # Path object operator check
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

        pattern = re.compile(
            r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':\s*(Cid_[0-9A-Fa-f]{2,4}(?:,\s*Cid_[0-9A-Fa-f]{2,4})*)\]"
        )                
        if any(pattern.search(text) for text in result):
            result = CMap_Error(result, pdf)
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
    elif pdf['SaveMethod'] != "Microsoft Save as" and pdf['SaveMethod'] != "Microsoft Print to PDF" and pdf['SaveMethod'] != "Adobe" and pdf['SaveMethod'] != "MAC":
        print("📌 Generation method is Unknown. Try all mappings.")
        candidates = [
            ("Microsoft Save as", saveas_main),
            ("Microsoft Print to PDF", printtopdf_main),
            ("Adobe", adobe_main),
            ("MAC", MAC_main),
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
                print(f"✅ {name} Generation method mapping success")
            except Exception as e:
                print(f"❌ {name} Generation method mapping fail: {e}")

        pdf['CandidateResults'] = all_results  

    else: #pdf['SaveMethod'] == "Unknown"
        print("❗ Mapping is not processed.")
    return pdf

def resolve_failed_cid_markers(text_input, pdf):
    """
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
                    #print(f"[{font_tag}:Cid_{cid}] → '{replacement}'")
                    resolved_chars.append(replacement)
                    cleaned_chars.append(replacement)
                else:
                    # fail → placeholder vs " "
                    resolved_chars.append(f"[{font_tag}:Cid_{cid}]")
                    cleaned_chars.append(" ")

            text_with_placeholders = text_with_placeholders.replace(full_match, ''.join(resolved_chars))
            text_cleaned = text_cleaned.replace(full_match, ''.join(cleaned_chars))

        return text_with_placeholders, text_cleaned

    if isinstance(text_input, str):
        return resolve_in_text(text_input)
    elif isinstance(text_input, list):
        placeholders, cleaned = zip(*(resolve_in_text(t) for t in text_input))
        return list(placeholders), list(cleaned)
    else:
        return text_input, text_input