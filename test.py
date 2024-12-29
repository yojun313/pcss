import pandas as pd

# CSV 파일 경로 설정
input_file = "name_origin.csv"  # 기존 CSV 파일 경로
output_file = "first_name.csv"  # 저장할 CSV 파일 경로

# CSV 파일 불러오기
df = pd.read_csv(input_file)

# 기존 열 이름과 새로운 열 이름 설정
old_name_column = '루시아피어나양'  # 기존 이름 열 이름
new_name_column = 'name'  # 새 이름 열 이름

# 열 이름 변경
df = df.rename(columns={old_name_column: new_name_column})

# 네 글자 이상 이름 제거
df_filtered = df[df[new_name_column].str.len() < 3]

# 필터링된 데이터 다시 저장
df_filtered.to_csv(output_file, index=False)

print(f"네 글자 이상 이름이 제거되고 열 이름이 변경된 데이터를 '{output_file}'에 저장했습니다.")
