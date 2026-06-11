import re

for filename in ['generate_diagrams.py', 'generate_missing_report.py']:
    with open(filename, 'r', encoding='utf-8') as f:
        code = f.read()
    
    match = re.search(r'def is_retired\(feature, release\):.*?return False', code, flags=re.DOTALL)
    if match:
        new_func = '''def is_retired(feature, release):
    if feature == "CVS" and release >= "2012-10":
        return True
    if feature == "Datatools" and release >= "2022-12":
        return True
    if feature == "EclipseLink" and release >= "2024-03":
        return True
    if feature == "SVN" and release >= "2016-06":
        return True
    if feature == "BIRT" and release >= "2020-12":
        return True
    return False'''
        code = code.replace(match.group(0), new_func)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(code)
