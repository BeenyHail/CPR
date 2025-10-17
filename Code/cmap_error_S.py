from llmquery import query_ollama
import sqlite3
import time
import re

class RetryFontMappingException(Exception):
    def __init__(self, font, excluded_fonts):
        self.font = font
        self.excluded_fonts = excluded_fonts
        super().__init__(f"Retry font mapping for {font}")

def cmap_total_damage(font, cids, pdf):
    font_name_map = pdf.get('FontNameMap', {})
    dbmapresult = pdf.setdefault('dbmapresult', {})
    font_CidUnicode = pdf.setdefault('FontCMap', {})
    excluded_fonts = pdf.get("dbmapresult", {}).get("exclude", {}).get(font, [])
    db_path = "fontdb.db"
    pattern = r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':Cid_[0-9A-Fa-f]{4}\]"

    def try_db_mapping(font_name, cids, db_path):
        """Map CIDs from DB based on font_name column and perform LLM validation"""
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
                    return None  # CID missing

            conn.close()
            result_str = ''.join(glyphs)
            #print(f"[📄 DB Font '{font_name}' Mapping Result]: {result_str}")
            if 'glyph' in result_str:
                response = "X"
            elif result_str == " ":
                return result_str
            elif len(cids) == 1:
                cid = cids[0]
                if len(result_str) <= 1:
                    #print("Single CID character -> return")
                    return f"[{font}:Cid_{cid}]"
            elif len(result_str) == 1:
                cid = cids[0]
                if len(result_str) <= 1:
                    #print("Single CID character -> return")
                    return f"[{font}:Cid_{cid}]"
            elif len(result_str) <= 2 and (' ' in result_str or result_str.strip() == ''):
                cid = cids[0]
                return f"[{font}:Cid_{cid}]"
            else:
                response = query_ollama(result_str)
                #print(f"[🤖 LLM Judgment]: {response}")

            if response == "O":
                return result_str
            else:
                return None
        except Exception as e:
            #print(f"[❌ DB Mapping Error]: {e}")
            return None

    # 0. First compare with cmap in already mapped font_CidUnicode

    for candidate_font, cmap in font_CidUnicode.items():
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
            elif len(cids) == 1:
                cid = cids[0]
                if len(result) <= 1:
                    return f"[{font}:Cid_{cid}]"
            else:

                response = query_ollama(result)

                if response == "O":

                    if isinstance(candidate_font, str):
                        candidate_font = candidate_font.encode('utf-8')
                    if isinstance(font, str):
                        font = font.encode('utf-8')
                    dbmapresult.setdefault(font, {})
                    dbmapresult[font][candidate_font] = dbmapresult[font].get(candidate_font, 0) + 1
                    if dbmapresult[font][candidate_font] >= 5:

                        if candidate_font in font_CidUnicode:
                            font_CidUnicode[font] = font_CidUnicode[candidate_font]
                            return result

                        try:
                            conn = sqlite3.connect(db_path)
                            cursor = conn.cursor()
                            cursor.execute(f"SELECT CID, [{candidate_font}] FROM GlyphOrder")
                            rows = cursor.fetchall()
                            conn.close()

                            cmap = {}
                            for cid_hex, glyph in rows:
                                if glyph is None:
                                    continue
                                cid_clean = cid_hex.replace("0x", "").upper()
                                cmap[cid_clean] = glyph

                            if isinstance(font, str):
                                font = font.encode()
                            font_CidUnicode[font] = cmap

                        except Exception as e:
                            return result 
                    return result 
                else: 
                    continue

    # 1. Find actual font name for the font tag (F1, etc.) from FontNameMap
    if font in font_name_map:
        real_font = font_name_map[font]
        if real_font in excluded_fonts:
            return None
        result = try_db_mapping(real_font, cids, db_path)
        if re.fullmatch(pattern, result):
            return result
        elif result is not None:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Read all CID and corresponding font column
                cursor.execute(f"SELECT CID, [{real_font}] FROM GlyphOrder")
                rows = cursor.fetchall()
                conn.close()

                cmap = {}
                for cid_hex, glyph in rows:
                    if glyph is None:
                        continue

                    cid_clean = cid_hex.replace("0x", "").upper()
                    cmap[cid_clean] = glyph  # CID is in 'ABCD' format
                if isinstance(font, str):
                    font = font.encode('utf-8')
                font_CidUnicode[font] = cmap
                return result

            except Exception as e:
                print(f"[❌ DB Mapping Error]: {e}")

            return result

    # 2-1. Try fonts with previous success records first
    if font in dbmapresult:
        for candidate_font, success_count in dbmapresult[font].items():
            if candidate_font in excluded_fonts:
                continue
            if candidate_font in font_CidUnicode:
                # Check if all CIDs exist in the candidate font's cmap
                if all(cid in font_CidUnicode[candidate_font] for cid in cids):
                    result = ''.join(font_CidUnicode[candidate_font][cid] for cid in cids)
                    continue
                else:
                    continue
            else:
                result = try_db_mapping(candidate_font, cids, db_path)
            pattern = r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':Cid_[0-9A-Fa-f]{4}\]"
            if result:
                if re.fullmatch(pattern, result):
                    return result
                else:
                    dbmapresult.setdefault(font, {})
                    dbmapresult[font][candidate_font] += 1
                    if dbmapresult[font][candidate_font] >= 5:
                        #print(f"[Font Confirmed: {font} → {candidate_font}]") Reload entire cmap from DB
                        try:
                            conn = sqlite3.connect(db_path)
                            cursor = conn.cursor()
                            cursor.execute(f"SELECT CID, [{candidate_font}] FROM GlyphOrder")
                            rows = cursor.fetchall()
                            conn.close()

                            cmap = {}
                            for cid_hex, glyph in rows:
                                if glyph is None:
                                    continue
                                cid_clean = cid_hex.replace("0x", "").upper()
                                cmap[cid_clean] = glyph

                            if isinstance(font, str):
                                font = font.encode()
                            font_CidUnicode[font] = cmap

                        except Exception as e:
                            return result
                    return result 
            else: 
                continue

    # 2-2. Try based on FontName list
    for fname in pdf.get('FontName', []):
        if fname in dbmapresult.get(font, {}) or fname in excluded_fonts:
            continue
        result = try_db_mapping(fname, cids, db_path)
        if result:
            if re.fullmatch(pattern, result):
                return result
            else:
                dbmapresult.setdefault(font, {})[fname] = 1
                return result
        else: 
            continue

    # 3. Try iterating through all DB font columns
    try:
        start_time = time.time()
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

    # 4. Output CID as is when mapping fails
    try:
        font_tag = font if isinstance(font, bytes) else font.encode()

        if len(cids) == 1:
            marker = f"[{font_tag}:Cid_{cids[0]}]"
            return marker 
        else:
            formatted = [f"Cid_{cid}" for cid in cids]
            marker = f"[{font_tag}:" + ', '.join(formatted) + "]"
            return marker
    except Exception as e:
        return ""  # fallback
    

