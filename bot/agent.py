from openai import OpenAI
from agents import (
    Agent,
    Runner,
    function_tool,
    set_default_openai_client,
    set_default_openai_api,
    WebSearchTool,
    InputGuardrail,
    GuardrailFunctionOutput,
    RunContextWrapper,
)
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_deployment: str

    class Config:
        env_file = ".env"


settings = Settings()

client = OpenAI(
    base_url=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
)

set_default_openai_client(client)
set_default_openai_api("chat_completions")


# ============ GUARDRAIL ============
class FinanceCheck(BaseModel):
    is_finance_related: bool
    reason: str


guardrail_agent = Agent(
    name="Guardrail",
    model=settings.azure_openai_deployment,
    instructions="Определи является ли запрос пользователя связанным с финансами: акции, облигации, криптовалюта, инвестиции, компании. Отвечай только JSON.",
    output_type=FinanceCheck,
)


async def finance_guardrail(
    ctx: RunContextWrapper, agent: Agent, input: str
) -> GuardrailFunctionOutput:
    result = await Runner.run(guardrail_agent, input, context=ctx.context)
    output = result.final_output_as(FinanceCheck)
    return GuardrailFunctionOutput(
        output_info=output,
        tripwire_triggered=not output.is_finance_related,
    )


# ============ TOOLS ============
@function_tool
def get_current_date() -> str:
    """Возвращает текущую дату"""
    from datetime import datetime
    return datetime.now().strftime("%d.%m.%Y")


# ============ AGENT ============
finance_agent = Agent(
    name="Финансовый аналитик",
    model=settings.azure_openai_deployment,
    instructions="""Ты опытный финансовый аналитик.

Когда пользователь просит проанализировать акцию или облигацию:
1. Используй WebSearch чтобы найти актуальную цену и новости
2. Найди ключевые финансовые показатели (P/E, дивиденды, долг)
3. Оцени риски и потенциал роста
4. Дай чёткую рекомендацию: 📈 ПОКУПАТЬ / ⏸ ДЕРЖАТЬ / 📉 ПРОДАВАТЬ
5. Объясни почему кратко и по делу

Всегда используй get_current_date чтобы знать актуальную дату.
Отвечай на русском языке. Будь конкретным.""",
    tools=[
        WebSearchTool(),
        get_current_date,
    ],
    input_guardrails=[
        InputGuardrail(guardrail_function=finance_guardrail)
    ],
)


async def analyze(user_message: str) -> str:
    """Запускает агента и возвращает ответ"""
    try:
        result = await Runner.run(finance_agent, user_message)
        return result.final_output
    except Exception as e:
        if "tripwire" in str(e).lower():
            return "❌ Я финансовый аналитик и могу помочь только с анализом акций, облигаций и инвестиций. Попробуй спросить про конкретную акцию или облигацию 😊"
        raise e
