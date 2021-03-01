from torch.utils.data import Dataset
import pandas as pd
import os
import numpy as np
import soundfile as sf
import torch
import json


class StronglyAnnotatedSet(Dataset):
    def __init__(
        self,
        audio_folder,
        tsv_file,
        encoder,
        target_len=10,
        fs=16000,
        return_filename=False,
        train=False,
    ):

        self.encoder = encoder
        self.fs = fs
        self.target_len = target_len * fs
        self.return_filename = return_filename
        self.train = train

        annotation = pd.read_csv(tsv_file, sep="\t")
        examples = {}
        for i, r in annotation.iterrows():
            if r["filename"] not in examples.keys():
                examples[r["filename"]] = {
                    "mixture": os.path.join(audio_folder, r["filename"]),
                    "events": [],
                }
                if not np.isnan(r["onset"]):
                    examples[r["filename"]]["events"].append(
                        {
                            "event_label": r["event_label"],
                            "onset": r["onset"],
                            "offset": r["offset"],
                        }
                    )
            else:
                if not np.isnan(r["onset"]):
                    examples[r["filename"]]["events"].append(
                        {
                            "event_label": r["event_label"],
                            "onset": r["onset"],
                            "offset": r["offset"],
                        }
                    )

        # we construct a dictionary for each example
        self.examples = examples
        self.examples_list = list(examples.keys())

    def __len__(self):
        return len(self.examples_list)

    def __getitem__(self, item):
        c_ex = self.examples[self.examples_list[item]]
        mixture, fs = sf.read(c_ex["mixture"])
        if len(mixture.shape) > 1:  # multi channel
            if not self.train:
                mixture = np.mean(mixture, axis=-1)
            else:  # randomly select one channel
                indx = np.random.randint(0, mixture.shape[-1] - 1)
                mixture = mixture[:, indx]

        if len(mixture) < self.target_len:
            mixture = np.pad(
                mixture, (0, self.target_len - len(mixture)), mode="constant"
            )
            padded_indx = [self.target_len / len(mixture)]
        else:
            padded_indx = [1.0]

        mixture = torch.from_numpy(mixture).float()

        # labels
        labels = c_ex["events"]
        # check if labels exists:
        if not len(labels):
            max_len_targets = self.encoder.n_frames
            strong = torch.zeros(max_len_targets, len(self.encoder.labels)).float()

        else:
            # to steps
            strong = self.encoder.encode_strong_df(pd.DataFrame(labels))
            strong = torch.from_numpy(strong).float()

        if self.return_filename:
            return mixture, strong.transpose(0, 1), padded_indx, c_ex["mixture"]
        else:
            return mixture, strong.transpose(0, 1), padded_indx


class WeakSet(Dataset):
    def __init__(self, audio_folder, tsv_file, encoder, target_len=10, fs=16000):

        self.encoder = encoder
        self.fs = fs
        self.target_len = target_len * fs

        annotation = pd.read_csv(tsv_file, sep="\t")
        examples = {}
        for i, r in annotation.iterrows():

            if r["filename"] not in examples.keys():
                examples[r["filename"]] = {
                    "mixture": os.path.join(audio_folder, r["filename"]),
                    "events": r["event_labels"].split(","),
                }

        self.examples = examples
        self.examples_list = list(examples.keys())

    def __len__(self):
        return len(self.examples_list)

    def __getitem__(self, item):
        c_ex = self.examples[self.examples_list[item]]
        mixture, fs = sf.read(c_ex["mixture"])

        if len(mixture.shape) > 1:  # multi channel
            indx = np.random.randint(0, mixture.shape[-1] - 1)
            mixture = mixture[:, indx]

        if len(mixture) < self.target_len:
            mixture = np.pad(
                mixture, (0, self.target_len - len(mixture)), mode="constant"
            )
            padded_indx = [self.target_len / len(mixture)]
        else:
            padded_indx = [1.0]

        mixture = torch.from_numpy(mixture).float()

        # labels
        labels = c_ex["events"]
        # check if labels exists:
        max_len_targets = self.encoder.n_frames
        weak = torch.zeros(max_len_targets, len(self.encoder.labels))
        if len(labels):
            weak_labels = self.encoder.encode_weak(labels)
            weak[0, :] = torch.from_numpy(weak_labels).float()

        return mixture, weak.transpose(0, 1), padded_indx


class UnlabelledSet(Dataset):
    def __init__(
        self, unlabeled_json, encoder, target_len=10, fs=16000,
    ):

        self.encoder = encoder
        self.fs = fs
        self.target_len = target_len * fs

        with open(unlabeled_json, "r") as f:
            files = json.load(f)

        self.examples = files

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, item):
        c_ex = self.examples[item]
        mixture, fs = sf.read(c_ex)

        if len(mixture.shape) > 1:  # multi channel
            indx = np.random.randint(0, mixture.shape[-1] - 1)
            mixture = mixture[:, indx]

        if len(mixture) < self.target_len:
            mixture = np.pad(
                mixture, (0, self.target_len - len(mixture)), mode="constant"
            )
            padded_indx = [self.target_len / len(mixture)]
        else:
            padded_indx = [1.0]

        mixture = torch.from_numpy(mixture).float()
        max_len_targets = self.encoder.n_frames
        strong = torch.zeros(max_len_targets, len(self.encoder.labels)).float()

        return mixture, strong.transpose(0, 1), padded_indx