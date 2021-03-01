import torch
import random


def mixup(audio_tensors, labels):

    audio1, audio2 = torch.chunk(audio_tensors, 2, dim=0)
    lab1, lab2 = torch.chunk(labels, 2, dim=0)

    gains = (
        torch.tensor([random.betavariate(2, 8) for x in range(audio2.shape[0])])
        .to(audio1)
        .reshape(-1, 1, 1)
    )
    mixed = audio1 * gains + audio2 * (1 - gains)
    new_labels = torch.clamp(lab1 * gains + lab2 * (1 - gains), min=0, max=1)

    return mixed, new_labels


def add_noise(mels, snr=30):

    snr = 10 ** (snr / 20)  # linear domain
    sigma = torch.std(mels, dim=(1, 2), keepdim=True) / snr
    mels = mels + torch.randn(mels.shape, device=mels.device) * sigma

    return mels