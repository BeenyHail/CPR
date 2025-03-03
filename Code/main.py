#main
import os
import sys
import re
import preprocess 
import ETC
import parser
from mapping import MappingText
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
            print("[File Error] No PDF signature detected.")
            return []
    
        return pdf_data_list

#Python code for one PDF file

if __name__ == "__main__":
    intro = """
==========================================================================
 ⠀⠀⠀⠀⠀⡀⡀⡀⡀⡀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⢀⠀⠀⠀⠀⠀⠀⡀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⢀⢀⢀⠀⠀⠀⠀⢀⢀⢀⢀⠀⠀⠀⠀⠀⢀⢀⢀⢀⢀⢀⠀⠀⠀
⠀⠀⠀⠀⣰⣿⠿⠿⠿⠿⠏⠠⣿⠏⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⣿⣧⠀⠀⠀⢀⣾⣿⡿⠀⠀⠀⠀⠀⠀⠀⠀⢀⣾⡿⠿⠿⣿⣷⡄⠀⣾⣿⠿⠿⣿⣷⡄⠀⠀⣾⡿⠿⠿⠿⠿⠃⠀⠀
⠀⠀⠀⢠⣿⣟⡀⣀⡀⠀⠀⣤⣤⠀⢠⣤⣄⠀⣠⣤⡤⠀⣼⣿⢿⣿⡄⢀⣴⣿⣿⣿⠃⢠⣤⡄⠀⢀⣤⡤⠀⣸⣿⠃⠀⠀⣼⣿⠃⣸⣿⠇⠀⠀⠨⣿⡯⠀⣸⣿⣃⡀⣀⡀⠀⠀⠀⠀
⠀⠀⠀⣾⣿⠻⠻⠻⠛⠀⣸⣿⠇⠀⠀⢿⣿⣾⠟⠉⠀⢰⣿⠇⠸⣿⣷⣿⠟⢡⣿⡏⠀⢸⣿⡗⣰⣿⠟⠁⢠⣿⣿⣶⣶⡿⠟⠁⢠⣿⡟⠀⠀⠀⣼⣿⠃⢠⣿⡿⠻⠻⠻⠃⠀⠀⠀⠀
⠀⠀⣰⣿⠇⠀⠀⠀⠀⢠⣿⡟⠀⢀⣰⣾⢿⣿⡄⠀⢀⣿⡿⠀⠀⠛⠛⠁⠀⣿⡿⠀⠀⠀⣿⣿⡿⠃⠀⠀⣾⡿⠁⠀⠀⠀⠀⠀⣾⣿⣁⣀⣤⣾⠟⠁⠀⣾⡿⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠛⠛⠀⠀⠀⠀⠀⠚⠛⠂⠐⠛⠛⠁⠸⠻⠳⠀⠸⠛⠃⠀⠀⠀⠀⠀⠸⠛⠃⠀⠀⣰⣿⠟⠀⠀⠀⠘⠟⠃⠀⠀⠀⠀⠀⠘⠛⠛⠛⠛⠋⠁⠀⠀⠘⠛⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀

==========================================================================
"FixMyPDF" is a powerful tool that extracts content from damaged or corrupted PDF files.
1. Extract Contents from PDF file.
2. Mapping the extracted content with other fonts (based on the first result)
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
                        'CMap' : [],
                        'Font' : [],
                        'Content' : [],
                        'Text' : "",
                        'MappingText' : {},
                        'CMap' : [],
                        'FontCMap': {},
                        'FontName' : [],
                        'Catalog':None,
                        'DamagedObj' : [],
                        'Metadata' : None,
                        'Result_path': result_path+"\\"+path[-1]
                    }
                ETC.makeDir(result_path)
                ETC.makeDir(pdf['Result_path'])

                objList = preprocess.extraction(PdfData)
                if len(objList) != 0:
                    decompressObj = preprocess.start(objList, pdf, PDF_path)
                    pdf = parser.Parsing(decompressObj, pdf)
                    MappingText(decompressObj, pdf)
                    
                    if pdf['Metadata'] != None:
                        parser.parse_Metadata(decompressObj, pdf, cnt)
                        print("Metadata : "+ pdf['Result_path']+"\\"+"PDF_"+str(cnt)+"_Metadata.txt")
                    if pdf['IsRecoverable'] == False:
                        print("[Recover Error] "+pdf['Title']+" is not recoverable")
                    else:
                        if pdf['Text'] != "":
                            with open(pdf['Result_path']+"\\"+"PDF_"+str(cnt)+"_Content.txt", 'w', encoding='utf-8') as f:
                                f.write(pdf['Text'])
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
                                text = '''[Recover Guide]\nif you want to recover the data, download the font file below and Open pdf file using ALPDF: \n'''
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
              
