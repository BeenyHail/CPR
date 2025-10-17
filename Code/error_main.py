import cmap_error_S
import cmap_error_P
from llmquery import query_ollama
import re

class RetryFontMappingException(Exception):
    def __init__(self, font, excluded_fonts):
        self.font = font
        self.excluded_fonts = excluded_fonts
        super().__init__(f"Retry font mapping for {font}")

def Error_main_S(c, pdf):
    result = []
    font_cid_map = clist_integrate(c)  # [(fonttag, [cid, cid, ...]), ...]
    font_CidUnicode = pdf['FontCMap']

    for item in font_cid_map:
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], bytes) and isinstance(item[1], list):
            font, cids = item

            # 1) Cmap total damage
            if font not in font_CidUnicode:
                #print(f"[ERROR: MissingCMap] font: {font}")
                mapped = cmap_error_S.cmap_total_damage(font, cids, pdf)
                if isinstance(mapped, list):
                    mapped = ''.join(mapped)
                result.append(mapped)
            else:
                # 2) Cmap partial damage
                mapped_text = []
                for cid in cids:
                    try:
                        if cid not in font_CidUnicode[font]:
                            #print(f"[ERROR: MissingCID] font: {font}, cid: {cid}")
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
                        #print(f"[ERROR: MissingCMapAccess] font: {font}, cid: {cid}")
                        mapped_text.append(f"[{font}:Cid_{cid}]")

                result.append(''.join(mapped_text))

        else:
            result.append(item)

    return ''.join(result)

def Error_main_P(c, pdf, pidx):
    result = []
    font_cid_map = clist_integrate(c)
    dbmapresult = pdf.setdefault('dbmapresult', {})
    exclude_map = dbmapresult.setdefault('exclude', {})
    forced_marker_fonts = set()

    # 1. When pidx is assigned to content & pidx also exists in FontCMap
    if pidx is not None and pidx in pdf.get("FontCMap", {}):
        for item in font_cid_map:
            if isinstance(item, tuple):
                font_tag, cid_group = item
                merged_result = cmap_error_P.none_damaged(font_tag, cid_group, pdf, pidx)
                result.append(merged_result)
            else:
                result.append(item)  
        return result

    # 2. When pidx is assigned to content & pidx does not exist in FontCMap (Only Resources damaged, Page intact)
    elif pidx is not None and pidx not in pdf.get("FontCMap", {}):
        pdf.setdefault("FontCMap", {})[pidx] = {}
        for item in font_cid_map:
            if isinstance(item, tuple):
                font_tag, cid_group = item
                if font_tag in pdf['FontCMap'].get(pidx, {}):  # Font confirmed and cmap reused
                    for cid_raw in cid_group:
                        cid = cid_raw.replace('Cid_', '')  # Remove prefix
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
                                #print(f"[⚠️ Error Detected] CID '{cid}' missing from previously confirmed font '{confirmed_font}' for '{font_tag}'")
                                # Add to exclusion list
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
                result.append(item)  # Add plain text as is
        return result
    
    # 3. When pidx is not assigned to content (None)
    else:
        #print("[⚠️ Content Damaged] No pidx")
        result = cmap_error_P.page_damaged(font_cid_map, pdf, pidx)
        if result is not None:
            return result
        else:
            #print(f"[📛 page_damaged failed → fallback to damaged]")
            result = []

        for item in font_cid_map:
            if isinstance(item, tuple):
                font_tag, cid_group = item
                if (cid_group[:3] == ["0001", "0002", "0003"]) and (not font_cid_map): # Case where custom CID + FontCMap are completely missing
                    forced_marker_fonts.add(font_tag)
                    formatted = [f"Cid_{cid_raw.replace('Cid_', '')}" for cid_raw in cid_group]
                    marker = f"[{font_tag}:" + ', '.join(formatted) + "]"
                    print(f"[🔎 CID List Marker After Mapping Failure]: {marker}")
                    result.append(marker)
                else:
                    merged_result = cmap_error_P.damaged(font_tag, cid_group, pdf, pidx)
                    result.append(merged_result)
            else:
                result.append(item)  # Add plain text as is
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
            if font_tag in pdf['FontCMap'].get(pidx, {}):  # Font confirmed and cmap reused
                for cid_raw in cid_group:
                    cid = cid_raw.replace('Cid_', '')  # Remove prefix
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
                            print(f"[⚠️ Error Detected] CID '{cid}' missing from previously confirmed font '{confirmed_font}' for '{font_tag}'")
                            # Add to exclusion list
                            font_b = font_tag
                            confirmed_b = confirmed_font if isinstance(confirmed_font, bytes) else confirmed_font.encode()
                            excluded_fonts = dbmapresult.setdefault('exclude', {}).setdefault(font_b, [])
                            if confirmed_b not in excluded_fonts:
                                excluded_fonts.append(confirmed_b)
                        raise RetryFontMappingException(font_tag, pdf['dbmapresult']['exclude'].get(font_tag, []))
            else:
                if (cid_group[:3] == ["0001", "0002", "0003"]) and (not font_cid_map): # Case where custom CID + FontCMap are completely missing
                    forced_marker_fonts.add(font_tag)
                    formatted = [f"Cid_{cid_raw.replace('Cid_', '')}" for cid_raw in cid_group]
                    marker = f"[{font_tag}:" + ', '.join(formatted) + "]"
                    #print(f"[🔎 CID List Marker After Mapping Failure]: {marker}")
                    result.append(marker)
                else: 
                    merged_result = cmap_error_P.none_damaged(font_tag, cid_group, pdf, pidx)
                    result.append(merged_result)
        else:
            result.append(item)  
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
                # Font exists but check individual CID
                mapped_text = []
                for cid in cid_group:
                    try:
                        mapped_text.append(font_CidUnicode[font][cid])
                    except KeyError:
                        #print(f"[ERROR: MissingCMapAccess] font: {font}, cid: {cid}")
                        mapped_text.append(f"[{font}:Cid_{cid}]")

                result.append(''.join(mapped_text))   
        else:
            result.append(item)  

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

            # If there is a plain string (always add including spaces)
            if start > pos:
                plain_text = text[pos:start]
                if last_font is not None and current_cids:
                    result.append((last_font, current_cids))
                    last_font, current_cids = None, []
                result.append(plain_text)  # Always append without strip()

            # Process CID block
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

        # Process remaining plain text (including spaces)
        if pos < len(text):
            plain_text = text[pos:]
            if last_font is not None and current_cids:
                result.append((last_font, current_cids))
                last_font, current_cids = None, []
            result.append(plain_text)

    # Process last CID
    if last_font is not None and current_cids:
        result.append((last_font, current_cids))

    # Post-merge same font_tags (merge consecutive CIDs)
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