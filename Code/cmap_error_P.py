from llmquery import query_ollama
import sqlite3
import time
import re

class RetryFontMappingException(Exception):
    def __init__(self, font, excluded_fonts):
        self.font = font
        self.excluded_fonts = excluded_fonts
        super().__init__(f"Retry font mapping for {font}")

def error_identify_P(font_CidUnicode, c):
    grouped = extract_font_cid_sequence_grouped(c)
    errors = []

    for block in grouped:
        font = block['font']
        if not isinstance(font, bytes):
            font = font.encode()
        cids = block['cids']

        # (1) 폰트 cmap이 아예 없을 때 → cids 모두 4자리 단위로 쪼개서 반환
        if font not in font_CidUnicode:
            print(f"[ERROR: MissingCMap] font: {font}")

            all_chunks = []
            for cid_raw in cids:
                chunks = [cid_raw[i:i+4] for i in range(0, len(cid_raw), 4)]
                all_chunks.extend(chunks)

            errors.append({
                "font": font,
                "cids": all_chunks,  # 분할된 cid 리스트
                "cid": None,
                "error": "MissingCMap"
            })
            continue

        # (2) 일부 CID가 없을 때
        cmap = font_CidUnicode[font]
        for cid_raw in cids:
            chunks = [cid_raw[i:i+4] for i in range(0, len(cid_raw), 4)]
            for chunk in chunks:
                if chunk not in cmap:
                    print(f"[ERROR: MissingCID] font: {font}, cid: {chunk}")
                    errors.append({
                        "font": font,
                        "cids": None,
                        "cid": chunk,
                        "error": "MissingCID"
                    })

    return errors


def extract_font_cid_sequence_grouped(c):
    font_regex = re.compile(rb'/(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)\s+\d+\.?\d*\s+Tf')
    cid_regex = re.compile(rb'<([A-Fa-f0-9\s\\n]+)>')

    result = []
    current_font = None
    current_cids = []

    lines = c.split(b'\n')

    for line in lines:
        font_match = font_regex.search(line)
        if font_match:
            new_font = font_match.group(1).decode('utf-8')
            if current_font != new_font:
                if current_font and current_cids:
                    result.append({"font": current_font, "cids": current_cids})
                current_font = new_font
                current_cids = []

        cid_matches = cid_regex.findall(line)
        for cid in cid_matches:
            if current_font:
                cid_clean = cid.decode('utf-8').replace('\n', '').replace(' ', '')
                current_cids.append(cid_clean)

    if current_font and current_cids:
        result.append({"font": current_font, "cids": current_cids})

    return result

def none_damaged(font_tag, cid_list, pdf, pidx=None):
    font_CidUnicode_all = pdf.setdefault("FontCMap", {})

    # 1️⃣ pidx에 따라 cmap 영역 결정
    if pidx is not None:
        font_CidUnicode = font_CidUnicode_all.setdefault(pidx, {})
    else:
        font_CidUnicode = font_CidUnicode_all  # 전역 cmap

    # 2️⃣ 기존 cmap에 모든 CID가 존재하면 그대로 사용
    if font_tag in font_CidUnicode:
        cmap = font_CidUnicode[font_tag]
        if all(cid in cmap for cid in cid_list):
            mapped = ''.join(cmap[cid] for cid in cid_list)
            return mapped  # ✅ 성공 반환

    # 3️⃣ 일부 CID 누락 → damaged() 호출
    if len(cid_list) == 1:
        return f"[{font_tag}:Cid_{cid_list[0]}]"
    else:
        mapped = damaged(font_tag, cid_list, pdf, pidx)

    # 4️⃣ damaged 결과가 유효하면 cmap 갱신
    if isinstance(mapped, str) and not re.match(r"\[.*?:Cid_", mapped):
        font_CidUnicode.setdefault(font_tag, {})
        for cid, char in zip(cid_list, mapped):
            font_CidUnicode[font_tag][cid] = char

    return mapped  # ✅ 성공 or fallback 마커 반환

