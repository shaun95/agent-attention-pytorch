import torch
from torch.nn import Module
from torch import nn, einsum, Tensor

from einops import rearrange, repeat
from einops.layers.torch import Rearrange

# functions

def exists(v):
    return v is not None

# main class

class AgentSelfAttention(Module):
    def __init__(
        self,
        dim,
        *,
        num_agent_tokens,
        dim_head = 64,
        heads = 8,
    ):
        super().__init__()
        self.scale = dim_head ** -0.5
        dim_inner = dim_head * heads

        self.to_qkv = nn.Sequential(
            nn.Linear(dim, dim_inner * 3, bias = False),
            Rearrange('b n (qkv h d) -> qkv b h n d', h = heads, qkv = 3)
        )

        self.agent_tokens = nn.Parameter(torch.zeros(heads, num_agent_tokens, dim_head))
        nn.init.normal_(self.agent_tokens, std = 0.02)

        self.to_out = nn.Sequential(
            Rearrange('b h n d -> b n (h d)'),
            nn.Linear(dim_inner, dim, bias = False)
        )

    def forward(
        self,
        x,
        mask = None
    ):
        batch = x.shape[0]

        q, k, v = self.to_qkv(x)

        a = repeat(self.agent_tokens, 'h m d -> b h m d', b = batch)

        a = a * self.scale

        qa_sim = einsum('b h i d, b h j d -> b h i j', q, a)
        ak_sim = einsum('b h i d, b h j d -> b h i j', a, k)

        qa_attn = qa_sim.softmax(dim = -1)
        ak_attn = ak_sim.softmax(dim = -1)

        out = einsum('b h i j, b h j d -> b h i d', ak_attn, v)
        out = einsum('b h i j, b h j d -> b h i d', qa_attn, out)

        return self.to_out(out)