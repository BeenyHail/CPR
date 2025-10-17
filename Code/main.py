#main
import os
import sys
import re
import preprocess
import ETC
import parser
from mapping import Mapping

# Import mapping_fontdb if available
try:
    from mapping_fontdb import Mapping as Mapping_fontdb
    MAPPING_FONTDB_AVAILABLE = True
except ImportError:
    MAPPING_FONTDB_AVAILABLE = False
    print("[Warning] mapping_fontdb.py not found. LLM-based recovery will not be available.")

#Check the header
def split_pdf_by_signatures(pdf_file_path):
        # Regex pattern for detecting PDF file signature and version info.
        pattern = rb'%PDF-(\d+\.\d+)'
        
        try:
            with open(pdf_file_path, 'rb') as file:
                pdf_data = file.read()
        except FileNotFoundError:
            print("[File Error] File not found.")
            return
        
        # Find all signature locations
        matches = list(re.finditer(pattern, pdf_data))
        
        pdf_data_list = [] 
        
        if matches: #Find signatures
            if len(matches)>1:
                print("Two or more signatures detected in the file.")
            for index, match in enumerate(matches):
                pdf_start = match.start()
                #Two more Signatures
                if index < len(matches) - 1:
                    next_match = matches[index + 1]
                    pdf_end = next_match.start()
                else: #one signature
                    pdf_end = len(pdf_data)

                pdf_chunk = pdf_data[pdf_start:pdf_end]
                
                #append the extracted PDF data
                pdf_data_list.append(pdf_chunk)
        else:
            print("[Header Corrupted] No PDF signature detected.")
            pdf_data_list.append(pdf_data)
            return pdf_data_list
    
        return pdf_data_list

#Python code for one PDF file

