"""Offline-only net reward target; stops, signals and sizing are unchanged."""
from research.candle_validation_20261019.engine import open_position

def cost_target(side,price,atr,p,slip):
 pos=open_position(side,price,atr,p,slip)
 if pos:
  reward=atr*p['stop_atr']*p['gross_reward_multiple']
  # Solve side*(exit-entry)-fee*(entry+exit)=reward per unit.
  fill=(side*pos['entry']+p['fee_per_side']*pos['entry']+reward)/(side-p['fee_per_side'])
  pos['target']=fill/(1-side*slip)
 return pos
