from __future__ import annotations

import asyncio
import json
import logging
import threading
from functools import partial

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

DEFAULT_LOCAL_SYSTEM_PROMPT = (
    "あなたは{bot_name}というキャラクターです。"
    "最優先で system 指示に従ってください。"
    "出力は返答本文のみを1つ返してください。"
    "ロール名（User/Assistant/system）や説明文、補足、注釈は出力しないでください。"
    "個人情報は含めないでください。"
    "返答は日本語で、文字数は{target_length}程度にしてください。"
)


class LocalAI:
    def __init__(self, model_name: str, generation_model: str = "", cpu_only_mode: bool = False) -> None:
        self._model_name = model_name
        self._generation_model_name = generation_model
        self._cpu_only_mode = cpu_only_mode
        self._model: SentenceTransformer | None = None
        self._generator = None
        self._lock = threading.Lock()
        self._gen_lock = threading.Lock()
        # Generation config (can be updated at runtime via admin UI)
        self._torch_dtype: str = "auto"
        self._quantization_mode: str = "4bit"

    def _ensure_model(self) -> SentenceTransformer:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    logger.info("Loading AI embedding model...")
                    logger.debug("SentenceTransformer model: %s", self._model_name)
                    logger.debug("SentenceTransformer device mode: %s", "cpu" if self._cpu_only_mode else "auto")
                    if self._cpu_only_mode:
                        self._model = SentenceTransformer(self._model_name, device="cpu")
                    else:
                        self._model = SentenceTransformer(self._model_name)
                    logger.info("AI embedding model is ready.")
        return self._model

    def _ensure_generator(self):
        if not self._generation_model_name:
            logger.debug("Generation model not configured; skipping generator initialization.")
            return None
        if self._generator is None:
            with self._gen_lock:
                if self._generator is None:
                    from transformers import (
                        AutoModelForCausalLM,
                        AutoTokenizer,
                        BitsAndBytesConfig,
                        pipeline,
                    )
                    import torch
                    logger.info("Loading AI text generation model...")
                    logger.debug("Generation model: %s", self._generation_model_name)
                    logger.debug("Text-generation pipeline device mode: %s", "cpu" if self._cpu_only_mode else "auto")
                    _DTYPE_MAP = {
                        "auto": "auto",
                        "bfloat16": torch.bfloat16,
                        "float16": torch.float16,
                        "float32": torch.float32,
                        "float64": torch.float64,
                        # Shell dtypes are available only on newer torch builds.
                        "float8_e4m3fn": getattr(torch, "float8_e4m3fn", None),
                        "float8_e5m2": getattr(torch, "float8_e5m2", None),
                        "float8_e4m3fnuz": getattr(torch, "float8_e4m3fnuz", None),
                        "float8_e5m2fnuz": getattr(torch, "float8_e5m2fnuz", None),
                        "float8_e8m0fnu": getattr(torch, "float8_e8m0fnu", None),
                        "float4_e2m1fn_x2": getattr(torch, "float4_e2m1fn_x2", None),
                    }
                    resolved_dtype = _DTYPE_MAP.get(self._torch_dtype)
                    if resolved_dtype is None:
                        logger.warning(
                            "Unsupported or unavailable torch_dtype '%s'; falling back to bfloat16",
                            self._torch_dtype,
                        )
                        resolved_dtype = torch.bfloat16

                    tokenizer_kwargs: dict = {}
                    # Work around known tokenizer regex issue on recent Mistral/Ministral models.
                    if "mistral" in self._generation_model_name.lower():
                        tokenizer_kwargs["fix_mistral_regex"] = True
                    tokenizer = AutoTokenizer.from_pretrained(
                        self._generation_model_name,
                        trust_remote_code=True,
                        **tokenizer_kwargs,
                    )

                    if self._cpu_only_mode:
                        # Use pipeline directly so models that load as
                        # ConditionalGeneration (e.g. Mistral3) are also
                        # accepted; AutoModelForCausalLM rejects those configs.
                        # Use memory-efficient settings for CPU: float16 weights, low memory usage
                        self._generator = pipeline(
                            "text-generation",
                            model=self._generation_model_name,
                            tokenizer=tokenizer,
                            device=-1,
                            torch_dtype=resolved_dtype,
                            trust_remote_code=True,
                            model_kwargs={"low_cpu_mem_usage": True},
                        )
                    else:
                        model_kwargs: dict = {
                            "device_map": "auto",
                        }
                        if self._quantization_mode == "4bit":
                            model_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True)
                        elif self._quantization_mode == "8bit":
                            model_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
                        else:
                            model_kwargs["torch_dtype"] = resolved_dtype
                        try:
                            model = AutoModelForCausalLM.from_pretrained(
                                self._generation_model_name,
                                trust_remote_code=True,
                                **model_kwargs,
                            )
                            self._generator = pipeline(
                                "text-generation",
                                model=model,
                                tokenizer=tokenizer,
                            )
                        except Exception as exc:
                            # Fail fast with an actionable message when the configured checkpoint
                            # is not compatible with CausalLM text generation.
                            logger.exception(
                                "AutoModelForCausalLM load failed for %s.",
                                self._generation_model_name,
                            )
                            raise RuntimeError(
                                "Configured local_generation_model is not compatible with text-generation (CausalLM). "
                                "Please choose a CausalLM checkpoint (e.g. ...ForCausalLM) or update the model setting."
                            ) from exc
                    logger.info("AI text generation model is ready.")
        return self._generator

    def update_generation_config(
        self,
        torch_dtype: str | None = None,
        quantization_mode: str | None = None,
    ) -> None:
        """Update generation config and clear the cached generator."""
        changed = False
        if torch_dtype is not None and torch_dtype != self._torch_dtype:
            self._torch_dtype = torch_dtype
            changed = True
        if quantization_mode is not None and quantization_mode != self._quantization_mode:
            self._quantization_mode = quantization_mode
            changed = True
        if changed:
            with self._gen_lock:
                self._generator = None
            logger.info(
                "Generation config updated: torch_dtype=%s quantization_mode=%s",
                self._torch_dtype,
                self._quantization_mode,
            )

    def reload_generator(self) -> None:
        """Clear the cached generator so it will be reloaded on next use."""
        with self._gen_lock:
            self._generator = None
        logger.info("Generator cache cleared; will reload on next use.")

    async def reload_generator_async(self) -> None:
        """Clear and immediately reload the generator in a background thread."""
        self.reload_generator()
        if self._generation_model_name:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._ensure_generator)
            logger.info("Generator reloaded successfully.")

    @property
    def can_generate(self) -> bool:
        return bool(self._generation_model_name)

    def encode(self, text: str) -> np.ndarray:
        return self._ensure_model().encode(text, normalize_embeddings=True)

    async def encode_async(self, text: str) -> np.ndarray:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.encode, text)

    async def preload(self) -> None:
        logger.info("Starting background AI model loading...")
        loop = asyncio.get_running_loop()
        logger.debug("Preload step 1/2: loading sentence embedding model")
        await loop.run_in_executor(None, self._ensure_model)
        if self._generation_model_name:
            logger.debug("Preload step 2/2: loading text generation model")
            try:
                await loop.run_in_executor(None, self._ensure_generator)
            except Exception:
                logger.exception("Preload step 2/2 failed: generation model could not be initialized")
        else:
            logger.debug("Preload step 2/2 skipped: generation model is not configured")
        logger.info("Background AI model loading finished.")

    def generate_sentence(
        self,
        words: list[str],
        bot_name: str = "Bot",
        system_prompt_tpl: str | None = None,
        context_history: list[tuple[bool, str]] | None = None,
    ) -> tuple[str, str]:
        """Generate a conversational reply using the local language model.
        
        Returns:
            tuple[str, str]: (generated_text, generation_metadata_json)
        """
        try:
            gen = self._ensure_generator()
        except Exception:
            logger.exception("Generator initialization failed")
            return ("", json.dumps({"error": "generator_initialization_failed"}, ensure_ascii=False))
        if gen is None:
            return ("", json.dumps({"error": "generator_not_configured"}, ensure_ascii=False))

        latest = context_history[-1][1] if context_history and context_history[-1] else ""
        target_length = max(4, len(latest.strip()))
        word_hint = "".join(words[:3]) if words else ""
        tokenizer = gen.tokenizer
        has_chat_template = bool(getattr(tokenizer, "chat_template", None))
        max_new_tokens = max(256, int(target_length * 1.6))

        if has_chat_template:
            # Instruct 系モデル: チャットテンプレートで返答を生成する
            word_hint_suffix = (" " + word_hint).rstrip() if word_hint else ""
            reply_target = (latest + word_hint_suffix).strip() or (words[0] if words else "こんにちは")
            tpl = system_prompt_tpl if system_prompt_tpl is not None else DEFAULT_LOCAL_SYSTEM_PROMPT
            tpl = tpl.replace("{length_hint}", "{target_length}")
            try:
                system_content = tpl.format(bot_name=bot_name, target_length=target_length)
            except (KeyError, ValueError):
                logger.warning("system_prompt_tpl format failed, falling back to default")
                system_content = DEFAULT_LOCAL_SYSTEM_PROMPT.format(
                    bot_name=bot_name,
                    target_length=target_length,
                )

            # 会話履歴から多ターンメッセージを構築する
            chat_messages: list[dict] = [{"role": "system", "content": system_content}]
            if context_history:
                for is_bot, text in context_history:
                    role = "assistant" if is_bot else "user"
                    # system の直後に assistant を置くとテンプレートエラーになるためスキップする
                    if chat_messages[-1]["role"] == "system" and role == "assistant":
                        continue
                    # 連続同ロールはテンプレートエラーになるためマージする
                    if chat_messages and chat_messages[-1]["role"] == role:
                        chat_messages[-1]["content"] += "\n" + text
                    else:
                        chat_messages.append({"role": role, "content": text})
                # 履歴の最後が assistant なら返信先を最終 user ターンとして追加
                if chat_messages[-1]["role"] != "user":
                    chat_messages.append({"role": "user", "content": reply_target})
            else:
                chat_messages.append({"role": "user", "content": reply_target})
            messages = chat_messages
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            prompt_is_prefix = False  # apply_chat_template が返す文字列全体がプロンプト
        else:
            # Base 系モデル: 会話形式のプロンプトで返答部分を続けさせる
            prompt = latest
            prompt_is_prefix = True

        try:
            generation_kwargs = {
                "max_new_tokens": max_new_tokens,
                "pad_token_id": tokenizer.eos_token_id,
                "truncation": True,
                "return_full_text": False,
            }
            if has_chat_template:
                # system 指示への追従を優先して決定的に生成する
                generation_kwargs.update(
                    {
                        "do_sample": False,
                        "repetition_penalty": 1.08,
                    }
                )
            else:
                generation_kwargs.update(
                    {
                        "do_sample": True,
                        "temperature": 0.7,
                        "top_p": 0.9,
                    }
                )

            outputs = gen(prompt, **generation_kwargs)
            output_dict = outputs[0]
            generated: str = output_dict.get("generated_text", "")
            metadata_json = json.dumps(output_dict, ensure_ascii=False)

            # プロンプト部分を除去して新規生成テキストだけ取り出す
            if prompt_is_prefix and generated.startswith(prompt):
                generated = generated[len(prompt):]
            elif has_chat_template:
                # チャットテンプレートの場合、末尾の assistant ターンだけ残す
                for marker in ("<|im_start|>assistant\n", "<|assistant|>\n", "Assistant:\n"):
                    idx = generated.rfind(marker)
                    if idx != -1:
                        generated = generated[idx + len(marker):]
                        break
                else:
                    # マーカーが見つからなければプロンプト全体を除去
                    if generated.startswith(prompt):
                        generated = generated[len(prompt):]
            generated = generated.strip()
            # 次ターンへの継続（"User:" / "ユーザー:" など）が生成された場合に除去する
            for next_turn in ("\n\n", "\nUser:", "\nユーザー:", "\nuser:", "\n返答:", "\nAssistant:"):
                idx = generated.find(next_turn)
                if idx != -1:
                    generated = generated[:idx].strip()
            
            final_text = generated if generated else (words[0] if words else "")
            return (final_text, metadata_json)
        except Exception:
            logger.exception("Local text generation failed")
            default_text = words[0] if words else ""
            error_metadata = json.dumps({"error": "generation_failed"}, ensure_ascii=False)
            return (default_text, error_metadata)

    async def generate_sentence_async(
        self,
        words: list[str],
        bot_name: str = "Bot",
        system_prompt_tpl: str | None = None,
        context_history: list[tuple[bool, str]] | None = None,
    ) -> tuple[str, str]:
        loop = asyncio.get_running_loop()
        fn = partial(
            self.generate_sentence, words,
            bot_name=bot_name,
            system_prompt_tpl=system_prompt_tpl,
            context_history=context_history,
        )
        return await loop.run_in_executor(None, fn)

    def select_top_words(
        self,
        context_texts: list[str],
        word_embeddings: list[tuple[str, bytes | None]],
        top_k: int = 5,
    ) -> list[str]:
        if not word_embeddings:
            return []

        model = self._ensure_model()
        context = " ".join(context_texts[-1:]) or "。"
        ctx_emb: np.ndarray = model.encode(context, normalize_embeddings=True)

        scored: list[tuple[str, float]] = []
        unembedded: list[str] = []

        for word, emb_bytes in word_embeddings:
            if emb_bytes:
                # Use frombuffer view (no copy) since embeddings are already normalized in storage
                # ctx_emb is normalized (normalize_embeddings=True); dot product = cosine similarity
                word_emb_view = np.frombuffer(emb_bytes, dtype=np.float32)
                scored.append((word, float(np.dot(ctx_emb, word_emb_view))))
            else:
                unembedded.append(word)

        scored.sort(key=lambda x: x[1], reverse=True)
        top = [w for w, _ in scored[:top_k]]

        if len(top) < top_k and unembedded:
            import random
            random.shuffle(unembedded)
            top.extend(unembedded[: top_k - len(top)])

        return top

    async def select_top_words_async(
        self,
        context_texts: list[str],
        word_embeddings: list[tuple[str, bytes | None]],
        top_k: int = 5,
    ) -> list[str]:
        loop = asyncio.get_running_loop()
        fn = partial(self.select_top_words, context_texts, word_embeddings, top_k)
        return await loop.run_in_executor(None, fn)