def page_damaged(font_cid_map, pdf, unknown_pidx=None):
    result = []
    font_CidUnicode_all = pdf.get('FontCMap', {})
    dbmapresult = pdf.setdefault("dbmapresult", {})
    valid_pidx = None

    # 1️⃣ pidx 기반 font_CidUnicode 순회
    for pidx_candidate, cmap_dict in font_CidUnicode_all.items():
        if not isinstance(pidx_candidate, int) or not isinstance(cmap_dict, dict):
            continue  # pidx 아님 → 다음으로

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
                trial_result.append(item)  # 'Graphic2 ' 같은 텍스트

        if not all_valid:
            continue

        joined = ''.join([s for s in trial_result if isinstance(s, str)])
        print(f"[🔍 pidx {pidx_candidate} 매핑 결과] {joined}")
        response = query_ollama(joined)
        print(f"[🔍 LLM 판정: pidx {pidx_candidate}] → {response}")

        if response == "O":
            return trial_result

    # 2️⃣ pidx 없이 전역 font_CidUnicode 검사
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
        print(f"[🔍 LLM 판정: global cmap 사용] → {response} | {joined}")

        if response == "O":
            return trial_result

    # 실패한 경우
    print("[⚠️ 모든 cmap 적용 실패 → damaged 처리]")
    return None

def resource_damaged(font, cids, pdf, pidx):
    """
    - damaged() 기반
    - 매핑 성공 시 FontCMap[pidx]에 확정 cmap 등록
    - 매핑 성공 이력을 pidx별로 기록
    """

    font_name_map = pdf.get("FontNameMap", {})
    dbmapresult = pdf.setdefault("dbmapresult", {})

    # ✅ pidx별 font_CidUnicode 가져오기
    font_CidUnicode_all = pdf.setdefault("FontCMap", {})
    font_CidUnicode = font_CidUnicode_all.setdefault(pidx, {})

    excluded_fonts = dbmapresult.get("exclude", {}).get(font, [])
    db_path = "glyphorder.db"
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
            print(f"[📄 DB 폰트 '{font_name}' 매핑 결과]: {result_str}")

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
                print(f"[🤖 LLM 판정]: {response}")
                return result_str if response == "O" else None
        except Exception as e:
            print(f"[❌ DB 매핑 에러]: {e}")
            return None

    # 🔍 (1) 기존 cmap 재사용 시도
    print("[🔍 기존 font_CidUnicode cmap과 우선 매핑 시도]")
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
                    print(f"[🧪 매핑 시도] font={font}, candidate_font={candidate_font}, result={result}")
                    response = query_ollama(result)
                    print(f"[🤖 LLM 판정]: {response}")
                    if response == "O":
                        dbmapresult.setdefault(font, {})
                        entry = dbmapresult[font].get(candidate_font, {"count": 0, "pidx_list": []})
                        entry["count"] += 1
                        if pidx not in entry["pidx_list"]:
                            entry["pidx_list"].append(pidx)
                        dbmapresult[font][candidate_font] = entry

                        # ✅ 폰트 확정 시 FontCMap[pidx] 등록
                        if entry["count"] >= 5:
                            font_CidUnicode[font] = cmap
                            print(f"[✅ 폰트 확정 및 cmap 재사용 완료: {font} → {candidate_font}, pidx={pidx}]")

                        return result

    # 🔍 (2) 다른 pidx cmap 재사용 시도
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
                        print(f"[🧪 {candidate_font} cmap (from pidx {other_pidx}) 매핑 결과] {result}")
                        response = query_ollama(result)
                        print(f"[🤖 LLM 판정]: {response}")
                        if response == "O":
                            dbmapresult.setdefault(font, {})
                            entry = dbmapresult[font].get(candidate_font, {"count": 0, "pidx_list": []})
                            entry["count"] += 1
                            if pidx not in entry["pidx_list"]:
                                entry["pidx_list"].append(pidx)
                            dbmapresult[font][candidate_font] = entry

                            if entry["count"] >= 5:
                                font_CidUnicode[font] = cmap
                                print(f"[✅ 폰트 확정 및 pidx cmap 재사용 완료: {font} ← {candidate_font}, pidx={pidx}]")

                            return result

    # 🔍 (3) FontNameMap 기반 매핑
    if font in font_name_map:
        real_font = font_name_map[font]
        if real_font not in excluded_fonts:
            print(f"[📌 FontNameMap 기반 매핑 시도] {font} → {real_font}")
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
                    print(f"[✅ {font}에 {real_font} cmap 전체 등록 완료]")
                except Exception as e:
                    print(f"[❌ DB 매핑 오류]: {e}")
            return result

    # 🔍 (4) dbmapresult 기반 매핑
    if font in dbmapresult:
        for candidate_font, meta in dbmapresult[font].items():
            if candidate_font in excluded_fonts:
                continue
            print(f"[🔁 이전 성공 폰트 시도] {font} → {candidate_font}")
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
                        print(f"[✅ {font}에 {candidate_font} cmap 전체 등록 완료]")
                    except Exception as e:
                        print(f"[❌ cmap 불러오기 실패]: {e}")
                return result

    # 🔍 (5) 전체 DB 컬럼 순회 매핑
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(GlyphOrder)")
        columns = [row[1] for row in cursor.fetchall() if row[1] != "CID"]
        conn.close()
    except Exception as e:
        print(f"[❌ DB 컬럼 불러오기 실패]: {e}")
        return None

    for col in columns:
        if col in excluded_fonts or col in dbmapresult.get(font, {}):
            continue
        print(f"[🔎 전체 DB 폰트 매핑 시도] {font} → {col}")
        result = try_db_mapping(col, cids, db_path)
        if result:
            if not re.fullmatch(pattern, result):
                dbmapresult.setdefault(font, {})[col] = {"count": 1, "pidx_list": [pidx]}
                return result

    # 🔍 (6) 최종 매핑 실패 → CID 마커 출력
    print("[⛔ 최종 매핑 실패. CID로 출력]")
    if len(cids) == 1:
        return f"[{font}:Cid_{cids[0].upper()}]"
    else:
        formatted = ", ".join(f"Cid_{cid.upper()}" for cid in cids)
        return f"[{font}:{formatted}]"


