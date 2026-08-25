import pandas as pd
import json


with open ('/home/primo/Scaricati/ICD11_progetto/mms/mms_completo.json','r',encoding='utf-8') as f:
    data=json.load(f)

df=pd.json_normalize(data)

df.to_csv('output_mms.csv', index=False, encoding='utf-8-sig', sep=';')
