import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load ALL real results
macsea = pd.read_csv('results/macsea_results.csv')
rr     = pd.read_csv('results/round_robin_results.csv')
heft   = pd.read_csv('results/heft_results.csv')
minmin = pd.read_csv('results/min_min_results.csv')

# Real numbers from actual runs
schedulers = ['Round Robin', 'HEFT', 'Min-Min', 'MACSEA']
colors     = ['#BBBBBB', '#BBBBBB', '#BBBBBB', '#2E75B6']

data = {
    'energy_wh': [
        rr['energy_wh'].mean(),
        heft['energy_wh'].mean(),
        minmin['energy_wh'].mean(),
        macsea['energy_wh'].mean(),
    ],
    'carbon_gco2': [
        rr['carbon_gco2'].mean(),
        heft['carbon_gco2'].mean(),
        minmin['carbon_gco2'].mean(),
        macsea['carbon_gco2'].mean(),
    ],
    'sla_compliance': [
        rr['sla_compliance'].mean(),
        heft['sla_compliance'].mean(),
        minmin['sla_compliance'].mean(),
        macsea['sla_compliance'].mean(),
    ],
    'total_cost_usd': [
        rr['total_cost_usd'].mean(),
        heft['total_cost_usd'].mean(),
        minmin['total_cost_usd'].mean(),
        macsea['total_cost_usd'].mean(),
    ],
}

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle(
    'MACSEA vs Baselines — Real Experimental Results\n'
    '(100 AI Jobs, Google Cluster Trace Workload)',
    fontsize=15, fontweight='bold', y=1.01
)

def bar_chart(ax, values, title, ylabel, lower_is_better=True):
    bars = ax.bar(schedulers, values, color=colors,
                  edgecolor='white', linewidth=1.5, width=0.55)

    # Highlight MACSEA
    bars[-1].set_edgecolor('#1F3864')
    bars[-1].set_linewidth(2.5)

    # Value labels
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + max(values)*0.015,
                f'{val:.2f}', ha='center', va='bottom',
                fontsize=10, fontweight='bold')

    # Improvement vs worst baseline
    baseline_vals = values[:-1]
    macsea_val = values[-1]
    if lower_is_better:
        worst = max(baseline_vals)
        improvement = (worst - macsea_val) / worst * 100
        label = f'↓{improvement:.1f}% vs worst baseline'
    else:
        worst = min(baseline_vals)
        improvement = (macsea_val - worst) / worst * 100
        label = f'↑{improvement:.1f}% vs worst baseline'

    ax.set_title(title, fontweight='bold', fontsize=13, pad=10)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_xticklabels(schedulers, fontsize=10)
    ax.annotate(label,
                xy=(3, macsea_val),
                xytext=(2.0, macsea_val * (0.75 if lower_is_better
                                           else 1.08)),
                fontsize=9, color='#1F3864', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='#1F3864',
                                lw=1.5))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(0, max(values) * 1.25)

# Plot all 4 charts
bar_chart(axes[0,0], data['energy_wh'],
          ' Energy Consumption',
          'Avg Energy per Job (Wh)')

bar_chart(axes[0,1], data['carbon_gco2'],
          ' Carbon Emissions',
          'Avg Carbon per Job (gCO2)')

bar_chart(axes[1,0], data['sla_compliance'],
          ' SLA Compliance Rate',
          'SLA Compliance (%)',
          lower_is_better=False)

bar_chart(axes[1,1], data['total_cost_usd'],
          'Scheduling Cost',
          'Avg Cost per Job (USD)')

# Summary table at bottom
summary_text = (
    f"MACSEA Results: "
    f"Energy={macsea['energy_wh'].mean():.2f}Wh | "
    f"Carbon={macsea['carbon_gco2'].mean():.2f}gCO2 | "
    f"SLA={macsea['sla_compliance'].mean():.1f}% | "
    f"Cost=${macsea['total_cost_usd'].mean():.4f} | "
    f"Carbon Saved={macsea['carbon_saved_pct'].mean():.1f}%"
)
fig.text(0.5, -0.01, summary_text, ha='center',
         fontsize=9, color='#333333',
         bbox=dict(boxstyle='round', facecolor='#EBF3FB',
                   alpha=0.8, edgecolor='#2E75B6'))

plt.tight_layout()
plt.savefig('figures/macsea_real_comparison.png',
            dpi=150, bbox_inches='tight', facecolor='white')
print(" Real comparison chart saved!")
print(f"\n── Summary ─────────────────────────────")
print(f"{'Scheduler':<15} {'Energy(Wh)':>12} "
      f"{'Carbon(gCO2)':>14} {'SLA%':>8} {'Cost$':>8}")
print("-" * 60)
for s, e, c, sl, co in zip(
    schedulers,
    data['energy_wh'], data['carbon_gco2'],
    data['sla_compliance'], data['total_cost_usd']
):
    marker = " ← MACSEA" if s == "MACSEA" else ""
    print(f"{s:<15} {e:>12.4f} {c:>14.4f} "
          f"{sl:>8.1f} {co:>8.4f}{marker}")

plt.show()