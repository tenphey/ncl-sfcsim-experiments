import pandas as pd
from scipy import stats
p='run_20260526_222616/grid_e11_results.csv'
df=pd.read_csv(p)
df_clean = df[(df['DHEFT']>0) & (df['NHEFT']>0)]
df_clean['gain_pct'] = (df_clean['DHEFT'] - df_clean['NHEFT'])/df_clean['DHEFT']*100
for rb, g in df_clean.groupby('repo_bw'):
    dhe_mean = g['DHEFT'].mean()
    nhe_mean = g['NHEFT'].mean()
    gain_mean = g['gain_pct'].mean()
    gain_median = g['gain_pct'].median()
    wins = (g['NHEFT'] < g['DHEFT']).sum()
    t=stats.ttest_rel(g['DHEFT'], g['NHEFT'], nan_policy='omit')
    pval = t.pvalue
    print('repo_bw=',rb)
    print('  DHEFT_mean=',round(dhe_mean,4),' NHEFT_mean=',round(nhe_mean,4))
    print('  gain_mean_pct=',round(gain_mean,4),' gain_median_pct=',round(gain_median,4))
    print('  wins_count (NHEFT<DHEFT)=',wins,' n_runs=',len(g))
    print('  paired t-test p=',pval)

