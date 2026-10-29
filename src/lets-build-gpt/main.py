import torch
from torch import nn
from torch.nn import functional as F


def main():
    # read it in to inspect it
    with open('input.txt', 'r', encoding='utf-8') as f:
        text = f.read()
        print("length of dataset in characters: ", len(text))

        chars = sorted(list(set(text)))
        vocab_size = len(chars)
        print(''.join(chars))
        print(vocab_size)

        # create a mapping from characters to integers
        stoi = { ch:i for i,ch in enumerate(chars) }
        itos = { i:ch for i,ch in enumerate(chars) }
        encode = lambda s: [stoi[c] for c in s] # encoder: take a string, output a list of integers
        decode = lambda l: ''.join([itos[i] for i in l]) # decoder: take a list of integers, output a string

        print(encode("hii there"))
        print(decode(encode("hii there")))

        # let's now encode the entire text dataset and store it into a torch.Tensor
        import torch # we use PyTorch: https://pytorch.org
        data = torch.tensor(encode(text), dtype=torch.long)
        print(data.shape, data.dtype)
        #print(data[:1000]) # the 1000 characters we looked at earier will to the GPT look like this

        # Let's now split up the data into train and validation sets
        n = int(0.9*len(data)) # first 90% will be train, rest val
        train_data = data[:n]
        val_data = data[n:]

        block_size = 8
        #print(train_data[:block_size+1])
        # tensor([18, 47, 56, 57, 58,  1, 15, 47, 58])

        x = train_data[:block_size]
        y = train_data[1:block_size+1]
        for t in range(block_size):
            context = x[:t+1]
            target = y[t]
            print(f"when input is {context} the target: {target}")

        # when input is tensor([18]) the target: 47
        # when input is tensor([18, 47]) the target: 56
        # when input is tensor([18, 47, 56]) the target: 57
        # when input is tensor([18, 47, 56, 57]) the target: 58
        # when input is tensor([18, 47, 56, 57, 58]) the target: 1
        # when input is tensor([18, 47, 56, 57, 58,  1]) the target: 15
        # when input is tensor([18, 47, 56, 57, 58,  1, 15]) the target: 47
        # when input is tensor([18, 47, 56, 57, 58,  1, 15, 47]) the target: 58

        torch.manual_seed(1337)
        batch_size = 4 # how many independent sequences will we process in parallel?
        block_size = 8 # what is the maximum context length for predictions?

        def get_batch(split):
            # generate a small batch of data of inputs x and targets y
            data = train_data if split == 'train' else val_data
            ix = torch.randint(len(data) - block_size, (batch_size,)) # tensor([ 76049, 234249, 934904, 560986])
            x = torch.stack([data[i:i+block_size] for i in ix])
            y = torch.stack([data[i+1:i+block_size+1] for i in ix])
            return x, y

        xb, yb = get_batch('train')
        # print('inputs:')
        # print(xb.shape)
        # print(xb)
        # print('targets:')
        # print(yb.shape)
        # print(yb)

        # print('----')

        # for b in range(batch_size): # batch dimension
        #     for t in range(block_size): # time dimension
        #         context = xb[b, :t+1]
        #         target = yb[b,t]
        #         print(f"when input is {context.tolist()} the target: {target}")
        #

        torch.manual_seed(1337)

        class BigramLanguageModel(nn.Module):

            def __init__(self, vocab_size):
                super().__init__()
                # each token directly reads off the logits for the next token from a lookup table
                self.token_embedding_table = nn.Embedding(vocab_size, vocab_size)

            def forward(self, idx, targets=None):

                # idx and targets are both (B,T) tensor of integers
                logits = self.token_embedding_table(idx) # (B,T,C) initialized with random values

                if targets is None:
                    loss = None
                else:
                    # This unpacks the 3-D shape into named sizes.
                    # - B = 4: the batch size, i.e. 4 independent sequences.
                    # - T = 8: block_size, the number of positions in each sequence.
                    # - C = 65: vocab_size ("channels"), one score per possible next character.
                    B, T, C = logits.shape
                    logits = logits.view(B*T, C) # 4x8 rows of 65 scores, i.e. 32 predictions
                    targets = targets.view(B*T) # and 32 answers
                    loss = F.cross_entropy(logits, targets)

                return logits, loss

            def generate(self, idx, max_new_tokens):
                # idx is (B, T) array of indices in the current context
                # On the first iteration:
                # - idx is [[0]], and token 0 is '\n'.
                # - self(idx) is called without targets, so the reshape is skipped and logits stays 3-D with shape (1, 1, 65).
                # - logits[:, -1, :] takes the last (and only) time step, giving shape (1, 65)
                # Those 65 numbers are row 0 of the embedding matrix: the model's scores for "what character comes after a newline"
                for _ in range(max_new_tokens):
                    # get the predictions
                    logits, loss = self(idx)
                    # focus only on the last time step
                    logits = logits[:, -1, :] # becomes (B, C)
                    # apply softmax to get probabilities
                    probs = F.softmax(logits, dim=-1) # (B, C)
                    # sample from the distribution
                    idx_next = torch.multinomial(probs, num_samples=1) # (B, 1)
                    # append sampled index to the running sequence
                    idx = torch.cat((idx, idx_next), dim=1) # (B, T+1)
                return idx

        m = BigramLanguageModel(vocab_size)
        logits, loss = m(xb, yb) # calls forward with targets
        print(logits.shape)
        print(loss)

        # idx grows like this:
        #[[0]]  →  [[0, 47]]  →  [[0, 47, 56]]  →  ...  →  shape (1, 101)
        generated = m.generate(
            idx = torch.zeros((1, 1), dtype=torch.long),
            max_new_tokens=100)

        print(decode(generated[0].tolist()))
        # SKIcLT;AcELMoTbvZv C?nq-QE33:CJqkOKH-q;:la!oiywkHjgChzbQ?u!3bLIgwevmyFJGUGp
        # wnYWmnxKWWev-tDqXErVKLgJ
        #
        # at this point there is no training so this is using a completely random embedding matrix

        # create a PyTorch optimizer and gets referecnes to the models trainable tensors (in our case just token_embedding_table)
        optimizer = torch.optim.AdamW(m.parameters(), lr=1e-3)

        batch_size = 32
        for steps in range(10000): # increase number of steps for good results...

            # sample a batch of data
            xb, yb = get_batch('train')

            # evaluate the loss
            logits, loss = m(xb, yb) # do one forward pass, this time 32x8 question/answers
            optimizer.zero_grad(set_to_none=True) # needs to be reset each step, impl detail
            loss.backward() # write .grad into parameters (gradients pointing towards which direction would reduce loss)
            optimizer.step() # based on gradients make changes to the weights (nudging individual weights in the opposite direction of its gradient to reduce loss)

        print(loss.item())

        print(decode(m.generate(idx = torch.zeros((1, 1), dtype=torch.long), max_new_tokens=500)[0].tolist()))


if __name__ == "__main__":
    main()