def damaged(font, cids, pdf, pidx):
    font_name_map = pdf.get('FontNameMap', {})
    dbmapresult = pdf.setdefault('dbmapresult', {})
    
    # 🔁 pidx별로 font_CidUnicode 분리
    font_CidUnicode_all = pdf.setdefault('FontCMap', {})
    font_CidUnicode = font_CidUnicode_all.setdefault(pidx, {})
    
    excluded_fonts = pdf.get("dbmapresult", {}).get("exclude", {}).get(font, [])
    db_path = "glyphorder.db"
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
            print(f"[📄 DB 폰트 '{font_name}' 매핑 결과]: {result_str}")
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
                print(f"[🤖 LLM 판정]: {response}")
            return result_str if response == "O" else None
        except Exception as e:
            print(f"[❌ DB 매핑 에러]: {e}")
            return None

    print("[🔍 기존 font_CidUnicode cmap과 우선 매핑 시도]")
    for candidate_font, cmap in font_CidUnicode_all.items():
        if isinstance(candidate_font, bytes) and isinstance(cmap, dict):
            if candidate_font in excluded_fonts:
                print(f"[⛔ 제외된 폰트: {candidate_font}, 생략]")
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
                    print(f"[🧪 {candidate_font} cmap 매핑 결과] {result}")
                    response = query_ollama(result)
                    print(f"[🤖 LLM 판정]: {response}")
                    if response == "O":
                        dbmapresult.setdefault(font, {})
                        entry = dbmapresult[font].get(candidate_font, {"count": 0, "pidx_list": []})
                        entry["count"] += 1

                        if pidx is not None and pidx not in entry["pidx_list"]:
                            entry["pidx_list"].append(pidx)

                        dbmapresult[font][candidate_font] = entry

                        # 폰트 확정 조건
                        if entry["count"] >= 5:
                            font_CidUnicode[font] = cmap
                            print(f"[✅ 폰트 확정 및 cmap 재사용 완료: {font} → {candidate_font}, pidx={pidx}]")
                        return result

    # 🔁 (2) pidx 구조 내의 모든 cmap 검사
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
                        print(f"[🧪 {candidate_font} cmap (from pidx {other_pidx}) 매핑 결과] {result}")
                        response = query_ollama(result)
                        print(f"[🤖 LLM 판정]: {response}")
                        if response == "O":
                            dbmapresult.setdefault(font, {})
                            dbmapresult[font][candidate_font] = dbmapresult[font].get(candidate_font, 0) + 1
                            if dbmapresult[font][candidate_font] >= 5:
                                font_CidUnicode[font] = cmap
                                print(f"[✅ 폰트 확정 및 pidx cmap 재사용 완료] {font} ← {candidate_font} (pidx {other_pidx})")
                            return result
                    

    if font in font_name_map:
        real_font = font_name_map[font]
        if real_font in excluded_fonts:
            print(f"[⛔ 제외된 폰트: {real_font}, FontNameMap 기반 생략]")
            return None
        print(f"[📌 FontNameMap 기반 매핑 시도] {font} → {real_font}")
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
                print(f"[✅ {font}에 {real_font} cmap 전체 등록 완료]")
            except Exception as e:
                print(f"[❌ DB 매핑 오류]: {e}")
        return result

    if font in dbmapresult:
        for candidate_font, success_count in dbmapresult[font].items():
            if candidate_font in excluded_fonts:
                continue
            print(f"[🔁 이전 성공 폰트 우선 시도] {font} → {candidate_font} ({success_count}회)")

            cmap_dict = font_CidUnicode_all.get(pidx, {}).get(candidate_font)
            if cmap_dict:
                result = ''.join(cmap_dict.get(cid, "") for cid in cids)
            else:
                result = try_db_mapping(candidate_font, cids, db_path)

            if result and not re.fullmatch(pattern, result):
                dbmapresult.setdefault(font, {})
                val = dbmapresult[font].get(candidate_font)

                # ① 신규 등록
                if val is None:
                    # pidx가 있는 경우 → dict 구조로 저장
                    if isinstance(candidate_font, bytes) and candidate_font == b'eng':
                        dbmapresult[font][candidate_font] = {"count": 1, "pidx_list": [pidx]}
                    else:
                        dbmapresult[font][candidate_font] = 1

                # ② int → 단순 증가
                elif isinstance(val, int):
                    dbmapresult[font][candidate_font] = val + 1

                # ③ dict → count/pidx_list 갱신
                elif isinstance(val, dict):
                    val["count"] = val.get("count", 0) + 1
                    if pidx is not None and pidx not in val.get("pidx_list", []):
                        val.setdefault("pidx_list", []).append(pidx)
                    dbmapresult[font][candidate_font] = val

                # ✅ count 추출 (dict/int 모두 대응)
                entry = dbmapresult[font][candidate_font]
                count_val = entry["count"] if isinstance(entry, dict) else entry

                # ✅ 5회 이상이면 cmap 확정
                if count_val >= 5:
                    try:
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        cursor.execute(f"SELECT CID, [{candidate_font}] FROM GlyphOrder")
                        rows = cursor.fetchall()
                        conn.close()
                        cmap = {cid_hex.replace("0x", "").upper(): glyph for cid_hex, glyph in rows if glyph}
                        font_CidUnicode[font] = cmap
                        print(f"[✅ {font}에 {candidate_font} cmap 전체 등록 완료]")
                    except Exception as e:
                        print(f"[❌ 확정 cmap 불러오기 실패]: {e}")

                return result

    for fname in pdf.get('FontName', []):
        if fname in dbmapresult.get(font, {}) or fname in excluded_fonts:
            continue
        print(f"[🔍 FontName 우선 매핑 시도] {font} → {fname}")
        result = try_db_mapping(fname, cids, db_path)
        if result and not re.fullmatch(pattern, result):
            dbmapresult.setdefault(font, {})[fname] = 1
            return result

    print("[📚 전체 DB 폰트 순회 매핑 시도]")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(GlyphOrder)")
        columns = [row[1] for row in cursor.fetchall() if row[1] != 'CID']
        conn.close()
    except Exception as e:
        print(f"[❌ 컬럼 불러오기 실패]: {e}")
        return

    for col in columns:
        if col in dbmapresult.get(font, {}) or col in excluded_fonts:
            continue
        print(f"[🔎 일반 매핑 시도] {font} → {col}")
        result = try_db_mapping(col, cids, db_path)
        if result:
            if re.fullmatch(pattern, result):
                return result
            else:
                dbmapresult.setdefault(font, {})[col] = 1
                return result
        else: 
            continue

    print("[⛔ 최종 매핑 실패. CID로 출력합니다.]")
    try:
        if len(cids) == 1:
            marker = f"[{font}:Cid_{cids[0]}]"
            print(f"[🪧 포맷 마커 반환] {marker}")
            return marker
        else:
            formatted = [f"Cid_{cid}" for cid in cids]
            marker = f"[{font}:" + ', '.join(formatted) + "]"
            print(f"[🔎 매핑 실패 후 CID 목록 마커]: {marker}")
            return marker
    except Exception as e:
        print(f"[⚠️ CID 출력 중 오류 발생]: {e}")
        return ""

