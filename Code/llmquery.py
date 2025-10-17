import requests
import json

def query_ollama(expression: str) -> str:
    url = "http://localhost:11434/api/generate"
    headers = {"Content-Type": "application/json"}

    prompt = f"""
The following text is the result of CID-to-Unicode mapping.
Please check if it is a natural, grammatically valid, and commonly used word or sentence in any major language (English, French, Chinese, Hindi, Arabic, Korean, etc.).

- If it is a real word or phrase that is commonly used in daily communication or formal writing, reply with "O"
- If it is unnatural, meaningless, overly symbolic, or a random combination of special characters or archaic letters, reply with "X"
- Do not explain your answer — only reply with O or X

Examples of acceptable expressions:
"추적추적", "있거니와", "그러니까", "그럼에도 불구하고",
"however", "therefore", "in conclusion", "worn shoes, still in his threadbare coat",
"donc", "par conséquent", "je vous remercie",
"因此", "所以说", "我们发现",
"धन्यवाद", "यह सच है", "केलिएआिर्शहै।",
"مرحبا", "الحمد لله", "ةمدخ  ليصوتلا  يهطلاو  تارئاطلاب  نودب  رايط"
"ありがとう", "そして", "静かな夜に"

Examples of invalid expressions:
"ᾔḊ", "⨊⧺", "𓀀😁صҖ", "⚛⌘∃ç", "ǂǁ",
"〄〓∰⊙♆", "¤†‰Ω", "₪𐌰𐍂𐌰", "∆₩∯", "√≠çπ∮",
"𐍃𐍄𐌰𐌹", "ß∂˚∆ø", "»¬÷×±"

Expression: {expression}
"""

    payload = {
        "model": "llama3.1:8b",
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    if response.ok:
        result = response.json()
        return result.get("response", "").strip()
    else:
        return f"Error: {response.status_code} - {response.text}"


if __name__ == "__main__":
    example = "예제텍스트"
    print(query_ollama(example))
