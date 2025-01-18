import sys
import json
import ast

from PCSS import PCSSEARCH

InputData = json.loads(sys.argv[1])

print(InputData)

option = InputData['option']
startyear = InputData['startyear']
endyear = InputData['endyear']
possible = InputData['Possible']
conf_list = InputData['selectedConferences']


pcssearch_obj = PCSSEARCH(int(option), bool(possible), int(startyear), int(endyear))
pcssearch_obj.search_main(conf_list)
