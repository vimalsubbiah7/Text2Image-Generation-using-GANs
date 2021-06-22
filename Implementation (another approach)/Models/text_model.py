#Code is modified from following site :https://github.com/google/tirg


"""Class for text data."""
import string
import numpy as np
import torch


class SimpleVocab(object):

  def __init__(self):
    super(SimpleVocab, self).__init__()
    self.word2id = {}
    self.wordcount = {}
    self.word2id['<UNK>'] = 0
    self.wordcount['<UNK>'] = 9e9

  def tokenize_text(self, text):
    text = text.encode('ascii', 'ignore').decode('ascii')
    tokens = str(text).lower().translate(str.maketrans('','',string.punctuation)).strip().split()
    return tokens

  def add_text_to_vocab(self, text):
    tokens = self.tokenize_text(text)
    for token in tokens:
      if token not in self.word2id:
        self.word2id[token] = len(self.word2id)
        self.wordcount[token] = 0
      self.wordcount[token] += 1

  def threshold_rare_words(self, wordcount_threshold=5):
    for w in self.word2id:
      if self.wordcount[w] < wordcount_threshold:
        self.word2id[w] = 0

  def encode_text(self, text):
    tokens = self.tokenize_text(text)
    x = [self.word2id.get(t, 0) for t in tokens]
    return x

  def get_size(self):
    return len(self.word2id)


class TextLSTMModel(torch.nn.Module):

  def __init__(self,
               texts_to_build_vocab,
               word_embed_dim=512,
               GRU_hidden_dim=512):

    super(TextLSTMModel, self).__init__()

    self.vocab = SimpleVocab()
    for text in texts_to_build_vocab:
      self.vocab.add_text_to_vocab(text)
    vocab_size = self.vocab.get_size()

    self.word_embed_dim = word_embed_dim
    self.GRU_hidden_dim = GRU_hidden_dim
    self.embedding_layer = torch.nn.Embedding(vocab_size, word_embed_dim)
    #GRU_implementaion
    self.gru = torch.nn.GRU(word_embed_dim, GRU_hidden_dim)
    

    self.fc_output = torch.nn.Sequential(
        torch.nn.Dropout(p=0.1),
        torch.nn.Linear(GRU_hidden_dim, GRU_hidden_dim),
    )

  def forward(self, x):
    """ input x: list of strings"""
    #print(x)
    if type(x) is list:
      if type(x[0]) is str or type(x[0]) is unicode:
            x = [self.vocab.encode_text(text) for text in x]

    assert type(x) is list
    assert type(x[0]) is list
    assert type(x[0][0]) is int
    return self.forward_encoded_texts(x)

  def forward_encoded_texts(self, texts):
    # to tensor
    lengths = [len(t) for t in texts]
    itexts = torch.zeros((np.max(lengths), len(texts))).long()
    for i in range(len(texts)):
      itexts[:lengths[i], i] = torch.tensor(texts[i])

    # embed words
    if torch.cuda.is_available():
      itexts = torch.autograd.Variable(itexts).cuda()


    etexts = self.embedding_layer(itexts)

    # lstm
    lstm_output, _ = self.forward_lstm_(etexts)

    # get last output (using length)
    text_features = []
    for i in range(len(texts)):
      text_features.append(lstm_output[lengths[i] - 1, i, :])

    # output
    text_features = torch.stack(text_features)
    text_features = self.fc_output(text_features)
    return text_features

  def forward_lstm_(self, etexts):
    batch_size = etexts.shape[1]

    
    #GRU implemention
    first_hidden = (torch.zeros(1, batch_size, self.GRU_hidden_dim))
    #first_hidden = (first_hidden[0].cuda(), first_hidden[1].cuda())
    if torch.cuda.is_available(): 
      first_hidden = (first_hidden.cuda())
    else :
      first_hidden = (first_hidden)

    lstm_output, last_hidden = self.gru(etexts, first_hidden)
    # print("GRU CALLED")

    return lstm_output, last_hidden