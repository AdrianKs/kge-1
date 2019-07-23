import torch.nn
import torch.nn.functional
from kge.model import KgeEmbedder


class LookupEmbedder(KgeEmbedder):
    def __init__(self, config, dataset, configuration_key, vocab_size):
        super().__init__(config, dataset, configuration_key)

        # read config
        self.dropout = self.get_option("dropout")
        self.normalize = self.check_option("normalize", ["", "L2"])
        self.regularize = self.check_option("regularize", ["", "l1", "l2", "l3"])
        self.regularize_weight = self.get_option("regularize_weight")
        self.sparse = self.get_option("sparse")
        self.config.check("train.trace_level", ["batch", "epoch"])
        self.vocab_size = vocab_size

        # setup embedder
        self.embeddings = torch.nn.Embedding(
            self.vocab_size, self.dim, sparse=self.sparse
        )
        # initialize weights
        init_ = self.get_option("initialize")

        try:
            init_args = self.get_option(init_ + "args")
        except KeyError:
            init_args = self.get_option("initialize_args")
        self.initialize(
            self.embeddings.weight.data,
            init_,
            init_args,
        )

    def _embed(self, embeddings):
        if self.dropout > 0:
            embeddings = torch.nn.functional.dropout(
                embeddings, p=self.dropout, training=self.training
            )
        if self.normalize == "L2":
            embeddings = torch.nn.functional.normalize(embeddings)
        return embeddings

    def embed(self, indexes):
        return self._embed(self.embeddings(indexes.long()))

    def embed_all(self):
        return self._embed(self.embeddings.weight)

    def penalty(self, **kwargs):
        # TODO factor out to a utility method
        if self.regularize == "" or self.regularize_weight == 0.0:
            return super().penalty(**kwargs)
        elif self.regularize == "l1":
            return super().penalty(**kwargs) + [
                self.regularize_weight * self.embeddings.weight.norm(p=1)
            ]
        elif self.regularize == "l2":
            return super().penalty(**kwargs) + [
                self.regularize_weight * self.embeddings.weight.norm(p=2) ** 2
            ]
        elif self.regularize == "l3":
            # As in CP-N3 paper, Eq. (4): Timothée Lacroix, Nicolas Usunier, Guillaume
            # Obozinski. Canonical Tensor Decomposition for Knowledge Base Completion.
            # ICML 2018. https://arxiv.org/abs/1806.07297
            return super().penalty(**kwargs) + [
                self.regularize_weight * self.embeddings.weight.norm(p=3) ** 3
            ]
        else:
            raise ValueError("unknown penalty")
