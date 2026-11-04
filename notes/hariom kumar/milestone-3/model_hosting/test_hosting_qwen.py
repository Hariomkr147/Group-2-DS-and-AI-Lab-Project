"""Check the standalone notebook without downloading weights or requiring a GPU."""
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


NOTEBOOK = Path(__file__).with_name("hosting-qwen.ipynb")
CELLS = {cell["id"]: cell for cell in json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]}
for cell in CELLS.values():
    cell["source"] = "".join(cell["source"])


class HostingNotebookChecks(unittest.TestCase):
    def test_clean_standalone_notebook(self):
        for cell in CELLS.values():
            if cell["cell_type"] == "code":
                compile(cell["source"], cell["id"], "exec")
                self.assertEqual(cell["outputs"], [])
                self.assertIsNone(cell["execution_count"])
        text = NOTEBOOK.read_text(encoding="utf-8")
        self.assertNotIn("ADAPTER_DIR", text)
        self.assertNotIn("/kaggle/input", text)
        last_code = [c for c in CELLS.values() if c["cell_type"] == "code"][-1]
        self.assertEqual(last_code["id"], "public-tunnel")

    def test_pinned_hub_loader_and_generation_limits(self):
        scope = {}
        exec(CELLS["install"]["source"].split("subprocess.check_call")[0], scope)
        exec(CELLS["configuration"]["source"], scope)
        torch = MagicMock()
        torch.cuda.is_available.return_value = True
        transformers, peft = MagicMock(), MagicMock()
        config = peft.PeftConfig.from_pretrained.return_value
        config.base_model_name_or_path = scope["BASE_MODEL_ID"]
        config.task_type, config.peft_type = "CAUSAL_LM", "LORA"
        config.r, config.lora_alpha = 16, 16
        tokenizer = transformers.AutoTokenizer.from_pretrained.return_value
        tokenizer.apply_chat_template.return_value = "QQQ<|im_end|>\n"
        tokenizer.encode.return_value = [248046]
        tokenizer.eos_token_id = 248044
        model = peft.PeftModel.from_pretrained.return_value
        model.generation_config.eos_token_id = [248044, 248046]
        model.config.text_config.max_position_embeddings = 262144
        with patch.dict(sys.modules, {"torch": torch, "transformers": transformers, "peft": peft}), \
                patch("importlib.metadata.version", return_value="fixture"):
            exec(CELLS["load-model"]["source"], scope)
        transformers.AutoModelForCausalLM.from_pretrained.assert_called_once_with(
            scope["BASE_MODEL_ID"], revision=scope["BASE_REVISION"], dtype=torch.float16,
            device_map={"": 0}, quantization_config=scope["quantization"],
            trust_remote_code=False, use_safetensors=True,
        )
        peft.PeftModel.from_pretrained.assert_called_once_with(
            transformers.AutoModelForCausalLM.from_pretrained.return_value,
            scope["MODEL_ID"], revision=scope["MODEL_REVISION"],
            is_trainable=False, use_safetensors=True,
        )
        transformers.AutoTokenizer.from_pretrained.assert_called_once_with(
            scope["BASE_MODEL_ID"], revision=scope["BASE_REVISION"], trust_remote_code=False,
        )
        exec(CELLS["inference"]["source"], scope)
        exec(CELLS["api-server"]["source"], scope)
        infer = scope["infer"]
        tokenizer.return_value = {"input_ids": MagicMock(), "attention_mask": MagicMock()}
        tokenizer.return_value["input_ids"].shape = (1, 10)
        tokenizer.decode.return_value = "What operation would undo adding 3?"
        model.generate.return_value.__getitem__.return_value = [1, 2]
        request = scope["validate_request"]({"messages": [{"role": "user", "content": "Help?"}]})
        result = infer(request)
        self.assertEqual(result["text"], tokenizer.decode.return_value)
        self.assertEqual(result["input_tokens"], 10)
        self.assertFalse(result["output_limit_reached"])
        self.assertEqual(model.generate.call_args.kwargs["eos_token_id"], [248044, 248046])
        self.assertFalse(model.generate.call_args.kwargs["do_sample"])
        model.generate.reset_mock()
        for body in ({"prompt": "x", "max_new_tokens": 97},
                     {"messages": [{"role": "assistant", "content": "x"}], "max_new_tokens": 96}):
            with self.assertRaises(ValueError):
                infer(body)
        tokenizer.return_value["input_ids"].shape = (1, 2000)
        with self.assertRaises(ValueError):
            infer({"prompt": "too long", "max_new_tokens": 96})
        model.generate.assert_not_called()


def load_tests(loader, tests, pattern):
    # Exercise the embedded server with the project's existing HTTP/auth/concurrency tests.
    server = types.ModuleType("kaggle_inference_api")
    exec(CELLS["api-server"]["source"], server.__dict__)
    existing = (Path(__file__).resolve().parents[4] / "Ncert work" /
                "09_skill_misconception_and_scope_mapping" / "code" / "test_kaggle_inference_api.py")
    spec = importlib.util.spec_from_file_location("embedded_api_checks", existing)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"kaggle_inference_api": server}):
        spec.loader.exec_module(module)
    tests.addTests(loader.loadTestsFromModule(module))
    return tests


if __name__ == "__main__":
    unittest.main()
