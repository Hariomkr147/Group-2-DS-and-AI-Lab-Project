"""Train a small original-architecture DKT demo baseline; never overwrite an export."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from kt import DKT

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'notes/hariom pandey/milestone-2/dkt_processed'


def main():
    torch.manual_seed(42);torch.set_num_threads(2)
    folder=HERE/'models/dkt';folder.mkdir(parents=True,exist_ok=True)
    if (folder/'dkt_weights.pt').exists():
        raise FileExistsError('Preserve the existing trained checkpoint before replacing it')
    data=np.load(SOURCE/'dkt_data.npz',allow_pickle=False);n=int(data['N'])
    name_path=HERE/'data/assist_skill_names.json'
    if not name_path.exists():name_path=HERE/'data/hf_skill_names.json'
    names=json.loads(name_path.read_text()) if name_path.exists() else {}
    rows=list(csv.DictReader((SOURCE/'skill_map.csv').open(encoding='utf-8')))
    assert len(rows)==n and [int(r['skill_index']) for r in rows]==list(range(n))
    x,s,c,m=[data[k+'_tr'] for k in ['X','S','C','M']]
    assert np.all(x[m==1]==(s+n*c)[m==1])
    model=DKT(n);opt=torch.optim.Adam(model.parameters(),lr=.001)
    loss_fn=torch.nn.BCEWithLogitsLoss();history=[]
    for epoch in range(3):
        order=torch.randperm(len(x)).numpy();total=0;steps=0
        model.train()
        for offset in range(0,len(x),32):
            ids=order[offset:offset+32];mask=torch.tensor((m[ids,1:]==1)&(m[ids,:-1]==1))
            inputs=torch.tensor(np.where(m[ids,:-1]==1,x[ids,:-1],2*n),dtype=torch.long)
            target=torch.tensor(s[ids,1:],dtype=torch.long)
            labels=torch.tensor(c[ids,1:],dtype=torch.float32)
            if not mask.any():continue
            output=model(inputs).gather(2,target.unsqueeze(-1)).squeeze(-1)
            loss=loss_fn(output[mask],labels[mask]);opt.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5);opt.step()
            total+=float(loss.detach());steps+=1
        history.append(total/steps);print('Epoch',epoch+1,'train loss',history[-1],flush=True)
    weights=folder/'dkt_weights.pt';torch.save(model.state_dict(),weights)
    skills=[dict(index=int(r['skill_index']),skill_id=r['skill_id_original'],name=names.get(r['skill_id_original'],'')) for r in rows]
    (folder/'skills.json').write_text(json.dumps(skills,indent=2))
    metadata=dict(architecture='DKT',n_skills=n,embedding_size=64,hidden_size=128,
                  interaction_encoding='skill_index + n_skills * correct',padding_index=2*n,
                  checkpoint='Locally trained original DKT demo baseline; 3 epochs; not the supplied notebook weights',
                  source_sha256=hashlib.sha256((SOURCE/'dkt_data.npz').read_bytes()).hexdigest(),
                  weights_sha256=hashlib.sha256(weights.read_bytes()).hexdigest(),training_loss=history,epochs=3)
    (folder/'metadata.json').write_text(json.dumps(metadata,indent=2))
    print('Saved trained demo baseline',flush=True)


if __name__=='__main__':main()
