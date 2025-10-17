from llmquery import query_ollama
import sqlite3
import time
import re

class RetryFontMappingException(Exception):
    def __init__(self, font, excluded_fonts):
        self.font = font
        self.excluded_fonts = excluded_fonts
        super().__init__(f"Retry font mapping for {font}")

def none_damaged(font_tag, cid_list, pdf, pidx=None):
    font_CidUnicode_all = pdf.setdefault("FontCMap", {})

    # 1) Determine cmap area based on pidx
    if pidx is not None:
        font_CidUnicode = font_CidUnicode_all.setdefault(pidx, {})
    else:
        font_CidUnicode = font_CidUnicode_all  # Global cmap

    # 2) If all CIDs exist in existing cmap, use as is
    if font_tag in font_CidUnicode:
        cmap = font_CidUnicode[font_tag]
        if all(cid in cmap for cid in cid_list):
            mapped = ''.join(cmap[cid] for cid in cid_list)
            return mapped  # Success return

    # 3) Some CIDs missing → call damaged()
    if len(cid_list) == 1:
        return f"[{font_tag}:Cid_{cid_list[0]}]"
    else:
        mapped = damaged(font_tag, cid_list, pdf, pidx)

    # 4) If damaged result is valid, update cmap
    if isinstance(mapped, str) and not re.match(r"\[.*?:Cid_", mapped):
        font_CidUnicode.setdefault(font_tag, {})
        for cid, char in zip(cid_list, mapped):
            font_CidUnicode[font_tag][cid] = char

    return mapped  # Success or fallback marker return

def page_damaged(font_cid_map, pdf, unknown_pidx=None):
    result = []
    font_CidUnicode_all = pdf.get('FontCMap', {})
    dbmapresult = pdf.setdefault("dbmapresult", {})
    valid_pidx = None

    # 1. Iterate font_CidUnicode based on pidx
    for pidx_candidate, cmap_dict in font_CidUnicode_all.items():
        if not isinstance(pidx_candidate, int) or not isinstance(cmap_dict, dict):
            continue  # Not pidx → next

        trial_result = []
        all_valid = True

        for item in font_cid_map:
            if isinstance(item, tuple):
                font_tag, cid_group = item
                if font_tag in cmap_dict and all(cid in cmap_dict[font_tag] for cid in cid_group):
                    mapped = ''.join(cmap_dict[font_tag][cid] for cid in cid_group)
                    trial_result.append(mapped)
                else:
                    all_valid = False
                    break
            else:
                trial_result.append(item)  # Text like 'Graphic2 '

        if not all_valid:
            continue

        joined = ''.join([s for s in trial_result if isinstance(s, str)])
        print(f"[🔍 pidx {pidx_candidate} mapping result] {joined}")
        response = query_ollama(joined)
        print(f"[🔍 LLM judgment: pidx {pidx_candidate}] → {response}")

        if response == "O":
            return trial_result

    # 2. Check global font_CidUnicode without pidx
    trial_result = []
    all_valid = True

    for item in font_cid_map:
        if isinstance(item, tuple):
            font_tag, cid_group = item
            cmap = font_CidUnicode_all.get(font_tag)
            if cmap and isinstance(cmap, dict) and all(cid in cmap for cid in cid_group):
                mapped = ''.join(cmap[cid] for cid in cid_group)
                trial_result.append(mapped)
            else:
                all_valid = False
                break
        else:
            trial_result.append(item)

    if all_valid:
        joined = ''.join([s for s in trial_result if isinstance(s, str)])
        response = query_ollama(joined)
        print(f"[🔍 LLM judgment: using global cmap] → {response} | {joined}")

        if response == "O":
            return trial_result

    # Failed case
    print("[⚠️ All cmap application failed → damaged handling]")
    return None

