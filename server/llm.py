"""LLM 호출 모듈. .env 의 LLM_BACKEND 로 anthropic(Claude API) / ollama(내 컴퓨터) 선택.

기능마다 JSON 스키마를 넘기면 그 모양 그대로의 dict를 돌려준다 (화면에 바로 쓰려고).
"""
import json
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

BACKEND = os.getenv("LLM_BACKEND", "anthropic").lower()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5")
ANTHROPIC_EFFORT = os.getenv("ANTHROPIC_EFFORT", "low")   # 짧은 추천 문장 위주라 low로 충분 (low~max)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


class LLMError(Exception):
    """화면에 그대로 보여줄 수 있는 한국어 오류."""


def model_name() -> str:
    return ANTHROPIC_MODEL if BACKEND == "anthropic" else OLLAMA_MODEL


def ask_json(system: str, prompt: str, schema: dict, max_tokens: int = 8000) -> dict:
    if BACKEND == "anthropic":
        return _anthropic(system, prompt, schema, max_tokens)
    if BACKEND == "ollama":
        return _ollama(system, prompt, schema, max_tokens)
    raise LLMError(f"알 수 없는 LLM_BACKEND: {BACKEND}")


# ---------- 스키마 도우미: 모든 칸 필수 + 정해진 칸 말고는 못 넣게 ----------
def obj(**props) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def arr(items: dict) -> dict:
    return {"type": "array", "items": items}


STR = {"type": "string"}


def enum(*values) -> dict:
    return {"type": "string", "enum": list(values)}


# ---------- 백엔드 ----------
_client = None


def _anthropic(system, prompt, schema, max_tokens):
    import anthropic  # anthropic 백엔드를 쓸 때만 필요

    global _client
    if _client is None:
        _client = anthropic.Anthropic(timeout=90.0)  # ANTHROPIC_API_KEY 환경변수 사용
    try:
        r = _client.beta.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": ANTHROPIC_EFFORT, "format": {"type": "json_schema", "schema": schema}},
            # 안전 분류기가 거절하면 서버가 알아서 다른 모델로 다시 시도
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except TypeError as e:   # 키가 없으면 SDK가 TypeError("Could not resolve authentication method ...")를 냄
        if "authentication" in str(e).lower():
            raise LLMError("AI 서버에 API 키가 없어요. server/.env 의 ANTHROPIC_API_KEY를 채우고 서버를 다시 켜주세요.")
        raise LLMError("anthropic 패키지가 오래됐을 수 있어요. 'pip install -U anthropic'으로 업데이트해주세요.")
    except anthropic.AuthenticationError:
        raise LLMError("AI 서버의 API 키가 올바르지 않아요. server/.env 의 ANTHROPIC_API_KEY를 확인해주세요.")
    except anthropic.RateLimitError:
        raise LLMError("지금 AI 사용량이 많아요. 잠시 뒤 다시 해주세요.")
    except anthropic.BadRequestError as e:
        raise LLMError(f"AI 요청 형식 오류: {e.message}")
    except anthropic.APIStatusError as e:
        raise LLMError(f"AI 서비스 오류({e.status_code}). 잠시 뒤 다시 해주세요.")
    except anthropic.APIConnectionError:
        raise LLMError("AI 서비스에 연결하지 못했어요. 인터넷 연결을 확인해주세요.")
    if r.stop_reason == "refusal":
        raise LLMError("AI가 이 내용에는 답하지 않았어요.")
    if r.stop_reason == "max_tokens":
        raise LLMError("답이 너무 길어져 끊겼어요. 다시 해주세요.")
    text = next((b.text for b in r.content if b.type == "text"), "")
    return _parse(text)


_HAN = re.compile(r"[一-鿿]")   # 중국어 한자


def _ollama(system, prompt, schema, max_tokens):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system + "\n- 반드시 한국어로만 답해. 중국어 한자나 영어 문장을 섞지 마."},
                     {"role": "user", "content": prompt}],
        "format": schema,  # Ollama도 JSON 스키마로 답 모양을 고정할 수 있음
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": max_tokens},
    }
    for attempt in range(3):
        try:
            r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=300)
            r.raise_for_status()
        except requests.RequestException:   # 처음 모델을 GPU에 올릴 때 한 번씩 실패해서 다시 시도
            continue
        text = r.json().get("message", {}).get("content", "")
        if _HAN.search(text) and attempt < 2:   # qwen 모델이 가끔 중국어로 답함 → 다시 생성
            continue
        return _parse(text)
    raise LLMError("Ollama에 연결하지 못했어요. 'ollama serve'가 켜져 있고 모델을 받아 뒀는지 확인해주세요.")


def _parse(text: str) -> dict:
    try:
        return json.loads(text)
    except ValueError:
        raise LLMError("AI 답을 읽지 못했어요. 다시 해주세요.")
