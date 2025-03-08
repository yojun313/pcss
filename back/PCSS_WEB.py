import sys
import json
import ast

from PCSS import PCSSEARCH

InputData = json.loads(sys.argv[1])

option = InputData['option']
startyear = InputData['startyear']
endyear = InputData['endyear']
# Possible 값을 Boolean으로 변환
threshold = InputData['uncertainty']
conf_list = InputData['selectedConferences']
countOption = InputData['CountOption']

countOption = True if countOption == '예' else False

pcssearch_obj = PCSSEARCH(int(option), float(threshold), int(startyear), int(endyear), countOption)
pcssearch_obj.main(conf_list)
