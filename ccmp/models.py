"""Built-in provider templates: Anthropic-compatible base URL + model mapping."""

TEMPLATES = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/anthropic",
        "models": {
            "default": "deepseek-v4-pro",
            "sonnet": "deepseek-v4-pro",
            "opus": "deepseek-v4-pro",
            "haiku": "deepseek-flash",
            "subagent": "deepseek-flash",
        },
    },
    "glm": {
        "base_url": "https://open.bigmodel.cn/api/anthropic",
        "models": {
            "default": "glm-5.3[1m]",
            "sonnet": "glm-5.3[1m]",
            "opus": "glm-5.3[1m]",
            "haiku": "glm-5.3-flash[1m]",
            "subagent": "glm-5.3-flash[1m]",
        },
        "extra_env": {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "1000000"},
    },
    "kimi": {
        "base_url": "https://api.moonshot.cn/anthropic",
        "models": {
            "default": "kimi-k3.1-pro",
            "sonnet": "kimi-k3.1-pro",
            "opus": "kimi-k3.1-pro",
            "haiku": "kimi-k2.7-code",
            "subagent": "kimi-k2.7-code",
        },
    },
    "ark": {
        "base_url": "https://ark.cn-beijing.volces.com/api/coding",
        "models": {
            "default": "glm-5.3",
            "sonnet": "glm-5.3",
            "opus": "glm-5.3",
            "haiku": "glm-5.3-flash",
            "subagent": "glm-5.3-flash",
        },
    },
    "bailian": {
        "base_url": "https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic",
        "models": {
            "default": "auto",
            "sonnet": "qwen3.8-flash",
            "opus": "qwen3.8-max",
            "haiku": "qwen3.8-flash",
            "subagent": "auto",
        },
        "extra_env": {"CLAUDE_CODE_MAX_CONTEXT_TOKENS": "983616"},
    },
}