def cmap_part_damage(font, cid, pdf):
    retry_flag = False
    dbmapresult = pdf.setdefault('dbmapresult', {})
    excluded_fonts = dbmapresult.setdefault('exclude', {}).setdefault(font, [])
    font_CidUnicode = pdf.setdefault('FontCMap', {})

    # 1. Check if a confirmed mapping currently exists
    if font in font_CidUnicode:
        confirmed_font = None
        for candidate, count in dbmapresult.get(font, {}).items():
            if isinstance(count, int) and count >= 3:
                confirmed_font = candidate
                break

        if confirmed_font:
            # 2. Consider as incorrect and add to exclusion list
            font = font if isinstance(font, bytes) else font.encode()
            excluded_fonts = dbmapresult.setdefault('exclude', {}).setdefault(font, [])
            if confirmed_font not in excluded_fonts:
                excluded_fonts.append(confirmed_font)
            dbmapresult[font] = {}  # Reset confirmed record
            font_CidUnicode.pop(font, None)

            # 3. Retry from the beginning (exclude existing font)
            retry_flag = True
            return None, retry_flag
        
        else:  # CMap partially damaged
            current_cmap = font_CidUnicode[font]
            db_path = "fontdb.db"
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(GlyphOrder)")
                columns = [row[1] for row in cursor.fetchall() if row[1] != 'CID']
                conn.close()

                for col in columns:
                    if col in dbmapresult.get('exclude', {}).get(font, []):
                        continue  # Skip excluded fonts

                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT CID, [{col}] FROM GlyphOrder")
                    rows = cursor.fetchall()
                    conn.close()

                    db_cmap = {
                        cid_hex.replace("0x", "").upper(): glyph
                        for cid_hex, glyph in rows if glyph is not None
                    }

                    # Check if it completely matches with current cmap
                    match = all(
                        db_cmap.get(cid) == uni for cid, uni in current_cmap.items()
                    )
                    if match:
                        font_CidUnicode[font] = db_cmap
                        return db_cmap.get(cid, None), retry_flag

            except Exception as e:
                print(f"[❌ Error While Comparing CMap]: {e}")

    else:
        cmap_total_damage(font, cid, pdf)

