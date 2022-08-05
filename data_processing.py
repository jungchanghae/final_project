import pytorch_lightning as pl
import torch.nn as nn
from transformers import ElectraModel, AutoTokenizer
import torch

import kss

import pandas as pd

def one_hot_encode(data, n_label=44):
    data = list(map(int,data.split(',')))
    one_hot = [0] * n_label
    label_idx = data
    for idx in label_idx:
        one_hot[idx] = 1
    return torch.LongTensor(one_hot)

def data_preprocessing(df,electra_model):
    # text split // 24분 소요
    X = df['text'][:]
    pr_x = []
    for x in X:
        split_x = []
        for sent in kss.split_sentences(x):
            split_x.append(electra_model(sent)[0])
        pr_x.append(split_x)
    x_data = torch.tensor(torch.stack(pr_x))

    # label one hot encoding and to tensor
    Y = df['emotion'][:]
    pr_y = []
    for y in Y:
        pr_y.append(one_hot_encode(y))
    y_data = torch.stack(pr_y,0)
    
    return x_data, y_data


electra_model_path= "./saved_model/kote_pytorch_lightning.bin"
train_data_path = './data/train.tsv'

df = pd.read_csv(train_data_path,delimiter='\t',names=['num','text','emotion'],header=None)

LABELS = ['불평/불만',
 '환영/호의',
 '감동/감탄',
 '지긋지긋',
 '고마움',
 '슬픔',
 '화남/분노',
 '존경',
 '기대감',
 '우쭐댐/무시함',
 '안타까움/실망',
 '비장함',
 '의심/불신',
 '뿌듯함',
 '편안/쾌적',
 '신기함/관심',
 '아껴주는',
 '부끄러움',
 '공포/무서움',
 '절망',
 '한심함',
 '역겨움/징그러움',
 '짜증',
 '어이없음',
 '없음',
 '패배/자기혐오',
 '귀찮음',
 '힘듦/지침',
 '즐거움/신남',
 '깨달음',
 '죄책감',
 '증오/혐오',
 '흐뭇함(귀여움/예쁨)',
 '당황/난처',
 '경악',
 '부담/안_내킴',
 '서러움',
 '재미없음',
 '불쌍함/연민',
 '놀람',
 '행복',
 '불안/걱정',
 '기쁨',
 '안심/신뢰']

device = "cuda" if torch.cuda.is_available() else "cpu"

class KOTEtagger(pl.LightningModule):
    def __init__(self):
        super().__init__()
        self.electra = ElectraModel.from_pretrained("beomi/KcELECTRA-base").to(device)
        self.tokenizer = AutoTokenizer.from_pretrained("beomi/KcELECTRA-base")
        self.classifier = nn.Linear(self.electra.config.hidden_size, 44).to(device)
        
    def forward(self, text:str):
        encoding = self.tokenizer.encode_plus(
          text,
          add_special_tokens=True,
          max_length=512,
          return_token_type_ids=False,
          padding="max_length",
          return_attention_mask=True,
          return_tensors='pt',
        ).to(device)
        output = self.electra(encoding["input_ids"], attention_mask=encoding["attention_mask"])
        output = output.last_hidden_state[:,0,:]
        output = self.classifier(output)
        output = torch.sigmoid(output)
        torch.cuda.empty_cache()
        
        return output

trained_model = KOTEtagger()
trained_model.load_state_dict(torch.load(electra_model_path))

x_data,y_data = data_preprocessing(df,trained_model)