def resource_damaged(font, cids, pdf, pidx):
    """
    - Based on damaged()
    - Register confirmed cmap to FontCMap[pidx] when mapping succeeds
    - Record mapping success history by pidx
    """

    font_name_map = pdf.get("FontNameMap", {})
    dbmapresult = pdf.setdefault("dbmapresult", {})

    # Get font_CidUnicode by pidx
    font_CidUnicode_all = pdf.setdefault("FontCMap", {})
    font_CidUnicode = font_CidUnicode_all.setdefault(pidx, {})

    excluded_fonts = dbmapresult.get("exclude", {}).get(font, [])
    db_path = "fontdb.db"
    pattern = r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':Cid_[0-9A-Fa-f]{4}\]"

    def try_db_mapping(font_name, cids, db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            glyphs = []
            for cid in cids:
                cursor.execute(f"SELECT [{font_name}] FROM GlyphOrder WHERE CID = ?", (f"0x{cid}",))
                result = cursor.fetchone()
                if result and result[0] is not None:
                    glyphs.append(result[0])
                else:
                    conn.close()
                    return None
            conn.close()

            result_str = "".join(glyphs)
            #print(f"[📄 DB font '{font_name}' mapping result]: {result_str}")

            if "glyph" in result_str:
                return None
            elif result_str == " ":
                return result_str
            elif len(cids) == 1 and len(result_str) <= 1:
                return f"[{font}:Cid_{cids[0]}]"
            elif len(result_str) <= 2 and (result_str.strip() == "" or " " in result_str):
                return f"[{font}:Cid_{cids[0]}]"
            else:
                response = query_ollama(result_str)
                #print(f"[🤖 LLM judgment]: {response}")
                return result_str if response == "O" else None
        except Exception as e:
            return None

    # (1) Attempt to reuse existing cmap
    for candidate_font, cmap in font_CidUnicode_all.items():
        if isinstance(candidate_font, bytes) and isinstance(cmap, dict):
            if candidate_font in excluded_fonts:
                continue
            if all(cid in cmap for cid in cids):
                result = "".join(cmap[cid] for cid in cids)
                if 'glyph' in result:
                    response = "X"
                elif result == " ":
                    return result
                elif len(cids) == 1 and len(result) <= 1:
                    return f"[{font}:Cid_{cids[0]}]"
                else:
                    #print(f"[🧪 Mapping attempt] font={font}, candidate_font={candidate_font}, result={result}")
                    response = query_ollama(result)
                    #print(f"[🤖 LLM judgment]: {response}")
                    if response == "O":
                        dbmapresult.setdefault(font, {})
                        entry = dbmapresult[font].get(candidate_font, {"count": 0, "pidx_list": []})
                        entry["count"] += 1
                        if pidx not in entry["pidx_list"]:
                            entry["pidx_list"].append(pidx)
                        dbmapresult[font][candidate_font] = entry

                        # Register to FontCMap[pidx] when font is confirmed
                        if entry["count"] >= 5:
                            font_CidUnicode[font] = cmap
                            #print(f"[✅ Font confirmed and cmap reuse completed: {font} → {candidate_font}, pidx={pidx}]")

                        return result

    # (2) Attempt to reuse cmap from other pidx
    for other_pidx, cmap_dict in font_CidUnicode_all.items():
        if not isinstance(cmap_dict, dict):
            continue
        if isinstance(other_pidx, int) and other_pidx != pidx:
            for candidate_font, cmap in cmap_dict.items():
                if candidate_font in excluded_fonts or font == candidate_font:
                    continue
                if isinstance(cmap, dict) and all(cid in cmap for cid in cids):
                    result = "".join(cmap[cid] for cid in cids)
                    if 'glyph' in result:
                        response = "X"
                    elif result == " ":
                        return result
                    elif len(cids) == 1 and len(result) <= 1:
                        return f"[{font}:Cid_{cids[0]}]"
                    else:
                        #print(f"[🧪 {candidate_font} cmap (from pidx {other_pidx}) mapping result] {result}")
                        response = query_ollama(result)
                        #print(f"[🤖 LLM judgment]: {response}")
                        if response == "O":
                            dbmapresult.setdefault(font, {})
                            entry = dbmapresult[font].get(candidate_font, {"count": 0, "pidx_list": []})
                            entry["count"] += 1
                            if pidx not in entry["pidx_list"]:
                                entry["pidx_list"].append(pidx)
                            dbmapresult[font][candidate_font] = entry

                            if entry["count"] >= 5:
                                font_CidUnicode[font] = cmap
                                #print(f"[✅ Font confirmed and pidx cmap reuse completed: {font} ← {candidate_font}, pidx={pidx}]")

                            return result

    # (3) FontNameMap-based mapping
    if font in font_name_map:
        real_font = font_name_map[font]
        if real_font not in excluded_fonts:
            #print(f"[📌 Attempting FontNameMap-based mapping] {font} → {real_font}")
            result = try_db_mapping(real_font, cids, db_path)
            if result is not None and not re.fullmatch(pattern, result):
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT CID, [{real_font}] FROM GlyphOrder")
                    rows = cursor.fetchall()
                    conn.close()
                    cmap = {cid_hex.replace("0x", "").upper(): glyph for cid_hex, glyph in rows if glyph}
                    font_CidUnicode[font] = cmap
                    #print(f"[✅ Full cmap registration completed for {font} with {real_font}]")
                except Exception as e:
                    return result
            return result

    # (4) dbmapresult-based mapping
    if font in dbmapresult:
        for candidate_font, meta in dbmapresult[font].items():
            if candidate_font in excluded_fonts:
                continue
            #print(f"[🔁 Attempting previously successful font] {font} → {candidate_font}")
            result = try_db_mapping(candidate_font, cids, db_path)
            if result and not re.fullmatch(pattern, result):
                meta["count"] = meta.get("count", 0) + 1
                meta.setdefault("pidx_list", []).append(pidx)
                dbmapresult[font][candidate_font] = meta

                if meta["count"] >= 5:
                    try:
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        cursor.execute(f"SELECT CID, [{candidate_font}] FROM GlyphOrder")
                        rows = cursor.fetchall()
                        conn.close()
                        cmap = {cid_hex.replace("0x", "").upper(): glyph for cid_hex, glyph in rows if glyph}
                        font_CidUnicode[font] = cmap
                    except Exception as e:
                        return result
                return result

    # (5) Mapping by brute-force checking all DB columns
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(GlyphOrder)")
        columns = [row[1] for row in cursor.fetchall() if row[1] != "CID"]
        conn.close()
    except Exception as e:
        return None

    for col in columns:
        if col in excluded_fonts or col in dbmapresult.get(font, {}):
            continue
        result = try_db_mapping(col, cids, db_path)
        if result:
            if not re.fullmatch(pattern, result):
                dbmapresult.setdefault(font, {})[col] = {"count": 1, "pidx_list": [pidx]}
                return result

    # (6) Final mapping failed → Output CID marker
    if len(cids) == 1:
        return f"[{font}:Cid_{cids[0].upper()}]"
    else:
        formatted = ", ".join(f"Cid_{cid.upper()}" for cid in cids)
        return f"[{font}:{formatted}]"


def damaged(font, cids, pdf, pidx):
    font_name_map = pdf.get('FontNameMap', {})
    dbmapresult = pdf.setdefault('dbmapresult', {})
    
    # Separate font_CidUnicode by pidx
    font_CidUnicode_all = pdf.setdefault('FontCMap', {})
    font_CidUnicode = font_CidUnicode_all.setdefault(pidx, {})
    
    excluded_fonts = pdf.get("dbmapresult", {}).get("exclude", {}).get(font, [])
    db_path = "fontdb.db"
    pattern = r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':Cid_[0-9A-Fa-f]{4}\]"

    def try_db_mapping(font_name, cids, db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            glyphs = []
            for cid in cids:
                cursor.execute(f"SELECT [{font_name}] FROM GlyphOrder WHERE CID = ?", (f"0x{cid}",))
                result = cursor.fetchone()
                if result and result[0] is not None:
                    glyphs.append(result[0])
                else:
                    conn.close()
                    return None
            conn.close()
            result_str = ''.join(glyphs)
            #print(f"[📄 DB font '{font_name}' mapping result]: {result_str}")
            if 'glyph' in result_str:
                response = "X"
            elif result_str == " ":
                return result_str
            elif len(cids) == 1 and len(result_str) <= 1:
                return f"[{font}:Cid_{cids[0]}]"
            elif len(result_str) <= 2 and (' ' in result_str or result_str.strip() == ''):
                return f"[{font}:Cid_{cids[0]}]"
            else:
                response = query_ollama(result_str)
                #print(f"[🤖 LLM judgment]: {response}")
            return result_str if response == "O" else None
        except Exception as e:
            return None

    # (1) mapping with existing font_CidUnicode cmap
    for candidate_font, cmap in font_CidUnicode_all.items():
        if isinstance(candidate_font, bytes) and isinstance(cmap, dict):
            if candidate_font in excluded_fonts:
                continue
            if all(cid in cmap for cid in cids):
                result = ''.join(cmap[cid] for cid in cids)
                if 'glyph' in result:
                    response = "X"
                elif result == " ":
                    return result
                elif len(cids) == 1 and len(result) <= 1:
                    return f"[{font}:Cid_{cids[0]}]"
                else:
                    #print(f"[🧪 {candidate_font} cmap mapping result] {result}")
                    response = query_ollama(result)
                    #print(f"[🤖 LLM judgment]: {response}")
                    if response == "O":
                        dbmapresult.setdefault(font, {})
                        entry = dbmapresult[font].get(candidate_font, {"count": 0, "pidx_list": []})
                        entry["count"] += 1

                        if pidx is not None and pidx not in entry["pidx_list"]:
                            entry["pidx_list"].append(pidx)

                        dbmapresult[font][candidate_font] = entry

                        # confirmed font → register to FontCMap[pidx]
                        if entry["count"] >= 5:
                            font_CidUnicode[font] = cmap
                        return result

    # (2) Check all cmap within pidx structure
    for other_pidx, cmap_dict in font_CidUnicode_all.items():
        if not isinstance(cmap_dict, dict):
            continue
        if isinstance(other_pidx, int) and other_pidx != pidx:
            for candidate_font, cmap in cmap_dict.items():
                if font == candidate_font:
                    continue
                if candidate_font in excluded_fonts:
                    continue
                if isinstance(cmap, dict) and all(cid in cmap for cid in cids):
                    result = ''.join(cmap[cid] for cid in cids)
                    if 'glyph' in result:
                        response = "X"
                    elif result == " ":
                        return result
                    elif len(cids) == 1 and len(result) <= 1:
                        return f"[{font}:Cid_{cids[0]}]"
                    else:
                        #print(f"[🧪 {candidate_font} cmap (from pidx {other_pidx}) mapping result] {result}")
                        response = query_ollama(result)
                        #print(f"[🤖 LLM judgment]: {response}")
                        if response == "O":
                            dbmapresult.setdefault(font, {})
                            dbmapresult[font][candidate_font] = dbmapresult[font].get(candidate_font, 0) + 1
                            if dbmapresult[font][candidate_font] >= 5:
                                font_CidUnicode[font] = cmap
                                #print(f"[✅ Font confirmed and pidx cmap reuse completed] {font} ← {candidate_font} (pidx {other_pidx})")
                            return result
                    
    #(3) Mapping based on FontNameMap 
    if font in font_name_map:
        real_font = font_name_map[font]
        if real_font in excluded_fonts:
            return None
        result = try_db_mapping(real_font, cids, db_path)
        if result is not None and not re.fullmatch(pattern, result):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(f"SELECT CID, [{real_font}] FROM GlyphOrder")
                rows = cursor.fetchall()
                conn.close()
                cmap = {cid_hex.replace("0x", "").upper(): glyph for cid_hex, glyph in rows if glyph}
                font_CidUnicode[font] = cmap
            except Exception as e:
                return result
        return result

    #(4) mapping based on success record
    if font in dbmapresult:
        for candidate_font, success_count in dbmapresult[font].items():
            if candidate_font in excluded_fonts:
                continue

            cmap_dict = font_CidUnicode_all.get(pidx, {}).get(candidate_font)
            if cmap_dict:
                result = ''.join(cmap_dict.get(cid, "") for cid in cids)
            else:
                result = try_db_mapping(candidate_font, cids, db_path)

            if result and not re.fullmatch(pattern, result):
                dbmapresult.setdefault(font, {})
                val = dbmapresult[font].get(candidate_font)

                # new entry
                if val is None:
                    # pidx → dict
                    if isinstance(candidate_font, bytes) and candidate_font == b'eng':
                        dbmapresult[font][candidate_font] = {"count": 1, "pidx_list": [pidx]}
                    else:
                        dbmapresult[font][candidate_font] = 1

                # int → count 
                elif isinstance(val, int):
                    dbmapresult[font][candidate_font] = val + 1

                # dict → count/pidx_list 
                elif isinstance(val, dict):
                    val["count"] = val.get("count", 0) + 1
                    if pidx is not None and pidx not in val.get("pidx_list", []):
                        val.setdefault("pidx_list", []).append(pidx)
                    dbmapresult[font][candidate_font] = val

                # count extract and check
                entry = dbmapresult[font][candidate_font]
                count_val = entry["count"] if isinstance(entry, dict) else entry

                if count_val >= 5:
                    try:
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        cursor.execute(f"SELECT CID, [{candidate_font}] FROM GlyphOrder")
                        rows = cursor.fetchall()
                        conn.close()
                        cmap = {cid_hex.replace("0x", "").upper(): glyph for cid_hex, glyph in rows if glyph}
                        font_CidUnicode[font] = cmap
                    except Exception as e:
                        return result

                return result

    #(5) mapping by fontname list
    for fname in pdf.get('FontName', []):
        if fname in dbmapresult.get(font, {}) or fname in excluded_fonts:
            continue
        result = try_db_mapping(fname, cids, db_path)
        if result and not re.fullmatch(pattern, result):
            dbmapresult.setdefault(font, {})[fname] = 1
            return result

    #(6) brute-force all columns
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(GlyphOrder)")
        columns = [row[1] for row in cursor.fetchall() if row[1] != 'CID']
        conn.close()
    except Exception as e:
        return

    for col in columns:
        if col in dbmapresult.get(font, {}) or col in excluded_fonts:
            continue
        result = try_db_mapping(col, cids, db_path)
        if result:
            if re.fullmatch(pattern, result):
                return result
            else:
                dbmapresult.setdefault(font, {})[col] = 1
                return result
        else: 
            continue

    #(7) mapping failed → return CID marker
    try:
        if len(cids) == 1:
            marker = f"[{font}:Cid_{cids[0]}]"
            return marker
        else:
            formatted = [f"Cid_{cid}" for cid in cids]
            marker = f"[{font}:" + ', '.join(formatted) + "]"
            return marker
    except Exception as e:
        return ""