def cmap_total_damage(font, cids, pdf):
    font_name_map = pdf.get('FontNameMap', {})
    dbmapresult = pdf.setdefault('dbmapresult', {})
    font_CidUnicode = pdf.setdefault('FontCMap', {})
    excluded_fonts = pdf.get("dbmapresult", {}).get("exclude", {}).get(font, [])
    db_path = "glyphorder.db"
    pattern = r"\[b'(C2_\d+|T1_\d+|TT\d+|F\d+|R\d+)':Cid_[0-9A-Fa-f]{4}\]"

    def try_db_mapping(font_name, cids, db_path):
        """DB에서 CID들을 font_name 컬럼 기준으로 매핑하고 LLM 검증까지 수행"""
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
                    return None  # CID 누락

            conn.close()
            result_str = ''.join(glyphs)
            print(f"[📄 DB 폰트 '{font_name}' 매핑 결과]: {result_str}")
            if 'glyph' in result_str:
                response = "X"
            elif result_str == " ":
                return result_str
            elif len(cids) == 1:
                cid = cids[0]
                if len(result_str) <= 1:
                    print("CID 한글자 -> 반환")
                    return f"[{font}:Cid_{cid}]"
            elif len(result_str) == 1:
                cid = cids[0]
                if len(result_str) <= 1:
                    print("CID 한글자 -> 반환")
                    return f"[{font}:Cid_{cid}]"
            elif len(result_str) <= 2 and (' ' in result_str or result_str.strip() == ''):
                cid = cids[0]
                return f"[{font}:Cid_{cid}]"
            else:
                response = query_ollama(result_str)
                print(f"[🤖 LLM 판정]: {response}")

            if response == "O":
                return result_str
            else:
                return None
        except Exception as e:
            print(f"[❌ DB 매핑 에러]: {e}")
            return None

    # 0. 이미 매핑된 font_CidUnicode 내의 cmap과 우선 비교
    print("[🔍 기존 font_CidUnicode cmap과 우선 매핑 시도]")

    for candidate_font, cmap in font_CidUnicode.items():
        if font == candidate_font:
            continue  # 자기 자신은 제외
        if candidate_font in excluded_fonts:
            print(f"[⛔ 제외된 폰트: {candidate_font}, 매핑 생략]")
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
                print(f"[🧪 {candidate_font} cmap 매핑 결과] {result}")
                response = query_ollama(result)
                print(f"[🤖 LLM 판정]: {response}")
                if response == "O":
                    # 매핑 성공 → 현재 font에 매핑 결과 반영
                    if isinstance(candidate_font, str):
                        candidate_font = candidate_font.encode('utf-8')
                    if isinstance(font, str):
                        font = font.encode('utf-8')
                    dbmapresult.setdefault(font, {})
                    dbmapresult[font][candidate_font] = dbmapresult[font].get(candidate_font, 0) + 1
                    if dbmapresult[font][candidate_font] >= 5:
                        print(f"[✅ 폰트 확정: {font} → {candidate_font}]")
                        # 1️⃣ 기존 font_CidUnicode에서 cmap 존재하면 재사용
                        if candidate_font in font_CidUnicode:
                            font_CidUnicode[font] = font_CidUnicode[candidate_font]
                            print(f"[♻️ 기존 cmap 재사용 완료] {font} ← {candidate_font}")
                            return result

                        # 2️⃣ 그렇지 않으면 DB에서 candidate_font 컬럼을 기준으로 cmap 생성
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
                            print(f"[📥 DB cmap 등록 완료] {font} ← {candidate_font}")

                        except Exception as e:
                            print(f"[❌ 확정 cmap 불러오기 실패]: {e}")
                    return result 
                else: 
                    continue

    # 1. FontNameMap에서 해당 폰트 태그(F1 등)에 대한 실제 폰트명 찾기
    if font in font_name_map:
        real_font = font_name_map[font]
        if real_font in excluded_fonts:
            print(f"[⛔ 제외된 폰트: {real_font}, FontNameMap 기반 생략]")
            return None
        print(f"[📌 FontNameMap 기반 매핑 시도] {font} → {real_font}")
        result = try_db_mapping(real_font, cids, db_path)
        if re.fullmatch(pattern, result):
            return result
        elif result is not None:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # CID와 해당 폰트 컬럼 전체 읽기
                cursor.execute(f"SELECT CID, [{real_font}] FROM GlyphOrder")
                rows = cursor.fetchall()
                conn.close()

                cmap = {}
                for cid_hex, glyph in rows:
                    if glyph is None:
                        continue

                    cid_clean = cid_hex.replace("0x", "").upper()
                    cmap[cid_clean] = glyph  # CID는 'ABCD' 형태
                if isinstance(font, str):
                    font = font.encode('utf-8')
                # 변환된 cmap 저장
                font_CidUnicode[font] = cmap
                print(f"[✅ {font}에 {real_font} cmap 전체 등록 완료]")
                return result

            except Exception as e:
                print(f"[❌ DB 매핑 오류]: {e}")

            return result

    # 2-1. 이전에 성공한 기록이 있는 폰트 우선 시도
    if font in dbmapresult:
        for candidate_font, success_count in dbmapresult[font].items():
            if candidate_font in excluded_fonts:
                print(f"[⛔ 제외된 폰트: {candidate_font}, 매핑 생략]")
                continue
            print(f"[🔁 이전 성공 폰트 우선 시도] {font} → {candidate_font} ({success_count}회)")
            if candidate_font in font_CidUnicode: 
                result = ''.join(font_CidUnicode[candidate_font][cid] for cid in cids)
                print(f"[✅ 기존 cmap 매핑] [{font}:{', '.join('Cid_' + cid for cid in cids)}] → '{result}'")
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
                        print(f"[✅ 폰트 확정: {font} → {candidate_font}]")
                            # ⬇️ DB에서 cmap 전체 다시 로드
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
                            print(f"[✅ {font}에 {candidate_font} cmap 전체 등록 완료]")

                        except Exception as e:
                            print(f"[❌ 확정 cmap 불러오기 실패]: {e}")
                    return result 
            else: 
                continue

    # 2-2. FontName 목록 기반 시도
    for fname in pdf.get('FontName', []):
        if fname in dbmapresult.get(font, {}) or fname in excluded_fonts:
            continue
        print(f"[🔍 FontName 우선 매핑 시도] {font} → {fname}")
        result = try_db_mapping(fname, cids, db_path)
        if result:
            if re.fullmatch(pattern, result):
                return result
            else:
                dbmapresult.setdefault(font, {})[fname] = 1
                return result
        else: 
            continue

    # 3. 전체 DB 폰트 컬럼 순회 시도
    print("[📚 전체 DB 폰트 순회 매핑 시도]")
    try:
        start_time = time.time()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(GlyphOrder)")
        columns = [row[1] for row in cursor.fetchall() if row[1] != 'CID']
        conn.close()
    except Exception as e:
        print(f"[❌ 컬럼 불러오기 실패]: {e}")
        return

    for col in columns:
        if col in dbmapresult.get(font, {}) or col in excluded_fonts:
            continue
        print(f"[🔎 일반 매핑 시도] {font} → {col}")
        result = try_db_mapping(col, cids, db_path)
        if result:
            if re.fullmatch(pattern, result):
                return result
            else:
                dbmapresult.setdefault(font, {})[col] = 1
                return result
        else: 
            continue

    # 4. 매핑 실패 시 CID 그대로 출력
    print("[⛔ 최종 매핑 실패. CID로 출력합니다.]")
    try:
        font_tag = font.decode() if isinstance(font, bytes) else font

        if len(cids) == 1:
            marker = f"[{font_tag}:Cid_{cids[0].upper()}]"
            print(f"[🪧 포맷 마커 반환] {marker}")
            return marker  # ✅ 단일 CID는 마커 형태로 반환
        else:
            formatted = []
            for cid in cids:
                if cid.isdigit():
                    formatted.append("Cid_" + format(int(cid), '04x').upper())
                else:
                    formatted.append(f"Cid_{cid.upper()}")
            marker = f"[{font_tag}:" + ', '.join(formatted) + "]"
            print(f"[🔎 매핑 실패 후 CID 목록 마커]: {marker}")
            return marker
    except Exception as e:
        print(f"[⚠️ CID 출력 중 오류 발생]: {e}")
        return ""  # fallback
    

