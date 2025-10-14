import os
import subprocess
import sqlite3
import xml.etree.ElementTree as ET
import pandas as pd

def run_ttx_extract(file_path, tables=["name", "GlyphOrder"], font_index=None, output_dir=None):
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
        subprocess.run(cmd, check=True)
        print(f"✅ Extracted: {os.path.basename(file_path)}" + (f" (index {font_index})" if font_index is not None else ""))
    except subprocess.CalledProcessError as e:
        print(f"❌ Extraction failed: {file_path} (index {font_index})")

def extract_ttc_all_fonts(ttc_path, output_dir=None):
    for i in range(10):
        run_ttx_extract(ttc_path, tables=["name", "GlyphOrder"], font_index=i, output_dir=output_dir)
        # 종료 조건: 생성된 .ttx 파일이 없거나 포맷 깨진 경우 종료
        expected_file = os.path.join(output_dir, os.path.basename(ttc_path).replace(".ttc", f"#{i}.ttx")) if output_dir else None
        if expected_file and not os.path.exists(expected_file):
            break

def extract_postscript_name(ttx_path):
    try:
        tree = ET.parse(ttx_path)
        root = tree.getroot()
        name_table = root.find("name")
        if name_table is not None:
            for record in name_table.findall("namerecord"):
                if record.get("nameID") == "6":
                    return record.text.strip()
    except:
        pass
    return os.path.splitext(os.path.basename(ttx_path))[0]  # fallback

def parse_glyphorder(ttx_path, agl_map=None):
    glyph_dict = {}
    if agl_map is None:
        agl_map = {}

    try:
        tree = ET.parse(ttx_path)
        root = tree.getroot()
        glyph_order = root.find("GlyphOrder")
        if glyph_order:
            for glyph in glyph_order.findall("GlyphID"):
                id_ = glyph.get("id")
                name = glyph.get("name")
                if id_ and name:
                    cid = f"0x{int(id_):04X}"

                    if name.startswith("uni") and len(name) == 7:
                        try:
                            value = chr(int(name[3:], 16))
                        except:
                            value = name
                    elif name in agl_map:
                        value = agl_map[name]
                    else:
                        value = name

                    glyph_dict[cid] = value
    except Exception as e:
        print(f"❌ Error parsing {ttx_path}: {e}")

    return glyph_dict

def build_dataframe_from_folder(folder_path, agl_map=None):
    all_data = {}
    for file in os.listdir(folder_path):
        if file.lower().endswith(".ttx"):
            ttx_path = os.path.join(folder_path, file)
            postscript_name = extract_postscript_name(ttx_path)
            glyphs = parse_glyphorder(ttx_path, agl_map=agl_map)  # ✅ AGL 적용
            all_data[postscript_name] = glyphs

    all_cids = sorted({cid for glyphs in all_data.values() for cid in glyphs})
    df = pd.DataFrame(index=all_cids)
    for font_name, glyphs in all_data.items():
        df[font_name] = pd.Series(glyphs)
    df.index.name = "CID"
    return df

def save_dataframe_to_sqlite(df, db_path, table_name="GlyphOrder"):
    conn = sqlite3.connect(db_path)
    df.reset_index(inplace=True)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    try:
        conn.execute(f"CREATE INDEX idx_{table_name.lower()}_cid ON {table_name}(CID)")
    except:
        pass
    conn.commit()
    conn.close()
    print(f"📦 DB 저장 완료: {db_path}")

def full_pipeline(input_folder, db_path, agl_map=None):
    os.makedirs("temp_ttx", exist_ok=True)

    for file in os.listdir(input_folder):
        path = os.path.join(input_folder, file)
        if file.lower().endswith((".ttf", ".otf")):
            run_ttx_extract(path, output_dir="temp_ttx")
        elif file.lower().endswith(".ttc"):
            extract_ttc_all_fonts(path, output_dir="temp_ttx")

    df = build_dataframe_from_folder("temp_ttx", agl_map)
    save_dataframe_to_sqlite(df, db_path)

def load_agl_mapping(file_path):
    glyphname_to_char = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('#') or ';' not in line:
                    continue
                parts = line.strip().split(';')
                if len(parts) != 2:
                    continue
                name, codepoints = parts
                try:
                    chars = ''.join(chr(int(cp, 16)) for cp in codepoints.split())
                    glyphname_to_char[name] = chars
                except:
                    continue
        print(f"✅ AGL 로딩 완료: {len(glyphname_to_char)}개 항목")
    except Exception as e:
        print(f"❌ glyphlist.txt 로딩 실패: {e}")

    return glyphname_to_char


# 🔧 실행 예시
if __name__ == "__main__":
    agl_path = "./glyphlist.txt"
    agl_map = load_agl_mapping(agl_path)
    input_folder = "path_to_your_font_files"  # 폴더 경로 설정
    db_path = "./glyphorder.db"
    full_pipeline(input_folder, db_path, agl_map)
