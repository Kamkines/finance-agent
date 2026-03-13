from agents import (
    Agent,
    Runner,
    function_tool,
    set_default_openai_client,
    set_default_openai_api,
    InputGuardrail,
    GuardrailFunctionOutput,
    RunContextWrapper,
    set_tracing_disabled,
)
from agents.memory import SQLiteSession
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings
from tavily import TavilyClient


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")
    telegram_bot_token: str
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_deployment: str
    tavily_api_key: str


settings = Settings()

client = AsyncOpenAI(
    base_url=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
)
set_default_openai_client(client)
set_default_openai_api("chat_completions")
set_tracing_disabled(True)

tavily = TavilyClient(api_key=settings.tavily_api_key)

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

@function_tool
def get_current_date() -> str:
    """Возвращает текущую дату"""
    from datetime import datetime
    return datetime.now().strftime("%d.%m.%Y")

@function_tool
def search_web(query: str) -> str:
    """Ищет актуальную финансовую информацию в интернете"""
    response = tavily.search(query=query, max_results=5)
    results = []
    for r in response.get("results", []):
        results.append(f"- {r['title']}: {r['content'][:300]}")
    return "\n".join(results)

finance_agent = Agent(
    name="Финансовый аналитик",
    model=settings.azure_openai_deployment,
    instructions="""Ты опытный финансовый аналитик.

Если пользователь использует слова "эта акция", "она", "её", "этой акции", "предыдущей" — посмотри историю диалога и используй последнюю упомянутую акцию. Никогда не переспрашивай если акция уже была в диалоге.

Когда пользователь просит проанализировать акцию или облигацию:
1. Используй search_web чтобы найти актуальную цену и новости
2. Используй ТОЛЬКО цены и цифры из search_web — не используй свои знания о ценах, они устарели
3. Найди ключевые финансовые показатели (P/E, дивиденды, долг)
4. Оцени риски и потенциал роста
5. Дай чёткую рекомендацию: 📈 ПОКУПАТЬ / ⏸ ДЕРЖАТЬ / 📉 ПРОДАВАТЬ
6. Объясни почему кратко и по делу

Всегда используй get_current_date чтобы знать актуальную дату.
Отвечай на русском языке. Будь конкретным.""",
    tools=[search_web, get_current_date],
    input_guardrails=[InputGuardrail(guardrail_function=finance_guardrail)],
)

async def analyze(user_message: str, user_id: int) -> str:
    try:
        session = SQLiteSession(
            session_id=str(user_id),
            db_path="/app/sessions.db"
        )

        result = await Runner.run(finance_agent, user_message, session=session)
        return result.final_output
    except Exception as e:
        if "tripwire" in str(e).lower():
            return "❌ Я финансовый аналитик и могу помочь только с анализом акций, облигаций и инвестиций. Попробуй спросить про конкретную акцию или облигацию 😊"
        raise e