def cmap_part_damage(font, cid, pdf):
    retry_flag = False
    dbmapresult = pdf.setdefault('dbmapresult', {})
    excluded_fonts = dbmapresult.setdefault('exclude', {}).setdefault(font, [])
    font_CidUnicode = pdf.setdefault('FontCMap', {})

    # 1. 현재 확정된 매핑이 존재하는지 확인
    if font in font_CidUnicode:
        confirmed_font = None
        for candidate, count in dbmapresult.get(font, {}).items():
            if isinstance(count, int) and count >= 3:
                confirmed_font = candidate
                break

        if confirmed_font:
            print(f"[⚠️ 오류 감지] '{font}'에 대해 이전에 확정된 폰트 '{confirmed_font}'에서 CID '{cid}'가 누락됨")

            # 2. 잘못된 것으로 간주하고 제외 목록에 추가
            font = font if isinstance(font, bytes) else font.encode()
            excluded_fonts = dbmapresult.setdefault('exclude', {}).setdefault(font, [])
            if confirmed_font not in excluded_fonts:
                excluded_fonts.append(confirmed_font)
            dbmapresult[font] = {}  # 확정 기록 초기화
            font_CidUnicode.pop(font, None)

            # 3. 처음부터 다시 재시도 (기존 폰트는 제외)
            print(f"[🔁 재시도] '{font}' 매핑을 처음부터 다시 시도 (제외: {excluded_fonts})")
            # 반드시 전체 stream에서 다시 호출하도록 외부 로직에서 처리
            retry_flag = True
            return None, retry_flag
    else:
        cmap_total_damage(font, cid, pdf)

