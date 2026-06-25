"""Modelo BC Leon v3 — Transformer PEQUEÑO (mucho menor que el del notebook) sobre el MISMO encoding oficial.

Encoder: EmbeddingBag(22000) -> 24 words -> TransformerEncoder -> value (tanh del pooling).
Decoder: EmbeddingBag(73847) -> 1 word por accion candidata -> cross-attiende al encoder -> score por candidato.
Policy = softmax sobre los scores de los candidatos de esa muestra (BC = cross-entropy contra el target experto).

Pensado para INFERENCIA CPU barata (presupuesto 600s/partida): d_model y nº de capas pequeños.
Las constantes de vocabulario (encoder_size=22000, decoder_size=73847) deben coincidir con bcil/encode.py.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F

ENCODER_SIZE = 22000
DECODER_SIZE = 73847
NUM_WORDS_ENC = 24


class LeonV3Net(nn.Module):
    def __init__(self, d_model=96, num_heads=4, d_ff=192, num_layers_enc=2, num_layers_dec=2):
        super().__init__()
        self.d_model = d_model
        self.encoder_bag = nn.EmbeddingBag(ENCODER_SIZE, d_model, mode="sum")
        enc_layer = nn.TransformerEncoderLayer(d_model, num_heads, d_ff, dropout=0.0, batch_first=True)
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers_enc, enable_nested_tensor=False)
        self.value_fc = nn.Linear(d_model, 1)
        self.decoder_bag = nn.EmbeddingBag(DECODER_SIZE, d_model, mode="sum")
        self.cross = nn.ModuleList([nn.MultiheadAttention(d_model, num_heads, batch_first=True) for _ in range(num_layers_dec)])
        self.norm = nn.ModuleList([nn.LayerNorm(d_model) for _ in range(num_layers_dec)])
        self.ff = nn.ModuleList([nn.Sequential(nn.Linear(d_model, d_ff), nn.ReLU(), nn.Linear(d_ff, d_model)) for _ in range(num_layers_dec)])
        self.norm2 = nn.ModuleList([nn.LayerNorm(d_model) for _ in range(num_layers_dec)])
        self.score_fc = nn.Linear(d_model, 1)

    def encode_state(self, e_idx, e_val, e_word_off):
        """-> encoder_out (B, 24, d), value (B,)"""
        h = self.encoder_bag(e_idx, e_word_off, e_val)        # (B*24, d)
        h = h.view(-1, NUM_WORDS_ENC, self.d_model)           # (B, 24, d)
        enc = self.encoder(h)                                  # (B, 24, d)
        value = torch.tanh(self.value_fc(enc).mean(dim=1)).squeeze(-1)  # (B,)
        return enc, value

    def score_candidates(self, enc_out, cand_emb, cand_mask):
        """enc_out (B,24,d); cand_emb (B,C,d) padded; cand_mask (B,C) True=valido -> scores (B,C)."""
        key_pad = ~cand_mask  # MHA espera True=ignorar en query padding; aqui enmascaramos queries despues
        x = cand_emb
        for att, n1, ff, n2 in zip(self.cross, self.norm, self.ff, self.norm2):
            y, _ = att(x, enc_out, enc_out, need_weights=False)
            x = n1(x + y)
            x = n2(x + ff(x))
        scores = self.score_fc(x).squeeze(-1)                 # (B, C)
        scores = scores.masked_fill(~cand_mask, float("-inf"))
        return scores

    def forward(self, e_idx, e_val, e_word_off, d_idx, d_val, d_word_off, n_cand):
        """Batch de entrenamiento. n_cand (B,) = nº candidatos por muestra. -> logits (B, Cmax), value (B,)."""
        enc_out, value = self.encode_state(e_idx, e_val, e_word_off)
        cand = self.decoder_bag(d_idx, d_word_off, d_val)     # (sum n_cand, d)
        B = n_cand.shape[0]
        Cmax = int(n_cand.max().item())
        dev = enc_out.device
        # scatter vectorizado (sin bucle Python): id de muestra y posicion dentro de la muestra por candidato
        samp = torch.repeat_interleave(torch.arange(B, device=dev), n_cand)        # (T,)
        starts = torch.cumsum(n_cand, 0) - n_cand                                  # inicio por muestra
        pos = torch.arange(cand.shape[0], device=dev) - starts[samp]               # (T,)
        cand_emb = cand.new_zeros(B, Cmax, self.d_model)
        cand_mask = torch.zeros(B, Cmax, dtype=torch.bool, device=dev)
        cand_emb[samp, pos] = cand
        cand_mask[samp, pos] = True
        logits = self.score_candidates(enc_out, cand_emb, cand_mask)
        return logits, value
