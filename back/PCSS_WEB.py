import sys
import json
import ast

from PCSS import PCSSEARCH

InputData = json.loads(sys.argv[1])

option = InputData['option']
startyear = InputData['startyear']
endyear = InputData['endyear']
# Possible 값을 Boolean으로 변환
possible = InputData['Possible']
if isinstance(possible, str):
    # 문자열 "True"/"False"를 Boolean 값으로 변환
    possible = possible.lower() == "true"

conf_list = InputData['selectedConferences']


pcssearch_obj = PCSSEARCH(int(option), possible, int(startyear), int(endyear))
pcssearch_obj.main(conf_list)