def cmap_total_damage_print(font, cids, pdf):

    font = font if isinstance(font, bytes) else font.encode()
    cids = [cid.upper() for cid in cids]

    font_CidUnicode = pdf.setdefault('FontCMap', {})
    dbmapresult = pdf.setdefault('dbmapresult', {})
    font_name_map_all = pdf.get('FontNameMap', {})
    page_idx_map = font_CidUnicode.get('page_idx', {})

    # 0. 결과 저장용
    result = None

    # 1. 이미 있는 FontCMap 내의 cmap들과 매핑 시도
    print("[🔍 기존 FontCMap cmap들과 매핑 시도]")
    for idx, cmap_group in font_CidUnicode.items():
        if isinstance(idx, int) and isinstance(cmap_group, dict):
            cmap = cmap_group.get(font)
            if cmap and all(cid in cmap for cid in cids):
                temp = ''.join(cmap[cid] for cid in cids)
                response = query_ollama(temp)
                print(f"[🧪 기존 cmap[{idx}][{font}] 매핑 결과] {temp} → {response}")
                if response == "O":
                    return temp  # 성공

    # 새 페이지 인덱스 부여
    current_idx = max([i for i in font_CidUnicode if isinstance(i, int)], default=-1) + 1
    font_CidUnicode[current_idx] = {}

    # 2. FontName 기반 DB 매핑 시도
    print("[📌 FontName 기반 매핑 시도]")
    candidates = []

    # 2-1. FontNameMap에서 추출
    fname = font_name_map_all.get(font)
    if fname:
        candidates.append(fname)

    # 2-2. 이전 매핑 성공 이력
    if font in dbmapresult:
        candidates.extend([f for f, v in dbmapresult[font].items() if v >= 1])

    # 2-3. FontName 목록 전체
    for f in pdf.get('FontName', []):
        if f not in candidates:
            candidates.append(f)

    def try_db_mapping(font_name, cids):
        try:
            conn = sqlite3.connect("glyphorder.db")
            cursor = conn.cursor()
            glyphs = []
            for cid in cids:
                cursor.execute(f"SELECT [{font_name}] FROM GlyphOrder WHERE CID = ?", (f"0x{cid}",))
                r = cursor.fetchone()
                if r and r[0]:
                    glyphs.append(r[0])
                else:
                    conn.close()
                    return None
            conn.close()
            temp = ''.join(glyphs)
            resp = query_ollama(temp)
            print(f"[📄 DB 매핑 결과: {font_name}] {temp} → {resp}")
            if resp == "O":
                return temp
        except Exception as e:
            print(f"[❌ DB 오류: {e}]")
        return None

    for fname in candidates:
        temp_result = try_db_mapping(fname, cids)
        if temp_result:
            font_CidUnicode[current_idx][font] = {}
            conn = sqlite3.connect("glyphorder.db")
            cursor = conn.cursor()
            cursor.execute(f"SELECT CID, [{fname}] FROM GlyphOrder")
            rows = cursor.fetchall()
            conn.close()
            cmap = {row[0].replace("0x", "").upper(): row[1] for row in rows if row[1]}
            font_CidUnicode[current_idx][font] = cmap
            dbmapresult.setdefault(font, {})[fname] = dbmapresult.get(font, {}).get(fname, 0) + 1
            return temp_result

    # 3. 전체 DB 열 순회 시도
    print("[📚 전체 DB 폰트 열 순회]")
    try:
        conn = sqlite3.connect("glyphorder.db")
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(GlyphOrder)")
        cols = [r[1] for r in cursor.fetchall() if r[1] != "CID"]
        conn.close()
    except Exception as e:
        print(f"[❌ DB 열 불러오기 실패]: {e}")
        return None

    for col in cols:
        if col in dbmapresult.get(font, {}):
            continue
        temp_result = try_db_mapping(col, cids)
        if temp_result:
            font_CidUnicode[current_idx][font] = {}
            conn = sqlite3.connect("glyphorder.db")
            cursor = conn.cursor()
            cursor.execute(f"SELECT CID, [{col}] FROM GlyphOrder")
            rows = cursor.fetchall()
            conn.close()
            cmap = {row[0].replace("0x", "").upper(): row[1] for row in rows if row[1]}
            font_CidUnicode[current_idx][font] = cmap
            dbmapresult.setdefault(font, {})[col] = 1
            return temp_result

    # 4. 매핑 실패 시 CID 그대로 출력
    print("[⛔ 최종 매핑 실패. CID로 출력합니다.]")
    try:
        font_tag = font.decode() if isinstance(font, bytes) else font

        if len(cids) == 1:
            marker = f"[{font_tag}:Cid_{cids[0].upper()}]"
            print(f"[🪧 포맷 마커 반환] {marker}")
            return marker  # ✅ 단일 CID는 마커 형태로 반환
        else:
            formatted = []
            for cid in cids:
                if cid.isdigit():
                    formatted.append("Cid_" + format(int(cid), '04x').upper())
                else:
                    formatted.append(f"Cid_{cid.upper()}")
            marker = f"[{font_tag}:" + ', '.join(formatted) + "]"
            print(f"[🔎 매핑 실패 후 CID 목록 마커]: {marker}")
            return marker
    except Exception as e:
        print(f"[⚠️ CID 출력 중 오류 발생]: {e}")
        return ""  # fallback