import re
with open('logs/application.log','r',encoding='utf-8',errors='ignore') as f:
    c=f.read()
entry=len(re.findall(r'ENTRY.*SUCCESS|ENTRY OPEN',c))
budget_cap=len(re.findall(r'Budget Cap',c))
block=len(re.findall(r'portfolio_check_failed',c))
exit_fill=len(re.findall(r'EXIT.*FILL',c))
errors=len(re.findall(r'ERROR(?!.*텔레그램)',c))
equity_matches=re.findall(r'Equity[:\s]+\$?([\d,]+)',c)
equity=float(equity_matches[-1].replace(',','')) if equity_matches else None
print(f'\n=== M60 Checkpoint (60 min) ===')
print(f'Entry SUCCESS: {entry}')
print(f'Exit FILL: {exit_fill}')
print(f'Budget Cap: {budget_cap}')
print(f'Portfolio BLOCK: {block}')
print(f'Block Rate: {block/(entry+block)*100:.1f}%' if (entry+block)>0 else 'N/A')
print(f'Errors: {errors}')
print(f'Equity: ${equity:,.0f}' if equity else 'Equity: N/A')