def damage_mac(font, cids, pdf):
    font_CidUnicode = pdf.setdefault('FontCMap', {})
    dbmapresult = pdf.setdefault('dbmapresult', {})   
    db_path = pdf.get('db_path', 'FontDB.sqlite')     

    if not isinstance(font_CidUnicode, dict) or not font_CidUnicode:
        #print("font_toUnicode is empty, mapping not possible")
        return "".join(f"[{font}:Cid_{cid}]" for cid in cids)

    def _build_result(cmap, cids_, font, allow_missing=False):
        try:
            result_chars = []
            missing_cids = []
            for cid in cids_:
                cid_hex = str(cid)
                if cid_hex in cmap:
                    result_chars.append(cmap[cid_hex])
                else:
                    if allow_missing:
                        result_chars.append(" ")  
                        missing_cids.append(cid)
                        if len(missing_cids) > 4:
                            return None  
                    else:
                        return None
            return "".join(result_chars), missing_cids
        except KeyError:
            return None

    for candidate_font, cmap in font_CidUnicode.items():
        if candidate_font == font:
            continue
        if not isinstance(cmap, dict):
            continue

        result = None
        missing_cids = []

        tmp = _build_result(cmap, cids, font, allow_missing=False)
        if tmp:
            result, missing_cids = tmp
        else:
            if len(cids) >= 10:
                tmp = _build_result(cmap, cids, font, allow_missing=True)
                if tmp:
                    result, missing_cids = tmp

        if result is None:
            continue

        if "glyph" in result:
            continue
        if result == " ":
            return result
        if len(cids) == 1 and len(result) <= 1:
            cid = cids[0]
            return f"[{font}:Cid_{cid}]"

        # === LLM Judgment ===
        try:
            response = query_ollama(result)  # 'O' or 'X'
        except Exception as e:
            response = "X"

        if response == "O":

            if missing_cids:
                fixed_result = []
                for cid, ch in zip(cids, result):
                    if cid in missing_cids:
                        fixed_result.append(f"[{font}:Cid_{cid}]")
                    else:
                        fixed_result.append(ch)
                result = "".join(fixed_result)
            # Mapping success → success record
            if isinstance(candidate_font, str):
                candidate_font = candidate_font.encode('utf-8')
            if isinstance(font, str):
                font = font.encode('utf-8')

            dbmapresult.setdefault(font, {})
            dbmapresult[font][candidate_font] = dbmapresult[font].get(candidate_font, 0) + 1

            if dbmapresult[font][candidate_font] >= 5:

                # Font confirmed. Copy existing cmap
                if candidate_font in font_CidUnicode:
                    font_CidUnicode[font] = font_CidUnicode[candidate_font]
                    return result

                # Load cmap from DB
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT CID, [{candidate_font.decode()}] FROM GlyphOrder")
                    rows = cursor.fetchall()
                    conn.close()

                    cmap_new = {}
                    for cid_hex, glyph in rows:
                        if glyph is None:
                            continue
                        cid_clean = cid_hex.replace("0x", "").upper().zfill(4)
                        cmap_new[cid_clean] = glyph

                    font_CidUnicode[font] = cmap_new

                except Exception as e:
                    return result

            return result
        else:
            continue

    # === All candidates failed → return placeholder ===
    if len(cids) == 1:
        return f"[{font}:Cid_{cids[0]}]"
    else:
        return "".join(f"[{font}:Cid_{cid}]" for cid in cids)