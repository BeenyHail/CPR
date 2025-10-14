from llmquery import query_ollama
import sqlite3
import time
import re

class RetryFontMappingException(Exception):
    def __init__(self, font, excluded_fonts):
        self.font = font
        self.excluded_fonts = excluded_fonts
        super().__init__(f"Retry font mapping for {font}")

def error_identify_S(font_CidUnicode, c):
    errors = []

    for font, cids in c:
        if not isinstance(font, bytes):
            font = font.encode()

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
        font_tag = font if isinstance(font, bytes) else font.encode()

        if len(cids) == 1:
            marker = f"[{font_tag}:Cid_{cids[0]}]"
            print(f"[🪧 포맷 마커 반환] {marker}")
            return marker  # ✅ 단일 CID는 마커 형태로 반환
        else:
            formatted = [f"Cid_{cid}" for cid in cids]
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
        
        else:  # CMap 일부 손상
            current_cmap = font_CidUnicode[font]
            db_path = "glyphorder.db"
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(GlyphOrder)")
                columns = [row[1] for row in cursor.fetchall() if row[1] != 'CID']
                conn.close()

                for col in columns:
                    if col in dbmapresult.get('exclude', {}).get(font, []):
                        continue  # 제외된 폰트는 건너뜀

                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT CID, [{col}] FROM GlyphOrder")
                    rows = cursor.fetchall()
                    conn.close()

                    db_cmap = {
                        cid_hex.replace("0x", "").upper(): glyph
                        for cid_hex, glyph in rows if glyph is not None
                    }

                    # 현재 cmap과 완전히 일치하는지 비교
                    match = all(
                        db_cmap.get(cid) == uni for cid, uni in current_cmap.items()
                    )
                    if match:
                        print(f"[📌 CMap 보완] 기존 CMap과 일치하는 DB 폰트 '{col}' 전체 CMap 적용")
                        font_CidUnicode[font] = db_cmap
                        return db_cmap.get(cid, None), retry_flag

            except Exception as e:
                print(f"[❌ CMap 비교 중 오류]: {e}")

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
    

import sqlite3

def damage_mac(font, cids, pdf):
    font_CidUnicode = pdf.setdefault('FontCMap', {})
    dbmapresult = pdf.setdefault('dbmapresult', {})   # ✅ 누적 기록 저장소
    db_path = pdf.get('db_path', 'FontDB.sqlite')     # ✅ DB 경로 (기본값 예시)

    print("[🔍 기존 font_CidUnicode cmap과 우선 매핑 시도]")

    if not isinstance(font_CidUnicode, dict) or not font_CidUnicode:
        print("[❗] font_toUnicode가 비어있어 매핑 불가")
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
                        result_chars.append(" ")  # 임시 공백 처리
                        missing_cids.append(cid)
                        if len(missing_cids) > 4:
                            return None  # 너무 많은 CID 누락 시 실패
                    else:
                        return None
            return "".join(result_chars), missing_cids
        except KeyError:
            return None

    print("[🔍 mac 전용: font_toUnicode 후보 cmap으로 매핑 시도]")

    for candidate_font, cmap in font_CidUnicode.items():
        if candidate_font == font:
            continue
        if not isinstance(cmap, dict):
            continue

        # === 매핑 시도 (기본 모드)
        result = None
        missing_cids = []

        tmp = _build_result(cmap, cids, font, allow_missing=False)
        if tmp:
            result, missing_cids = tmp
        else:
            # === 조건 충족 시 missing 허용 모드
            if len(cids) >= 10:
                tmp = _build_result(cmap, cids, font, allow_missing=True)
                if tmp:
                    result, missing_cids = tmp

        if result is None:
            continue

        if "glyph" in result:
            continue
        if result == " ":
            print(f"[✅ 공백 단일 매핑 확정] {candidate_font} → ' '")
            return result
        if len(cids) == 1 and len(result) <= 1:
            cid = cids[0]
            return f"[{font}:Cid_{cid}]"

        # === LLM 판정 ===
        print(f"[🧪 후보 {candidate_font} 매핑 결과] {result}")
        try:
            response = query_ollama(result)  # 'O' or 'X'
        except Exception as e:
            print(f"[LLM 오류] {e}")
            response = "X"

        print(f"[🤖 LLM 판정]: {response}")
        if response == "O":
            # ✅ missing_cids가 있다면 placeholder로 대체
            if missing_cids:
                fixed_result = []
                for cid, ch in zip(cids, result):
                    if cid in missing_cids:
                        fixed_result.append(f"[{font}:Cid_{cid}]")
                    else:
                        fixed_result.append(ch)
                result = "".join(fixed_result)
            # ✅ 매핑 성공 → 누적 기록
            if isinstance(candidate_font, str):
                candidate_font = candidate_font.encode('utf-8')
            if isinstance(font, str):
                font = font.encode('utf-8')

            dbmapresult.setdefault(font, {})
            dbmapresult[font][candidate_font] = dbmapresult[font].get(candidate_font, 0) + 1

            if dbmapresult[font][candidate_font] >= 5:
                print(f"[✅ 폰트 확정: {font} → {candidate_font}]")

                # 1️⃣ 기존 cmap 복사
                if candidate_font in font_CidUnicode:
                    font_CidUnicode[font] = font_CidUnicode[candidate_font]
                    print(f"[♻️ 기존 cmap 재사용 완료] {font} ← {candidate_font}")
                    return result

                # 2️⃣ DB에서 cmap 불러오기
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
                    print(f"[📥 DB cmap 등록 완료] {font} ← {candidate_font}")

                except Exception as e:
                    print(f"[❌ 확정 cmap 불러오기 실패]: {e}")

            return result
        else:
            print(f"[❌ 탈락] {candidate_font}")

    # === 모든 후보 실패 → placeholder 반환 ===
    if len(cids) == 1:
        return f"[{font}:Cid_{cids[0]}]"
    else:
        return "".join(f"[{font}:Cid_{cid}]" for cid in cids)