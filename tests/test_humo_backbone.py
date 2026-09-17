import pytest

pytest.importorskip("torch")


@pytest.mark.gpu
def test_carga_y_pasada_corta():
    import torch
    from transformers import AutoModel, AutoTokenizer

    tok = AutoTokenizer.from_pretrained("BSC-LT/MrBERT-es")
    modelo = AutoModel.from_pretrained("BSC-LT/MrBERT-es")
    ids = tok("El ministro de Hacienda anunció la reforma.", return_tensors="pt")
    with torch.no_grad():
        salida = modelo(**ids).last_hidden_state
    assert salida.shape[-1] == 768 and salida.shape[1] == ids["input_ids"].shape[1]
