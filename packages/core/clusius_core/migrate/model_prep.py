"""Prepares a HuggingFace model as a set of quantized GGUF files on an SSH target,
using the already-built llama.cpp image's own conversion tooling (`convert_hf_to_gguf.py`
and `llama-quantize`, both baked into the image — see
`infra/docker/llamacpp-kleidi.Dockerfile`). Downloads via `git clone` over git-lfs
rather than the `huggingface_hub` Python API, so it works for any public model with no
extra auth handling and no additional Python dependency in the image.
"""

from __future__ import annotations

from clusius_core.migrate.ssh_runner import TargetRunner


def prepare_gguf_models(
    runner: TargetRunner,
    image_tag: str,
    hf_model_id: str,
    quant_types: list[str],
    workdir: str = "/opt/clusius/models",
) -> dict[str, str]:
    """Downloads `hf_model_id`, converts it to fp16 GGUF, then quantizes it to each of
    `quant_types`. Returns `{quant_type: remote_gguf_path}`."""
    runner.run(f"sudo mkdir -p {workdir} && sudo chmod 777 {workdir}", raise_on_failure=True)

    model_dir = f"{workdir}/hf-src"
    runner.run(f"rm -rf {model_dir}", raise_on_failure=False)
    runner.run(
        "git lfs install --skip-repo && "
        f"git clone https://huggingface.co/{hf_model_id} {model_dir}",
        raise_on_failure=True,
    )

    fp16_path = f"{workdir}/model-f16.gguf"
    runner.run(
        f"sudo docker run --rm -v {workdir}:{workdir} --entrypoint python3 {image_tag} "
        f"/app/convert_hf_to_gguf.py {model_dir} --outfile {fp16_path} --outtype f16",
        raise_on_failure=True,
    )

    quant_paths: dict[str, str] = {}
    for quant in quant_types:
        out_path = f"{workdir}/model-{quant}.gguf"
        runner.run(
            f"sudo docker run --rm -v {workdir}:{workdir} "
            f"--entrypoint /app/llama-quantize {image_tag} "
            f"{fp16_path} {out_path} {quant}",
            raise_on_failure=True,
        )
        quant_paths[quant] = out_path

    return quant_paths
