# Lets Build GPT


## Terms

**Tokenization** is text -> integers ('h' -> 46)

**Embedding** integer -> vector of learned numbers (46 -> [x, x, x, ..., x])

## Attention

Each attention head will have Queries, Keys and Values learned from training. 
It is hard to know exactly what a given attention headmay be attending and how. 

Take a sequence of tokens, "the cat ". Each position t has an embedding vector x[t] (token embedding plus position embedding). 
We multiply Q and K by each token embedding to get a query/key vector for each token.

position:   0    1    2    3    4    5    6    7
char:       t    h    e   ' '   c    a    t   ' '
            │    │    │    │    │    │    │    │
query:     q0   q1   q2   q3   q4   q5   q6   q7    = x[t] @ Wq.T
key:       k0   k1   k2   k3   k4   k5   k6   k7    = x[t] @ Wk.T
value:     v0   v1   v2   v3   v4   v5   v6   v7    = x[t] @ Wv.T

conceptually, the keys answer the queires

the dot product of Q and K gives a matrix of scores (aka attention pattern) where a high score means the key attends to the query.
This is then normalized (scaled and softmax) to gives a probability distributon which gives how much each token influence others

For a token to actually cause a change to another its value vector is added to the token attending it.
For example in "the fluffy animal" the value vector of fluffy gets added to the embedding of animal

- q: what 'animal' wants to find in earlier tokens,
- k: how 'fluffy' describes itself to tokens that are searching,
- v: what 'fluffy' passes on to a token that attends to it.

Values are added as a weighted sum based on the weights of the attention pattern (clarify)


## Results 

without training

```plain
step 0: train loss 4.2846, val loss 4.2820

anlowhgros soirm otophoo tnongmmsis
ho sasoIe nhto rqimi
hre  tTaurfati notGotev
idydhfo dvorlZ sKr ioywJar3pt sFesg
hadsh
eutnoryyJeenfwelizrng  BvfoY
 thur iisovIo MAbeyrB tgnhe.G raeuuie herE ?redo:soV dlsth;-usbe ta-touJlle idCiv
l iCroy meuroze
 azoSUity
r -?a:nKe,.rat mStie se ni turim n, u;.e ther:seh i OeQre ,rn IAltjaaB f qe oe; jitn onandB t he !$&Zu&J Zt ercDno u potS ofdMMr oTrhed t IR tt ScinerqovratfNtnn xb t haarnthesu as ttA
t,me dpqhlko o toodo .h tpn noSls tDl L tfa eY'iB VedxraPuni.ehGIariKiGsood eari,yler traow; FTCr:aGreaeer seZ rere taWfalolyKY!.eefprhat!omexe
srNfcrUist 
ge'rire dr iod neretOtY aea Fois hbzelkees i e
e v J s sarebeps!n ond MQitJhFsszD?3hCtz:liwNA aergoZ giekgtFoX IiDtw:eh&oo
me ttDhr b!
fheeneecheheoto!hectof tk;S sd me ?an'hjTGd,- onart ter tC ssg, irhSrcot:r Ele?resSn; w?'RhehhjYcth t saJrrao eDs o
t:cAnt  etoyee!hei, eT'-IFherej e s!tE?aunott, t t, t mhmb!a
 e t J'pX
Tee trn ttO tyarootBrejtnun ser derre alig htalhat :-teYthoMrrVn hrbee bp
;rIDiuht-bes ta  3otbicer hov mrr o he dUBsnJ:tn t TttqiTitin ,wod
JerGec mtD o nrenlela
Utat mCwe g?
nnDmv bdirsefhe p eufDhtIe r3oles. io tebogrrsahintiteXf tt tOfu,kPedj Frsw-RdaAheWnnZD e S tJtIdJme ese m,
? h ma-nJ. thWnjA
 ep Uht aee
h
```

With training

```plain
Reposed, prison: I will steal the woman.

GREMIO:
She shall be?

SRCALUTIO:
Nay, though a forsworn too; if they were no more
Than Angelo
Who do sound my slave it, these were eyes
Vas like asleep: I heard it! We terr'd
This lack of true which I speak.
We will hence out to say do, in the prince,
Who feeling of your dread; each his ear,
As fingers Aparily was found, and for him
To give it so much leisurps dinges; 'tis as may
Be be strew'd, in this, I cannot.

SLY:
God in good farth:
Am I not go unto a king.

SLY:
Well, proclamate.

RICHARD:
Bend richly, give me hearts.

Lord:
Hath he did look upon my friends make lady.
```