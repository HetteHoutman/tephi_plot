import os
import sys

import pandas as pd

from miscellaneous import check_argv_num

check_argv_num(sys.argv, 1, '(sat_ukv_results xlsx)')

df = pd.read_excel(sys.argv[1], index_col=[0,1])

for idx, row in df.iterrows():
    datetime_str = str(idx[0][:4]) + str(idx[0][5:7]) + str(idx[0][8:10]) + '_' + str(row.hour)
    os.system(f"python fourier_analysis.py ../tephiplot/settings/{datetime_str}.json {idx[1]}")
