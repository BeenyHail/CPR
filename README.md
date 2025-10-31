# CPR(Corrupted PDF Recovery Algorithm)

## 📚Overview

-   **CPR** is a Python-based tool designed to recover damaged PDF documents.
-   As PDF files have become widely used due to their compatibility across different operating systems, issues with corrupted files blocking access to content have also increased.
-   The diversity of PDF structures, influenced by the generation methods(e.g. software) and document contents, makes it difficult to identify and fix damaged objects.
-   **CPR** is developed to extract and restore key elements like text, images, and graphics by analyzing existing data on an object-by-object basis.


## 💡Key Features
-   **Multi-Generator Adaptability:** Handles various PDF generation methods, each with its own recovery logic optimized for producer-specific structures. Even in rendering-impossible cases—such as macOS-generated files with corrupted or missing font references—**CPR can still reconstruct readable content** through specialized recovery logic.
-   **Assess Recoverability:** Checks for essential data like Content objects, CMap objects, and Image data.
-   **Extract Content:** Extracts text, images, graphics and metadata from damaged PDF files.
-   **FontDB-Based Text Recovery:** When text-related structures are severely corrupted, recovers readable content through LLM-assisted CID-to-Unicode mapping with FontDB.


## 📄 Dataset

- Overview
	
	|Type|Details|
	|:------:|---|
	|Languages|3 (English, French, Korean)|
	|Fonts|10 total (6 OS-embedded + 4 external)|
	|Generation Methods|6 (across Windows & macOS)|
	|Ground Truth PDFs|22 (each 3–5 pages)|
	|Corrupted PDFs|655 total|

- Generation Method (6 types)
	
	|**OS**|Generation Method|
	|:------:|---|
	|Windows|Adobe Acrobat|
	|Windows|Microsoft Save as PDF|
	|Windows|Microsoft Print to PDF|
	|macOS|Adobe Acrobat|
	|macOS|Document Editor - Save as PDF|
	|macOS|Document Editor - Print to PDF|

- Deleted Object Type & Resulting Corrupted PDF Types
	- 8 content-related object types selectively deleted

	|Deleted Object Type|Observed Result in PDF Viewer|
	|:------:|---|
	|Catalog|completely unreadable|
	|PageTree|completely unreadable|
	|Page|displayed as blank pages|
	|DescendantFonts|displayed as blank pages|
	|Font|text appears garbled or unreadable|
	|ToUnicode(CMap) & FontFile|text appears garbled or unreadable| 
	|Resources|displayed as blank pages| 
	|Content*|completely unreadable (only Content Object remains)| 

## 🚀 Installation
```bash
#if you don't have git, this should be done first.
#download&install git -> https://git-scm.com/install/
winget install --id Git.Git -e --source winget
```
(1) If you only want the code
```bash
git clone --no-checkout https://github.com/BeenyHail/CPR.git
cd CPR
git sparse-checkout init --cone
git sparse-checkout set Code
git checkout main
pip install -r requirements.txt
```
(2) If you want the code & full dataset(original pdf files 132 + corrupted files 655)
```bash
git clone https://github.com/BeenyHail/CPR
cd CPR
pip install -r requirements.txt
```
## ✅ Configure LLM

-   CPR uses an **LLM-based recovery** module to restore text when encoding structures are severely corrupted.
-   The default configuration supports **Llama 3.1 (8B)** for local inference via **Ollama**, but you can easily replace it with any other model by modifying the `llmquery.py` file.
```bash
# install ollama -> <https://ollama.com/download>
ollama run llama3.1:8b
```

## 🛠️ Usage

```bash
PS D:\\CPR-main> python.exe d:/CPR-main/Code/main.py   

==========================================================================
 ⠀     ⠀⠀⠀⠀⡀⡀⡀⡀⡀ ⠀⠀ ⢀⢀⢀⢀⢀⠀⠀⠀ ⢀⢀⢀⢀⠀⠀⠀⠀⠀
⠀⠀     ⠀⠀ ⣰⣿⠿⠿⣿⣷⡄ ⢀⣾⡿⠿⠿⣿⣷⡄ ⢀⣾⡿⠿⠿⣿⣷⡄⠀⠀⠀
⠀     ⠀ ⢠⣿⣟     ⠃ ⣸⣿⠃⠀⠀⣼⣿⠃ ⣸⣿⠃⠀⠀⣼⣿⠃
⠀     ⠀⢠⣿⡟    ⠀  ⢠⣿⣿⣶⣶⡿⠟⠁⢠⣿⣿⣶⣶⡿⠟
⠀     ⠀⣾⣿⣁⣀⠀⠀ ⠀⢠⣿⡟⠀     ⢠⣿⡟⠀  ⢀⣿⡿
⠀     ⠀⠘⠛⠛⠛⠛⠋⠐⠛⠛⠁     ⠐⠛⠛⠁   ⠸⠛  

==========================================================================
"CPR" is a powerful tool that extracts content from damaged or corrupted PDF files.
1. Extract Contents from PDF file.
2. Mapping the extracted content with other fonts (based on the first result) --> coming soon

Select the option  : 1
Input the PDF File path : 'c:\\Users\\BeenyHail\\Downloads\\Examples.pdf'   
======================================================================
[Step 1] Running basic mapping without FontDB&LLM...
Step 1 Content: '{Result Path}'
======================================================================
[Step 2] FontCMap&FontDB-based recovery is available.
This improves the accuracy and quality of text recovery, but requires LLM (ollama).
Do you want to attempt FontCMap&FontDB-based recovery? (yes/no):
	- yes: [Step 2] Running FontCMap&FontDB-based mapping...
					→ [Success] FontCMap&FontDB-based mapping completed.
					→ Content : '{Result Path}'
	- no: Skipping LLM-based recovery. Using basic mapping results. 
					→ End
```

## 📝 Requirements

Python 3.X
(recommend 3.12.x)


## License
<a href="https://creativecommons.org">Untitled</a> © 1999 by 
<a href="https://creativecommons.org">Jane Doe</a> is licensed under 
<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC 4.0</a>
<img src="https://mirrors.creativecommons.org/presskit/icons/cc.svg" alt="CC" height="16">
<img src="https://mirrors.creativecommons.org/presskit/icons/by.svg" alt="BY" height="16">
<img src="https://mirrors.creativecommons.org/presskit/icons/nc.svg" alt="NC" height="16">
