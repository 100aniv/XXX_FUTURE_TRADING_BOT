import re
with open('logs/application.log','r',encoding='utf-8',errors='ignore') as f:
    c=f.read()

entry_success=len(re.findall(r'ENTRY.*SUCCESS|ENTRY OPEN',c))
entry_reduced=len(re.findall(r'ENTRY.*REDUCED',c))
exit_fill=len(re.findall(r'EXIT.*FILL',c))
budget_cap=len(re.findall(r'Budget Cap',c))
portfolio_block=len(re.findall(r'portfolio_check_failed',c))
volume_guard=len(re.findall(r'volume_guard.*block|Volume Guard.*BLOCK',c,re.IGNORECASE))
exposure_guard=len(re.findall(r'exposure.*block|Exposure Guard.*BLOCK',c,re.IGNORECASE))
cooldown=len(re.findall(r'cooldown.*block|Cooldown.*BLOCK',c,re.IGNORECASE))
errors=len(re.findall(r'ERROR(?!.*텔레그램)',c))
criticals=len(re.findall(r'CRITICAL',c))

total_attempts=entry_success+entry_reduced+portfolio_block
block_rate=portfolio_block/total_attempts*100 if total_attempts>0 else 0
budget_cap_rate=budget_cap/(entry_success+entry_reduced)*100 if (entry_success+entry_reduced)>0 else 0

equity_matches=re.findall(r'Equity[:\s]+\$?([\d,]+)',c)
equity=float(equity_matches[-1].replace(',','')) if equity_matches else None

print(f'\n=== FINAL STATISTICS (1H 52MIN) ===')
print(f'Entry SUCCESS: {entry_success}')
print(f'Entry REDUCED: {entry_reduced}')
print(f'Exit FILL: {exit_fill}')
print(f'Budget Cap Applied: {budget_cap} ({budget_cap_rate:.1f}%)')
print(f'Portfolio BLOCK: {portfolio_block} ({block_rate:.1f}%)')
print(f'  - Volume Guard: {volume_guard}')
print(f'  - Exposure Guard: {exposure_guard}')
print(f'  - Cooldown: {cooldown}')
print(f'Errors: {errors}')
print(f'Criticals: {criticals}')
print(f'Equity: ${equity:,.0f}' if equity else 'Equity: N/A')
print(f'Log Size: {len(c)/1024:.1f}KB')