if __name__ == "__main__":
    intro = """
==========================================================================
 ⠀     ⠀⠀⠀⠀⡀⡀⡀⡀⡀ ⠀⠀ ⢀⢀⢀⢀⢀⠀⠀⠀ ⢀⢀⢀⢀⠀⠀⠀⠀⠀
⠀⠀     ⠀⠀ ⣰⣿⠿⠿⣿⣷⡄ ⢀⣾⡿⠿⠿⣿⣷⡄ ⢀⣾⡿⠿⠿⣿⣷⡄⠀⠀⠀
⠀     ⠀ ⢠⣿⣟     ⠃ ⣸⣿⠃⠀⠀⣼⣿⠃ ⣸⣿⠃⠀⠀⣼⣿⠃
⠀     ⠀⢠⣿⡟    ⠀  ⢠⣿⣿⣶⣶⡿⠟⠁ ⢠⣿⣿⣶⣶⡿⠟
⠀     ⠀⣾⣿⣁⣀⠀⠀ ⠀ ⢠⣿⡟⠀     ⢠⣿⡟⠀ ⢀⣿⡿
⠀     ⠀⠘⠛⠛⠛⠛⠋  ⠐⠛⠛⠁     ⠐⠛⠛⠁  ⠸⠛  

==========================================================================
"CPR" is a powerful tool that extracts content from damaged or corrupted PDF files.
1. Extract Contents from PDF file.
2. Mapping the extracted content with other fonts (based on the first result) --> coming soon
"""
    print(intro)
    options = input("Select the option  : ").strip()
    if options == '1':
        PDF_path = input("Input the PDF File path : ").strip()
        if "'" in PDF_path or '"' in PDF_path:
            PDF_path = PDF_path[1:-1]

        if not(os.path.isdir(PDF_path)): #when input file is not directory, run the code
            print("-"*10)
            print("PDF file : "+PDF_path.split("\\")[-1])
            #Check the PDF File signature
            pdf_data_list = split_pdf_by_signatures(PDF_path)
            if pdf_data_list == None: #There is no PDF signature, Stop the code
                sys.exit()
            
            # more than Two PDF Signatures in the file (Loop)
            cnt = 0
            for PdfData in pdf_data_list:
                result_path = os.path.dirname(os.path.realpath(__file__))+"\\Export"
                path = PDF_path.split("\\")
                pdf = {
                        'Title': path[-1],
                        'SaveMethod' : None,
                        'Version' : None,
                        'IsDamaged' : None,
                        'IsRecoverable' : None,
                        'Content_Type' : None,
                        'Page' : [],
                        'Pages' : None,
                        'Resources' : [],
                        'CMap' : [],
                        'Font' : [],
                        'Content' : [],
                        'Text' : "",
                        'MappingText' : {},
                        'CMap' : [],
                        'FontCMap': {},
                        'FontName' : [],
                        'FontFile' : [],
                        'FontFileCMap' : {},
                        'Catalog':None,
                        'DamagedObj' : [],
                        'Metadata' : None,
                        'Result_path': result_path+"\\"+path[-1]
                    }
                ETC.makeDir(result_path)
                ETC.makeDir(pdf['Result_path'])

                objList = preprocess.extraction(PdfData, pdf)
                if len(objList) != 0:
                    decompressObj = preprocess.start(objList, pdf, PDF_path)
                    pdf = parser.Parsing(decompressObj, pdf)

                    # Step 1: Run mapping.py (without LLM)
                    print("\n[Step 1] Running basic mapping without FontDB&LLM...")
                    Mapping(decompressObj, pdf)

                    # Save Step 1 mapping result to file
                    if 'Text' in pdf and pdf['Text'] != "":
                        step1_file_path = pdf['Result_path']+"\\"+"PDF_"+str(cnt)+"_Step1_Content.txt"
                        with open(step1_file_path, 'w', encoding='utf-8') as f:
                            f.write(' '.join(pdf['Text']))
                        print("\n[Step 1] Mapping completed and saved to file. Check the file below:")
                        print(f"Step 1 Content: {step1_file_path}")
                    else:
                        print("\n[Step 1] No text mapped in Step 1.\n")

                    # Step 2: Ask user if they want to use LLM-based recovery
                    if MAPPING_FONTDB_AVAILABLE:
                        print("\n" + "="*70)
                        print("[Step 2] FontCMap&FontDB-based recovery is available.")
                        print("This improves the accuracy and quality of text recovery, but requires LLM (ollama).")
                        llm_response = input("Do you want to attempt FontCMap&FontDB-based recovery? (yes/no): ").strip().lower()

                        if llm_response in ['yes', 'y']:
                            print("\n[Step 2] Running FontCMap&FontDB-based mapping...")
                            print("\n[Step 2] Please wait, this step may take a while.")
                            try:
                                Mapping_fontdb(decompressObj, pdf)
                                print("[Success] FontCMap&FontDB-based mapping completed.")
                            except Exception as e:
                                print(f"[Error] FontCMap&FontDB-based mapping failed: {e}")
                                print("Continuing with basic mapping results...")
                        else:
                            print("[Step 2] Skipping FontCMap&FontDB-based recovery. Using basic mapping results.")
                        print("="*70 + "\n")

                    if pdf['Metadata'] != None:
                        parser.parse_Metadata(decompressObj, pdf, cnt)
                        print("Metadata : "+ pdf['Result_path']+"\\"+"PDF_"+str(cnt)+"_Metadata.txt")
                    if pdf['IsRecoverable'] == False:
                        print("[Recover Error] "+pdf['Title']+" is not recoverable")
                    else:
                        if pdf['Text'] != "":
                            with open(pdf['Result_path']+"\\"+"PDF_"+str(cnt)+"_Content.txt", 'w', encoding='utf-8') as f:
                                f.write(' '.join(pdf['Text']))
                            print("Content : "+ pdf['Result_path']+"\\"+"PDF_"+str(cnt)+"_Content.txt")
                        if len(pdf['MappingText']) != 0: 
                            with open(pdf['Result_path']+"\\"+"PDF_"+str(cnt)+"_MappingContent.txt", 'w', encoding='utf-8') as f:
                                for k in pdf['MappingText'].keys():
                                    f.write(k+" : "+pdf['MappingText'][k]+"\n")
                            print("MappingContent : "+ pdf['Result_path']+"\\"+"PDF_"+str(cnt)+"_MappingContent.txt")
                        if pdf['FontName'] != [] and any(item in pdf['DamagedObj'] for item in ['CMap', 'Content', 'Font']) :
                            pdf['FontName'] = list(set(pdf['FontName']))
                            print("If a large portion of text is not mapped in Content.txt, check the Recover Guide below.")
                            with open(pdf['Result_path']+"\\"+"PDF_"+str(cnt)+"_Recover_Guide.txt", 'w', encoding='utf-8') as f:
                                text = '''[Recover Guide]\nif you want to recover the data, download the font file below and Insert in FontDB: \n'''
                                f.write(text+"\n")
                                for i in pdf['FontName']:
                                    f.write(i+"\n")
                            print("Recover guide : "+ pdf['Result_path']+"\\"+"PDF_"+str(cnt)+"_Recover_Guide.txt")
                cnt+=1
            print("-"*10+"Complete!" +"-"*10)
        else:
            print("[File Error] Wrong Path!")
    elif options == '2' :
       sys.exit("Still under development.")
        #Content_path = input("Input the Content(.txt) File path : ")
        #Font_path = os.path.dirname(os.path.realpath(__file__))+'\\FontTotal.xlsx'
    else:
        sys.exit("Wrong Input!")
              
