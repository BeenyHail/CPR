import sys
import os
import re
import subprocess
import xml.etree.ElementTree as ET

def makeDir(directory): #make directory
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
        except OSError:
            print("Error: Failed to create the directory.")
            sys.exit()

def detectZeroStreak(hex_data):
        zero_byte = b'\x00'
        #Set the number of consecutive 00 bytes to check for.
        min_consecutive_zeros = 48 
        consecutive_zeros = zero_byte * min_consecutive_zeros

        return consecutive_zeros in hex_data

# === Arabic Presentation Forms-A/B Mapping ===
ARABIC_FORMS = {
    "0621": {"isol": "FE80"},
    "0622": {"isol": "FE81", "fina": "FE82"},
    "0623": {"isol": "FE83", "fina": "FE84"},
    "0624": {"isol": "FE85", "fina": "FE86"},
    "0625": {"isol": "FE87", "fina": "FE88"},
    "0626": {"isol": "FE89", "fina": "FE8A", "init": "FE8B", "medi": "FE8C"},
    "0627": {"isol": "FE8D", "fina": "FE8E"},
    "0628": {"isol": "FE8F", "fina": "FE90", "init": "FE91", "medi": "FE92"},
    "0629": {"isol": "FE93", "fina": "FE94"},
    "062A": {"isol": "FE95", "fina": "FE96", "init": "FE97", "medi": "FE98"},
    "062B": {"isol": "FE99", "fina": "FE9A", "init": "FE9B", "medi": "FE9C"},
    "062C": {"isol": "FE9D", "fina": "FE9E", "init": "FE9F", "medi": "FEA0"},
    "062D": {"isol": "FEA1", "fina": "FEA2", "init": "FEA3", "medi": "FEA4"},
    "062E": {"isol": "FEA5", "fina": "FEA6", "init": "FEA7", "medi": "FEA8"},
    "062F": {"isol": "FEA9", "fina": "FEAA"},
    "0630": {"isol": "FEAB", "fina": "FEAC"},
    "0631": {"isol": "FEAD", "fina": "FEAE"},
    "0632": {"isol": "FEAF", "fina": "FEB0"},
    "0633": {"isol": "FEB1", "fina": "FEB2", "init": "FEB3", "medi": "FEB4"},
    "0634": {"isol": "FEB5", "fina": "FEB6", "init": "FEB7", "medi": "FEB8"},
    "0635": {"isol": "FEB9", "fina": "FEBA", "init": "FEBB", "medi": "FEBC"},
    "0636": {"isol": "FEBD", "fina": "FEBE", "init": "FEBF", "medi": "FEC0"},
    "0637": {"isol": "FEC1", "fina": "FEC2", "init": "FEC3", "medi": "FEC4"},
    "0638": {"isol": "FEC5", "fina": "FEC6", "init": "FEC7", "medi": "FEC8"},
    "0639": {"isol": "FEC9", "fina": "FECA", "init": "FECB", "medi": "FECC"},
    "063A": {"isol": "FECD", "fina": "FECE", "init": "FECF", "medi": "FED0"},
    "0641": {"isol": "FED1", "fina": "FED2", "init": "FED3", "medi": "FED4"},
    "0642": {"isol": "FED5", "fina": "FED6", "init": "FED7", "medi": "FED8"},
    "0643": {"isol": "FED9", "fina": "FEDA", "init": "FEDB", "medi": "FEDC"},
    "0644": {"isol": "FEDD", "fina": "FEDE", "init": "FEDF", "medi": "FEE0"},
    "0645": {"isol": "FEE1", "fina": "FEE2", "init": "FEE3", "medi": "FEE4"},
    "0646": {"isol": "FEE5", "fina": "FEE6", "init": "FEE7", "medi": "FEE8"},
    "0647": {"isol": "FEE9", "fina": "FEEA", "init": "FEEB", "medi": "FEEC"},
    "0648": {"isol": "FEED", "fina": "FEEE"},
    "0649": {"isol": "FEEF", "fina": "FEF0"},
    "064A": {"isol": "FEF1", "fina": "FEF2", "init": "FEF3", "medi": "FEF4"},
}


def glyphname_to_unicode_full(name: str) -> str:
    """
    Unified converter (with chr() range error prevention)
    """
    if not name.startswith("uni"):
        return None

    # --- Detect Arabic forms ---
    m_ar = re.match(r"uni([0-9A-Fa-f]{4,12})(?:\.(isol|init|medi|fina))$", name)
    if m_ar:
        base, form = m_ar.groups()
        base = base.upper()
        if form and base in ARABIC_FORMS and form in ARABIC_FORMS[base]:
            return chr(int(ARABIC_FORMS[base][form], 16))
        else:
            try:
                return chr(int(base, 16))
            except ValueError:
                return None

    # --- Detect general/composite unicode ---
    m = re.match(r"uni([0-9A-Fa-f]{4,})(?:\..*)?$", name)
    if not m:
        return None
    hexseq = m.group(1)

    chars = []
    # Split by 4-digit units (discard incomplete last chunk)
    for i in range(0, len(hexseq) - (len(hexseq) % 4), 4):
        try:
            code = int(hexseq[i:i+4], 16)
            if 0 <= code <= 0x10FFFF:
                chars.append(chr(code))
        except ValueError:
            continue
    return "".join(chars) if chars else None


def run_ttx_extract_glyphorder(file_path, output_dir=None):
    """Extract GlyphOrder table using ttx"""
    cmd = ["ttx", "-t", "GlyphOrder"]
    if output_dir:
        basename = os.path.basename(file_path)
        name = os.path.splitext(basename)[0]
        output_file = os.path.join(output_dir, f"{name}.ttx")
        cmd.extend(["-o", output_file])
    cmd.append(file_path)

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_file
    except subprocess.CalledProcessError:
        return None


def extract_glyph_order(ttx_path, agl_map=None):
    """Extract and convert {glyphID: unicode_char} from ttx file"""
    if agl_map is None:
        agl_map = {}

    try:
        tree = ET.parse(ttx_path)
        root = tree.getroot()
        glyph_order = root.find("GlyphOrder")
        if glyph_order is not None:
            glyph_map = {}
            for idx, glyph_id_elem in enumerate(glyph_order.findall("GlyphID")):
                glyph_name = glyph_id_elem.get("name")
                if glyph_name:
                    cid = format(idx, '04X')  # CID format: 4-digit hexadecimal
                    value = glyph_name  # default value

                    # If starts with glyph: convert CID to unicode
                    if glyph_name.startswith("glyph"):
                        try:
                            # Convert CID to integer then to unicode character
                            code_point = int(cid, 16)
                            value = chr(code_point)
                        except (ValueError, OverflowError):
                            pass  # Keep default value on conversion failure
                    # If starts with uni: use glyphname_to_unicode_full
                    elif glyph_name.startswith("uni"):
                        shaped = glyphname_to_unicode_full(glyph_name)
                        if shaped:
                            value = shaped
                    # If doesn't start with uni or glyph, look up in AGL (Adobe Glyph List)
                    elif glyph_name in agl_map:
                        value = agl_map[glyph_name]

                    glyph_map[cid] = value
            return glyph_map
    except Exception as e:
        print(f"Error parsing GlyphOrder: {e}")
    return None