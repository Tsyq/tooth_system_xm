"""
封装智谱大模型（BigModel）的调用逻辑。

配置说明（放在项目根目录的 .env 中）：
- ZHIPU_API_KEY: 智谱开放平台的 API Key
- ZHIPU_API_URL: 大模型 HTTP 接口完整 URL（例如：https://open.bigmodel.cn/api/paas/v4/chat/completions）

注意：这里通过 python-decouple 读取 .env，和 settings.py 的读取方式保持一致，
不依赖系统环境变量，从而避免你已经写了 .env 但 os.getenv 读不到的情况。

由于不同环境下的网关实现可能略有差异，这里采用「尽量通用」的请求与解析方式：
- 请求体：messages 格式，兼容主流 Chat 接口；
- 响应解析：优先使用 data['result']，否则退回到 OpenAI 风格的 choices[0]['message']['content']。
"""
from typing import Optional

import requests
from decouple import config


ZHIPU_API_KEY = config('ZHIPU_API_KEY', default='')
ZHIPU_API_URL = config('ZHIPU_API_URL', default='')
ZHIPU_MODEL = config('ZHIPU_MODEL', default='glm-4')


class LLMCallError(RuntimeError):
    """大模型调用异常（统一类型，方便上层捕获）"""


def call_llm(prompt: str, *, system_prompt: Optional[str] = None, temperature: float = 0.3) -> str:
    """
    调用大模型接口，返回生成的文本。

    说明：
    - 不直接依赖具体厂商 SDK，仅使用 HTTP POST，方便你在网关层做协议适配；
    - 如果需要自定义 payload 结构，可以在这里按你的网关格式调整。
    """
    if not ZHIPU_API_URL:
        raise LLMCallError('ZHIPU_API_URL 未配置，请在 .env 中设置后重启服务')

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": ZHIPU_MODEL,
        "messages": messages,
        "temperature": float(temperature),
    }

    headers = {
        "Content-Type": "application/json",
    }
    # 约定使用 Bearer 形式，如果你的网关需要其他形式，可以在这里调整
    if ZHIPU_API_KEY:
        headers["Authorization"] = f"Bearer {ZHIPU_API_KEY}"

    try:
        resp = requests.post(ZHIPU_API_URL, json=payload, headers=headers, timeout=60)
        data = resp.json()

        # 智谱接口通常在 JSON 中包含 code / error 字段，非 200 需要视为失败
        if isinstance(data, dict):
            if data.get("error"):
                raise LLMCallError(f"调用大模型返回错误: {data['error']}")
            if isinstance(data.get("code"), int) and data["code"] != 200:
                # 智谱部分接口使用 code 字段表示业务状态
                raise LLMCallError(f"调用大模型返回错误: {data}")
    except Exception as exc:  # noqa: BLE001
        raise LLMCallError(f'调用大模型接口失败: {exc}') from exc

    # 兼容几种常见返回格式
    # 1) 百度系 / 通用网关常见：{"result": "..."}
    if isinstance(data, dict) and "result" in data and isinstance(data["result"], str):
        return data["result"]

    # 2) OpenAI / DeepSeek 兼容风格：{"choices":[{"message":{"content":"..."}}]}
    try:
        choices = data.get("choices") if isinstance(data, dict) else None
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content")
            if isinstance(content, str):
                return content
    except Exception:  # noqa: BLE001
        # 解析失败时继续走兜底逻辑
        pass

    raise LLMCallError(f'无法从大模型响应中解析文本内容: {data}')


